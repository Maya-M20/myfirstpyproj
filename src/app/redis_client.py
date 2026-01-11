import redis
import os
import logging
from typing import Optional
import json
from functools import wraps
import pickle
from datetime import timedelta

logger = logging.getLogger(__name__)


class RedisClient:
    """Клиент для работы с Redis с обработкой ошибок"""

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = None
        self.is_available = False

    def connect(self):
        """Подключение к Redis"""
        try:
            self._client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=False,  # получаем bytes, сами декодируем
                socket_connect_timeout=5,  # таймаут подключения 5 сек
                socket_timeout=5,  # таймаут операций 5 сек
                retry_on_timeout=True,  # повторять при таймауте
                max_connections=10,  # максимальное количество подключений
            )
            # Проверяем подключение
            self._client.ping()
            self.is_available = True
            logger.info("Подключение к Redis установлено")
        except Exception as e:
            self.is_available = False
            logger.warning(f"Redis недоступен: {e}. Работа без кеша.")
            self._client = None

    @property
    def client(self):
        """Ленивая загрузка клиента Redis"""
        if self._client is None:
            self.connect()
        return self._client

    def set(self, key: str, value, ttl: int = 3600) -> bool:
        """Сохранить значение с TTL (по умолчанию 1 час)"""
        if not self.is_available:
            return False

        try:
            # Сериализуем объект
            serialized = pickle.dumps(value)
            result = self.client.setex(key, ttl, serialized)
            return bool(result)
        except Exception as e:
            logger.error(f"Ошибка записи в Redis: {e}")
            self.is_available = False
            return False

    def get(self, key: str):
        """Получить значение по ключу"""
        if not self.is_available:
            return None

        try:
            value = self.client.get(key)
            if value:
                return pickle.loads(value)
            return None
        except Exception as e:
            logger.error(f"Ошибка чтения из Redis: {e}")
            self.is_available = False
            return None

    def delete(self, key: str) -> bool:
        """Удалить ключ"""
        if not self.is_available:
            return False

        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Ошибка удаления из Redis: {e}")
            self.is_available = False
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Удалить все ключи по паттерну"""
        if not self.is_available:
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Ошибка удаления по паттерну: {e}")
            self.is_available = False
            return 0

    def clear_cache(self):
        """Очистить весь кеш (только для разработки!)"""
        if not self.is_available:
            return

        try:
            self.client.flushdb()
            logger.info("🧹 Весь кеш Redis очищен")
        except Exception as e:
            logger.error(f"Ошибка очистки кеша: {e}")


# Создаем глобальный экземпляр
redis_client = RedisClient()


def get_redis_client() -> RedisClient:
    """
    Функция для получения Redis клиента.
    Создана для совместимости с Celery.
    """
    global redis_client

    # Если клиент не подключен, подключаем
    if not redis_client.is_available:
        redis_client.connect()

    return redis_client
