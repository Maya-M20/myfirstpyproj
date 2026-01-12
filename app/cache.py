import hashlib
import inspect
from functools import wraps
from typing import Callable, Any
import logging
from .redis_client import redis_client

logger = logging.getLogger(__name__)


def generate_cache_key(func: Callable, *args, **kwargs) -> str:
    """Генерирует ключ кеша на основе функции и её аргументов"""
    func_name = func.__module__ + "." + func.__qualname__

    args_repr = []

    for i, arg in enumerate(args):
        try:
            args_repr.append(f"arg{i}:{repr(arg)}")
        except:
            args_repr.append(f"arg{i}:<unserializable>")

    for k, v in kwargs.items():
        try:
            args_repr.append(f"{k}:{repr(v)}")
        except:
            args_repr.append(f"{k}:<unserializable>")

    key_string = f"{func_name}|{'|'.join(args_repr)}"
    key_hash = hashlib.md5(key_string.encode()).hexdigest()

    return f"cache:{func_name}:{key_hash}"


def cached(ttl: int = 300):
    """
    Декоратор для кеширования результатов функций

    Args:
        ttl: Время жизни кеша в секундах (по умолчанию 5 минут)
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Генерируем ключ кеша
            cache_key = generate_cache_key(func, *args, **kwargs)

            # Пытаемся получить данные из кеша
            cached_result = redis_client.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Кеш HIT для {func.__name__}")
                # Добавляем флаг cache_hit для логирования
                wrapper.cache_hit = True
                return cached_result

            # Если нет в кеше, выполняем функцию
            logger.debug(f"Кеш MISS для {func.__name__}")
            wrapper.cache_hit = False
            result = func(*args, **kwargs)

            # Сохраняем результат в кеш
            redis_client.set(cache_key, result, ttl=ttl)

            return result

        # Инициализируем флаг
        wrapper.cache_hit = False

        # Метод для инвалидации кеша этой функции
        def invalidate_cache(*args, **kwargs):
            cache_key = generate_cache_key(func, *args, **kwargs)
            deleted = redis_client.delete(cache_key)
            if deleted:
                logger.debug(f"Кеш INVALIDATED для {func.__name__}")
            return deleted

        wrapper.invalidate_cache = invalidate_cache

        return wrapper

    return decorator


def invalidate_molecules_cache():
    """Инвалидирует ВЕСЬ кеш молекул"""
    deleted = redis_client.delete_pattern("cache:*molecule*")
    deleted += redis_client.delete_pattern("cache:*search*")
    logger.info(f"Инвалидировано кешей молекул: {deleted}")
    return deleted
