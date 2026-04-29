from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id          = Column(Integer, primary_key=True)
    book_id     = Column(Integer, ForeignKey("books.id"))
    question    = Column(Text)
    answer      = Column(Text)
    q_embedding = Column(Vector(768 ))#768  # question ka embedding 384
    created_at  = Column(DateTime, default=func.now())