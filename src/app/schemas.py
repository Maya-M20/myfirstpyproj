from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


# Базовый класс для молекулы - что общего у всех молекулярных схем
class MoleculeBase(BaseModel):
    name: str
    formula: str
    molecular_weight: float
    smiles: str


# Схема для СОЗДАНИЯ молекулы (принимаем от пользователя)
class MoleculeCreate(MoleculeBase):
    pass  # пока наследуем все поля без изменений


# Схема для ОТПРАВКИ молекулы (возвращаем пользователю)
class Molecule(MoleculeBase):
    id: int  # добавляем ID
    created_at: datetime  # добавляем дату создания
    updated_at: Optional[datetime] = None  # может быть пустым если не обновлялась

    # Важная настройка для Pydantic v2:
    class Config:
        from_attributes = True  # позволяет создавать схему из SQLAlchemy модели


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PROGRESS = "PROGRESS"
    REVOKED = "REVOKED"


class TaskBase(BaseModel):
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: Optional[int] = 0
    current_step: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    parameters: Dict[str, Any] = {}
    timeout: Optional[int] = 300


class TaskResponse(BaseModel):
    task_id: str
    status_url: str
    message: str
