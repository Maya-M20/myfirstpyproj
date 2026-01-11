from .celery_app import celery_app
from .redis_client import get_redis_client
import time
from typing import Dict, Any

redis_client = get_redis_client()


@celery_app.task(bind=True, name="substructure_search")
def substructure_search_task(self, search_data: Dict[str, Any]):
    """
    Асинхронная задача для субструктурного поиска
    """
    try:
        total_steps = 5
        current_step = 0

        # Шаг 1: Подготовка данных
        current_step += 1
        self.update_state(
            state="PROGRESS",
            meta={
                "current": current_step,
                "total": total_steps,
                "status": "Подготовка данных",
                "progress": int((current_step / total_steps) * 100),
            },
        )
        time.sleep(2)  # Имитация работы

        # Шаг 2: Поиск субструктур
        current_step += 1
        self.update_state(
            state="PROGRESS",
            meta={
                "current": current_step,
                "total": total_steps,
                "status": "Поиск субструктур",
                "progress": int((current_step / total_steps) * 100),
            },
        )
        time.sleep(3)

        # Шаг 3: Фильтрация результатов
        current_step += 1
        self.update_state(
            state="PROGRESS",
            meta={
                "current": current_step,
                "total": total_steps,
                "status": "Фильтрация результатов",
                "progress": int((current_step / total_steps) * 100),
            },
        )
        time.sleep(2)

        # Шаг 4: Анализ
        current_step += 1
        self.update_state(
            state="PROGRESS",
            meta={
                "current": current_step,
                "total": total_steps,
                "status": "Анализ результатов",
                "progress": int((current_step / total_steps) * 100),
            },
        )
        time.sleep(1)

        # Шаг 5: Формирование отчета
        current_step += 1
        self.update_state(
            state="PROGRESS",
            meta={
                "current": current_step,
                "total": total_steps,
                "status": "Формирование отчета",
                "progress": 100,
            },
        )
        time.sleep(1)

        result = {
            "found_structures": 42,
            "search_time": 9.0,
            "search_params": search_data,
            "message": "Поиск завершен успешно",
        }

        # Сохраняем результат в Redis
        import json

        redis_client.setex(f"search_result_{self.request.id}", 3600, json.dumps(result))

        return result

    except Exception as e:
        self.update_state(
            state="FAILURE",
            meta={
                "exc_type": type(e).__name__,
                "exc_message": str(e),
                "status": "Ошибка выполнения",
            },
        )
        raise


@celery_app.task(
    bind=True, name="long_running_task", time_limit=300, soft_time_limit=280
)
def long_running_task_with_timeout(self, data):
    """
    Задача с таймаутом (5 минут максимум)
    """
    try:
        # Длительная операция
        for i in range(100):
            time.sleep(1)
            self.update_state(state="PROGRESS", meta={"progress": i + 1, "total": 100})

            # Проверка таймаута
            if self.request.called_directly:
                continue

        return {"result": "success", "processed_items": 100}

    except Exception as e:
        # Логирование ошибки
        import logging

        logging.error(f"Task failed: {e}")
        raise
