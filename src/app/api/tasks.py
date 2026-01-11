from fastapi import APIRouter, HTTPException, BackgroundTasks
from celery.result import AsyncResult
from ..schemas import TaskResponse, SearchRequest, TaskBase
from ..tasks import substructure_search_task
from ..celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/search", response_model=TaskResponse)
async def start_search_task(request: SearchRequest):
    """
    Запуск асинхронного субструктурного поиска
    """
    try:
        # Запускаем Celery задачу
        task = substructure_search_task.delay(
            {"query": request.query, "parameters": request.parameters}
        )

        return TaskResponse(
            task_id=task.id,
            status_url=f"/api/tasks/status/{task.id}",
            message="Задача поиска запущена",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}", response_model=TaskBase)
async def get_task_status(task_id: str):
    """
    Проверка статуса задачи
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

        return TaskBase(**response_data)

    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Task not found: {e}")


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """
    Отмена задачи
    """
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return {"message": f"Task {task_id} cancelled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def celery_health():
    """
    Проверка здоровья Celery
    """
    try:
        # Простая проверка подключения к брокеру
        insp = celery_app.control.inspect()
        stats = insp.stats()

        if stats:
            return {"status": "healthy", "workers": len(stats), "workers_info": stats}
        else:
            return {"status": "no workers available"}

    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
