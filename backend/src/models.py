from sqlalchemy import Column, Integer, String, Boolean
from .database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    telefono = Column(String(20), nullable=False, unique=True)
    consentimiento = Column(Boolean, nullable=True)  # None = no definido, True/False = decisión