from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.books import Book
from app.workers.task import process_book
import shutil
import os

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/Upload")
async def upload_book(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    upload_dir = "/app/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    pdf_path = f"{upload_dir}/{file.filename}"

    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    book = Book(title=file.filename, status="pending")
    db.add(book)
    await db.commit()
    await db.refresh(book)
    book_id = book.id

    process_book.delay(book_id, pdf_path)  # type: ignore[attr-defined]

    return {
        "book_id": book_id,
        "message": "Processing start in BackGround"
    }


@router.get("/{book_id}/chunks")
async def get_chunks(
    book_id: int,
    db: AsyncSession = Depends(get_db)
):
    from app.models.chunks import Chunk
    await db.rollback()
    result = await db.execute(
        select(Chunk).where(Chunk.book_id == book_id).order_by(Chunk.chunk_index)
    )
    chunks = result.scalars().all()
    return {
        "book_id": book_id,
        "total_chunks": len(chunks),
        "chunks": chunks
    }


@router.get("/{book_id}/progress")  # ✅ / add kiya
async def book_progress(
    book_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Book).where(Book.id == book_id)
    )
    book = result.scalar_one_or_none()

    if not book:
        return {"error": "Book nahi mili"}

    meta = book.meta_data or {}  # type: ignore
    chunks_done = meta.get("chunks_done", 0)
    total_chunks = meta.get("total_chunks", 1)

    status = str(book.status)
    if status == "pending":
        message = "⏳ Processing shuru nahi hui"
    elif status == "processing":
        message = f"⚙️ Chal rahi hai — {chunks_done}/{total_chunks} chunks done"
    elif status == "done":
        message = "✅ Processing complete!"
    else:
        message = "❓ Unknown status"

    return {
        "book_id": book_id,
        "title": book.title,
        "status": book.status,
        "message": message,
        "progress": {
            "chunks_done": chunks_done,
            "total_chunks": total_chunks,
            "chunks_remaining": meta.get("chunks_remaining", 0),
            "percent_complete": round((chunks_done / total_chunks) * 100),
            "estimated_remaining_minutes": meta.get("estimated_remaining_minutes"),
            "total_time_minutes": meta.get("total_time_minutes"),
        }
    }


@router.get("/{book_id}/status")
async def book_status(
    book_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Book).where(Book.id == book_id)
    )
    book = result.scalar_one_or_none()

    if not book:
        return {"error": "Book nahi mili"}

    return {
        "book_id": book_id,
        "title": book.title,
        "status": book.status,
        "meta_data": book.meta_data
    }