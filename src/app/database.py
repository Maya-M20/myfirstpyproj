from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()  # Функция ищет файл .env в папке проекта и загружает все переменные из него.

# Для Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Пробуем получить DATABASE_URL из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")

# Если не нашли в .env, пробуем получить из Docker окружения
if not DATABASE_URL:
    DATABASE_URL = os.environ.get("DATABASE_URL")


# Создаем движок для подключения к БД
# pool_pre_ping=True проверяет подключение перед использованием
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,  # Переподключаемся каждые 5 минут
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для всех моделей
Base = declarative_base()
