from sqlalchemy import Column, Integer,String,Text,ForeignKey, JSON
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class Book(Base):
    __tablename__ = "books"
    id              = Column(Integer,primary_key=True)
    title           = Column(String(255))
    total_pages     = Column(Integer)
    status          = Column(String(50),default="pending") # pending/processing/done
    json_path       = Column(String(500))
    meta_data       = Column(JSON) 