import hashlib
import inspect
from functools import wraps
from typing import Callable, Any
import logging
from .redis_client import redis_client

logger = logging.getLogger(__name__)


def generate_cache_key(func: Callable, *args, **kwargs) -> str:
    """генерация ключа кеша"""
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
    декоратор для кеширования результатов функций

    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = generate_cache_key(func, *args, **kwargs) #генерация ключа кэша

            #получаем данные из кеша
            cached_result = redis_client.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Кеш HIT для {func.__name__}")
                #добавление флага cache_hit для логирования
                wrapper.cache_hit = True
                return cached_result

            #если не в кэше, то функция 
            logger.debug(f"Кеш MISS для {func.__name__}")
            wrapper.cache_hit = False
            result = func(*args, **kwargs)

            #созранение рез-та в кэш
            redis_client.set(cache_key, result, ttl=ttl)

            return result

        wrapper.cache_hit = False

        #метод для инвалидации кэша этой функции
        def invalidate_cache(*args, **kwargs):
            cache_key = generate_cache_key(func, *args, **kwargs)
            deleted = redis_client.delete(cache_key)
            if deleted:
                logger.debug(f"Кэш INVALIDATED для {func.__name__}")
            return deleted

        wrapper.invalidate_cache = invalidate_cache

        return wrapper

    return decorator


def invalidate_molecules_cache():
    """инвалидация всего кэша молекул"""
    deleted = redis_client.delete_pattern("cache:*molecule*")
    deleted += redis_client.delete_pattern("cache:*search*")
    logger.info(f"Инвалидировано кэшей молекул: {deleted}")
    return deleted
