from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


#базовый класс для молекулы
class MoleculeBase(BaseModel):
    name: str
    formula: str
    molecular_weight: float
    inchi: str
    smiles: str


#схема для создания молекулы - от пользователя
class MoleculeCreate(MoleculeBase):
    pass 


#схема для отправки молекулы - к пользователю
class Molecule(MoleculeBase):
    id: int  
    created_at: datetime  
    updated_at: Optional[datetime] = None 

    class Config:
        from_attributes = True 


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
