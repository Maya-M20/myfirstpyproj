from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index
from sqlalchemy.sql import func 
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

#твблица molecules в БД
class Molecule(Base):
    __tablename__ = "molecules"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String(255), nullable=False, index=True)
    
    formula = Column(String(100), nullable=False)
    
    molecular_weight = Column(Float, nullable=False)

    inchi = Column(String, nullable=False, unique=True)
    
    smiles = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

#индексы для ускорения поиска

Index("idx_molecule_name_formula", Molecule.name, Molecule.formula)

Index("idx_molecular_weight", Molecule.molecular_weight)