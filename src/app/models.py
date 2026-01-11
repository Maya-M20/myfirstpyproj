# Импортируем необходимые типы данных из SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index
from sqlalchemy.sql import func  # для работы с датами
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

# Создаем класс Molecule (Молекула)
# Это будет соответствовать таблице 'molecules' в БД
class Molecule(Base):
    # Имя таблицы в БД
    __tablename__ = "molecules"
    
    # Поля таблицы:
    
    # ID - целое число, первичный ключ, с индексом
    # Primary Key = уникальный идентификатор (как номер паспорта)
    # Index = ускоряет поиск по этому полю
    id = Column(Integer, primary_key=True, index=True)
    
    # Название молекулы - строка до 255 символов, не может быть пустым
    name = Column(String(255), nullable=False, index=True)
    
    # Формула - строка до 100 символов, не может быть пустой
    formula = Column(String(100), nullable=False)
    
    # Молекулярный вес - число с плавающей точкой
    molecular_weight = Column(Float, nullable=False)
    
    # SMILES - текстовое поле для химической нотации
    smiles = Column(Text, nullable=False)

    # Дата создания - автоматически ставится при создании
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Дата обновления - автоматически обновляется при изменении
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# СОЗДАЕМ ИНДЕКСЫ для ускорения поиска:

# Индекс по имени и формуле вместе (для сложных поисков)
Index("idx_molecule_name_formula", Molecule.name, Molecule.formula)

# Индекс по молекулярному весу (для поиска по весу)
Index("idx_molecular_weight", Molecule.molecular_weight)