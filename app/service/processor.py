import re
from typing import Dict

def clean_text(text: str) -> str:
    """Text ko clean karta hai"""
    if not text:
        return ""
    
    # Multiple spaces/newlines ko ek space mein
    text = re.sub(r'\s+', ' ', text)
    
    # Sirf clearly useless characters hatao
    text = re.sub(r'[^\w\s.,!?:;()\-\'\"@#%&+=/<>]', ' ', text)
    
    # Extra spaces phir se
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def process_chunk(book_id: int, chunk_data: dict) -> dict:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.core.config import settings
    from app.models.chunks import Chunk
    from app.models.books import Book

    row_text = " ".join(chunk_data.get("pages_text", []))
    cleaned_text = clean_text(row_text)

    # ✅ Ye add karo — empty chunk skip karo
    if not cleaned_text:
        print(f"[WARN] Chunk {chunk_data['chunk_index']} ka text empty hai, skip kar raha hoon")
        return {"chunk_id": None, "status": "skipped - empty text"}

    summary = cleaned_text[:500] + "..." if len(cleaned_text) > 500 else cleaned_text

    engine = create_engine(settings.SYNC_DATABASE_URL)
    with Session(engine) as session:
        chunk = Chunk(
            book_id=book_id,
            chunk_index=chunk_data["chunk_index"],
            start_page=chunk_data["start_page"],
            end_page=chunk_data["end_page"],
            row_text=cleaned_text,
            summary=summary,
            meta_data={
                "start_page": chunk_data["start_page"],
                "end_page": chunk_data["end_page"],
                "char_count": len(cleaned_text),
                "word_count": len(cleaned_text.split()),
            }
        )
        session.add(chunk)
        book= session.get(Book,book_id)
        if book:
            book.status ="done"  # type: ignore

        session.commit()
        session.refresh(chunk)

    return {"chunk_id": chunk.id, "status": "saved"}
