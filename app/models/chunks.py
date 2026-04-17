from sqlalchemy import Column, Integer,String,Text,ForeignKey, JSON
from pgvector.sqlalchemy import Vector
from app.core.database import Base


class Chunk(Base):
    __tablename__ = "chunks"
    id              = Column(Integer,primary_key= True)
    book_id         = Column(Integer,ForeignKey("books.id"))
    chunk_index     = Column(Integer)
    start_page      = Column(Integer)
    end_page        = Column(Integer)
    row_text        = Column(Text)
    summary         = Column(Text)
    embedding       = Column(Vector(1536))     # OpenAI ada-002 dimension
    meta_data       = Column(JSON)
