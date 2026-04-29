from fastapi import APIRouter
from pydantic import BaseModel
from app.service.chat_service import chat_with_book, get_book_memory
from sqlalchemy import create_engine, text
from app.core.config import settings

router = APIRouter()

class ChatRequest(BaseModel):
    book_id: int
    query: str

@router.post("/chat")
def chat(request: ChatRequest):
    """Book se chat karo"""
    result = chat_with_book(request.book_id, request.query)
    return result

@router.get("/chat/memory/{book_id}")
def book_memory(book_id: int):
    """Book ka start, middle, end memory nikalo"""
    memory = get_book_memory(book_id)
    return memory
from sqlalchemy import create_engine, text
from app.core.config import settings

@router.get("/chat/books")
def get_all_books():
    """Saari processed books ki list"""
    from sqlalchemy import create_engine, text
    from app.core.config import settings
    
    engine = create_engine(settings.SYNC_DATABASE_URL)
    with engine.connect() as conn:
        books = conn.execute(
            text("SELECT id, title, status, total_pages, meta_data FROM books ORDER BY id DESC")
        ).mappings().all()
    return {"books": [dict(b) for b in books]}