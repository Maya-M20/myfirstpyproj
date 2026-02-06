from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

#Загрузка переменных окружения
load_dotenv()  # Функция ищет файл .env в папке проекта и загружает все переменные из него.

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = os.environ.get("DATABASE_URL")


#создание движка для подключения к БД
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)

#создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#базовый класс для всех моделей
Base = declarative_base()
