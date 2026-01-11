from celery import Celery
from .redis_client import get_redis_client
import os

# Получаем клиент Redis
redis_client = get_redis_client()

celery_app = Celery(
    "myfirstpyproject",
    broker=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/0",
    backend=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/1",
    include=["app.tasks"],
)

# Конфигурация
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_send_sent_event=True,
    worker_send_task_events=True,
    result_extended=True,
)


# Используем ваш Redis клиент для результатов
class CustomRedisBackend:
    def __init__(self):
        self.redis = redis_client

    def store_result(self, task_id, result, state, **kwargs):
        """Сохранение результата в Redis"""
        import json

        data = {"result": result, "state": state, "date_done": kwargs.get("date_done")}
        self.redis.setex(f"celery-task-meta-{task_id}", 86400, json.dumps(data))

    def get_result(self, task_id):
        """Получение результата из Redis"""
        import json

        data = self.redis.get(f"celery-task-meta-{task_id}")
        if data:
            return json.loads(data)
        return None
