from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from rdkit import Chem
from typing import List, Optional
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
from celery.result import AsyncResult

import sys
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Корректируем пути для импорта из app
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # Поднимаемся на уровень выше (в /app)
sys.path.append(parent_dir)

# Импортируем из app (теперь app находится на том же уровне что и src)
try:
    from app import models, schemas
    from app.database import engine, SessionLocal
    from app.dependencies import get_db
    from app.cache import cached, invalidate_molecules_cache
    from app.redis_client import redis_client, get_redis_client
    from app.celery_app import celery_app
    from app.tasks import substructure_search_task

    logger.info(" Импорт модулей из app успешен")
except ImportError as e:
    logger.error(f" Ошибка импорта: {e}")
    logger.info("Текущий sys.path:")
    for p in sys.path:
        logger.info(f"  {p}")
    raise

app = FastAPI(title="Molecules API with Celery", version="1.0.0")

# ============================================================================
# СОЗДАНИЕ ТАБЛИЦ В БАЗЕ ДАННЫХ
# ============================================================================

print("Проверяем подключение к PostgreSQL и создаем таблицы...")

try:
    # Создаем таблицы если их нет
    models.Base.metadata.create_all(bind=engine)
    print(" Таблицы успешно созданы в PostgreSQL!")

except Exception as e:
    print(f"Ошибка при создании таблиц: {e}")
    print("Продолжаем без базы данных...")


# Инициализируем Redis при старте
@app.on_event("startup")
async def startup_event():
    redis_client.connect()
    logger.info("Приложение запущено, Redis подключен")


# ============================================================================
# PYDANTIC СХЕМЫ
# ============================================================================


class MoleculeSimple(BaseModel):
    """Простая схема для добавления молекулы (только ID и SMILES)"""

    id: str
    smiles: str


class MoleculeUpdateSimple(BaseModel):
    """Схема для обновления молекулы"""

    smiles: str


class SearchRequest(BaseModel):
    """Схема для субструктурного поиска"""

    substructure: str
    parameters: dict = {}
    timeout: Optional[int] = 300


class CeleryTaskResponse(BaseModel):
    """Схема ответа для запуска Celery задачи"""

    task_id: str
    status_url: str
    message: str


class TaskStatusResponse(BaseModel):
    """Схема ответа для статуса задачи"""

    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
    progress: Optional[int] = 0
    current_step: Optional[str] = None
    date_done: Optional[datetime] = None


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================


def substructure_search(
    molecules_smiles: List[str], substructure_smiles: str
) -> List[str]:
    """
    Поиск молекул, содержащих заданную субструктуру.
    """
    try:
        substructure_mol = Chem.MolFromSmiles(substructure_smiles)
        if substructure_mol is None:
            raise ValueError(f"Некорректный SMILES субструктуры: {substructure_smiles}")
    except Exception as e:
        raise ValueError(f"Ошибка при создании молекулы субструктуры: {e}")

    results = []

    for smiles in molecules_smiles:
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                logger.warning(f"Пропущен некорректный SMILES: {smiles}")
                continue

            if mol.HasSubstructMatch(substructure_mol):
                results.append(smiles)

        except Exception as e:
            logger.error(f"Ошибка при обработке молекулы {smiles}: {e}")
            continue

    return results


# ============================================================================
# CELERY ЭНДПОИНТЫ
# ============================================================================


@app.post("/async/search", response_model=CeleryTaskResponse)
async def start_async_search(
    search_request: SearchRequest, background_tasks: BackgroundTasks
):
    """
    Запуск асинхронного субструктурного поиска через Celery
    """
    try:
        # Запускаем Celery задачу
        task = substructure_search_task.delay(
            {
                "substructure": search_request.substructure,
                "parameters": search_request.parameters,
                "timeout": search_request.timeout,
            }
        )

        logger.info(f"Запущена асинхронная задача поиска: task_id={task.id}")

        return CeleryTaskResponse(
            task_id=task.id,
            status_url=f"/tasks/status/{task.id}",
            message="Задача субструктурного поиска запущена. Используйте status_url для отслеживания прогресса.",
        )

    except Exception as e:
        logger.error(f"Ошибка при запуске задачи: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Проверка статуса Celery задачи
    """
    try:
        task_result = AsyncResult(task_id, app=celery_app)

        response_data = {"task_id": task_id, "status": task_result.status}

        if task_result.info:
            if isinstance(task_result.info, dict):
                response_data.update(task_result.info)
            else:
                response_data["result"] = task_result.info

        if task_result.state == "FAILURE":
            response_data["error"] = str(task_result.info)

        if task_result.date_done:
            response_data["date_done"] = task_result.date_done

        logger.info(
            f"Запрос статуса задачи: task_id={task_id}, status={task_result.status}"
        )
        return TaskStatusResponse(**response_data)

    except Exception as e:
        logger.error(f"Ошибка при получении статуса задачи: {e}")
        raise HTTPException(status_code=404, detail=f"Task not found: {e}")


@app.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """
    Отмена выполнения задачи
    """
    try:
        celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
        logger.info(f"Задача отменена: task_id={task_id}")
        return {"message": f"Task {task_id} cancelled", "task_id": task_id}
    except Exception as e:
        logger.error(f"Ошибка при отмене задачи: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/celery/health")
async def celery_health():
    """
    Проверка здоровья Celery
    """
    try:
        insp = celery_app.control.inspect()
        stats = insp.stats()

        if stats:
            workers = len(stats)
            active_tasks = insp.active() or {}
            scheduled_tasks = insp.scheduled() or {}

            health_info = {
                "status": "healthy",
                "workers": workers,
                "active_tasks": sum(len(tasks) for tasks in active_tasks.values()),
                "scheduled_tasks": sum(
                    len(tasks) for tasks in scheduled_tasks.values()
                ),
                "workers_info": {
                    k: {"concurrency": v.get("pool", {}).get("max-concurrency", "N/A")}
                    for k, v in stats.items()
                },
            }
            return health_info
        else:
            return {"status": "no workers available", "workers": 0}

    except Exception as e:
        logger.error(f"Ошибка проверки здоровья Celery: {e}")
        return {"status": "unhealthy", "error": str(e)}


# ============================================================================
# КОРНЕВЫЕ ЭНДПОИНТЫ
# ============================================================================


@app.get("/")
def home():
    return {
        "message": "API для работы с химическими молекулами",
        "features": ["PostgreSQL", "Redis Cache", "Celery Async Tasks"],
        "endpoints": [
            "POST /molecules - Добавление новой молекулы",
            "GET /molecules/{id} - Получение молекулы по ID",
            "PUT /molecules/{id} - Обновление молекулы",
            "DELETE /molecules/{id} - Удаление молекулы",
            "GET /molecules - Список всех молекул с пагинацией",
            "POST /search - Субструктурный поиск (синхронный)",
            "POST /async/search - Субструктурный поиск (асинхронный через Celery)",
            "GET /tasks/status/{task_id} - Проверка статуса задачи",
            "GET /celery/health - Проверка здоровья Celery",
            "GET /health - Проверка здоровья приложения",
        ],
    }


@app.get("/health")
def health_check():
    """Проверка здоровья приложения"""
    redis_status = "available" if redis_client.is_available else "unavailable"

    # Проверка Celery
    celery_status = "unknown"
    try:
        insp = celery_app.control.inspect()
        stats = insp.stats()
        celery_status = "available" if stats else "no workers"
    except:
        celery_status = "unavailable"

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {"redis": redis_status, "celery": celery_status},
    }


@app.get("/page", response_class=HTMLResponse)
def html_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI with Celery</title>
        <meta charset="utf-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 100px auto;
                text-align: center;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                border-radius: 15px;
            }
            h1 {
                font-size: 3em;
                margin: 0;
            }
            .features {
                background: rgba(255,255,255,0.1);
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }
            a {
                color: white;
                text-decoration: none;
                background: rgba(255,255,255,0.2);
                padding: 10px 20px;
                border-radius: 5px;
                display: inline-block;
                margin: 10px;
            }
            a:hover {
                background: rgba(255,255,255,0.3);
            }
        </style>
    </head>
    <body>
        <h1>FastAPI with Celery</h1>
        <p>Асинхронная обработка химических данных</p>
        <div class="features">
            <strong>Доступные функции:</strong><br>
            • PostgreSQL база данных<br>
            • Redis кеширование<br>
            • Celery асинхронные задачи<br>
            • Субструктурный поиск молекул
        </div>
        <div>
            <a href="/">JSON API</a>
            <a href="/docs">Документация</a>
            <a href="/flower" target="_blank">Celery Monitor</a>
        </div>
    </body>
    </html>
    """


# ============================================================================
# ОСНОВНЫЕ ЭНДПОИНТЫ API С КЕШИРОВАНИЕМ
# ============================================================================


# 1. POST /molecules — Добавление новой молекулы
@app.post("/molecules")
def add_molecule(molecule: MoleculeSimple, db: Session = Depends(get_db)):
    """
    Добавляет новую молекулу в базу данных.
    """
    try:
        # Проверяем, нет ли молекулы с таким ID
        existing = (
            db.query(models.Molecule)
            .filter(models.Molecule.name == molecule.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400, detail=f"Молекула с ID '{molecule.id}' уже существует"
            )

        # Создаем молекулу
        db_molecule = models.Molecule(
            name=molecule.id,
            formula="N/A",
            molecular_weight=0.0,
            smiles=molecule.smiles,
            inchi=None,
        )

        db.add(db_molecule)
        db.commit()
        db.refresh(db_molecule)

        logger.info(
            f"✅ Молекула добавлена: ID='{molecule.id}', SMILES='{molecule.smiles}'"
        )

        #  ИНВАЛИДАЦИЯ КЕША ПОСЛЕ ДОБАВЛЕНИЯ
        invalidate_molecules_cache()
        logger.info(f"Кеш инвалидирован после добавления молекулы {molecule.id}")

        return {
            "message": "Молекула успешно добавлена",
            "id": molecule.id,
            "database_id": db_molecule.id,
            "smiles": molecule.smiles,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при добавлении: {str(e)}")


# 2. GET /molecules/{id} — Получение молекулы по ID (С КЕШИРОВАНИЕМ)
@app.get("/molecules/{molecule_id}")
@cached(ttl=600)  #  Кешируем на 10 минут
def get_molecule(molecule_id: str, db: Session = Depends(get_db)):
    """
    Получает молекулу по её идентификатору.
    """
    molecule = (
        db.query(models.Molecule).filter(models.Molecule.name == molecule_id).first()
    )

    if not molecule:
        raise HTTPException(
            status_code=404, detail=f"Молекула с ID '{molecule_id}' не найдена"
        )

    result = {
        "id": molecule.name,
        "database_id": molecule.id,
        "smiles": molecule.smiles,
        "formula": molecule.formula,
        "molecular_weight": molecule.molecular_weight,
        "inchi": molecule.inchi,
        "created_at": molecule.created_at,
        "updated_at": molecule.updated_at,
    }

    logger.info(f"✅ Получена молекула {molecule_id}")
    return result


# 3. PUT /molecules/{id} — Обновление молекулы
@app.put("/molecules/{molecule_id}")
def update_molecule(
    molecule_id: str, update_data: MoleculeUpdateSimple, db: Session = Depends(get_db)
):
    """
    Обновляет SMILES молекулы по её идентификатору.
    """
    molecule = (
        db.query(models.Molecule).filter(models.Molecule.name == molecule_id).first()
    )

    if not molecule:
        raise HTTPException(
            status_code=404, detail=f"Молекула с ID '{molecule_id}' не найдена"
        )

    try:
        old_smiles = molecule.smiles
        molecule.smiles = update_data.smiles

        db.commit()
        db.refresh(molecule)

        logger.info(
            f"Молекула обновлена: ID='{molecule_id}', SMILES: {old_smiles} -> {update_data.smiles}"
        )

        #  ИНВАЛИДАЦИЯ КЕША ПОСЛЕ ОБНОВЛЕНИЯ
        # 1. Инвалидируем кеш этой конкретной молекулы
        get_molecule.invalidate_cache(molecule_id)

        # 2. Инвалидируем общий кеш
        invalidate_molecules_cache()

        logger.info(f"Кеш инвалидирован после обновления молекулы {molecule_id}")

        return {
            "message": f"Молекула '{molecule_id}' успешно обновлена",
            "id": molecule_id,
            "old_smiles": old_smiles,
            "new_smiles": update_data.smiles,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении: {str(e)}")


# 4. DELETE /molecules/{id} — Удаление молекулы
@app.delete("/molecules/{molecule_id}")
def delete_molecule(molecule_id: str, db: Session = Depends(get_db)):
    """
    Удаляет молекулу по её идентификатору.
    """
    molecule = (
        db.query(models.Molecule).filter(models.Molecule.name == molecule_id).first()
    )

    if not molecule:
        raise HTTPException(
            status_code=404, detail=f"Молекула с ID '{molecule_id}' не найдена"
        )

    try:
        db_id = molecule.id
        db.delete(molecule)
        db.commit()

        logger.info(f"Молекула удалена: ID='{molecule_id}' (database_id={db_id})")

        #  ИНВАЛИДАЦИЯ КЕША ПОСЛЕ УДАЛЕНИЯ
        # 1. Инвалидируем кеш удаленной молекулы
        get_molecule.invalidate_cache(molecule_id)

        # 2. Инвалидируем общий кеш
        invalidate_molecules_cache()

        logger.info(f"Кеш инвалидирован после удаления молекулы {molecule_id}")

        return {
            "message": f"Молекула '{molecule_id}' успешно удалена",
            "id": molecule_id,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении: {str(e)}")


# 5. GET /molecules — Список всех молекул (С КЕШИРОВАНИЕМ)
@app.get("/molecules")
@cached(ttl=300)  # Кешируем на 5 минут
def get_all_molecules(
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(10, ge=1, le=100, description="Количество записей для возврата"),
    db: Session = Depends(get_db),
):
    """
    Возвращает список всех молекул с пагинацией.
    """
    # Получаем общее количество молекул
    total = db.query(models.Molecule).count()

    # Получаем молекулы с пагинацией
    molecules = db.query(models.Molecule).offset(skip).limit(limit).all()

    # Преобразуем в требуемый формат
    result = []
    for molecule in molecules:
        result.append(
            {
                "id": molecule.name,
                "database_id": molecule.id,
                "smiles": molecule.smiles,
                "formula": molecule.formula,
                "molecular_weight": molecule.molecular_weight,
                "created_at": molecule.created_at,
            }
        )

    logger.info(f"Получено {len(molecules)} молекул (skip={skip}, limit={limit})")

    return {"total": total, "skip": skip, "limit": limit, "molecules": result}


# 6. POST /search — Субструктурный поиск (синхронный, С КЕШИРОВАНИЕМ)
@app.post("/search")
@cached(ttl=600)  # Кешируем на 10 минут (поиск может быть тяжелым)
def search_molecules(search_request: SearchRequest, db: Session = Depends(get_db)):
    """
    Выполняет синхронный субструктурный поиск по всем молекулам.
    Для больших наборов данных используйте /async/search
    """
    # Получаем ВСЕ молекулы из БД
    all_molecules = db.query(models.Molecule).all()

    if not all_molecules:
        return {
            "substructure": search_request.substructure,
            "found_count": 0,
            "molecules": [],
        }

    # Извлекаем SMILES
    all_smiles = [mol.smiles for mol in all_molecules]

    # Выполняем поиск субструктур
    try:
        found_smiles = substructure_search(all_smiles, search_request.substructure)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Находим полную информацию о найденных молекулах
    results = []
    for smiles in found_smiles:
        molecule = (
            db.query(models.Molecule).filter(models.Molecule.smiles == smiles).first()
        )
        if molecule:
            results.append(
                {
                    "id": molecule.name,
                    "database_id": molecule.id,
                    "smiles": molecule.smiles,
                    "formula": molecule.formula,
                    "molecular_weight": molecule.molecular_weight,
                }
            )

    logger.info(
        f"Выполнен синхронный поиск субструктуры '{search_request.substructure}', найдено {len(results)} молекул"
    )

    return {
        "substructure": search_request.substructure,
        "found_count": len(results),
        "molecules": results,
    }


# ============================================================================
# ЭНДПОИНТЫ ДЛЯ УПРАВЛЕНИЯ КЕШЕМ
# ============================================================================


@app.get("/cache/stats")
def get_cache_stats():
    """Получить статистику кеша Redis"""
    if not redis_client.is_available:
        return {"redis": "unavailable"}

    try:
        info = redis_client.client.info()
        keys_count = redis_client.client.dbsize()

        return {
            "redis": "available",
            "used_memory": info.get("used_memory_human", "N/A"),
            "keys": keys_count,
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": round(
                info.get("keyspace_hits", 0)
                / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)),
                2,
            ),
        }
    except Exception as e:
        return {"redis": "error", "error": str(e)}


@app.delete("/cache/clear")
def clear_cache():
    """Очистить весь кеш Redis (только для разработки!)"""
    if not redis_client.is_available:
        return {"message": "Redis недоступен"}

    try:
        redis_client.client.flushdb()
        logger.warning("Весь кеш Redis очищен")
        return {"message": "Кеш очищен"}
    except Exception as e:
        return {"message": f"Ошибка при очистке кеша: {str(e)}"}


@app.delete("/cache/molecules")
def clear_molecules_cache():
    """Очистить кеш молекул"""
    deleted = invalidate_molecules_cache()
    return {"message": f"Инвалидировано кешей молекул: {deleted}"}


# Запуск приложения
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
