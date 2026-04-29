from fastapi import APIRouter,Depends
from  sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,text 
from app.core.database import get_db
from app.models.chunks import Chunk

router= APIRouter(prefix="/chunks", tags=["chunks"])

def chunk_to_dict(chunk: Chunk) -> dict:
    """Chunk object ko safe dict mein convert karo — embedding exclude karo"""
    return {
        "id": chunk.id,
        "book_id": chunk.book_id,
        "chunk_index": chunk.chunk_index,
        "start_page": chunk.start_page,
        "end_page": chunk.end_page,
        "row_text": chunk.row_text,
        "summary": chunk.summary,
        "meta_data": chunk.meta_data,
        "has_embedding": chunk.embedding is not None,  # ✅ Vector ki jagah bool
    }
@router.get("/{chunk_id}")
async def get_chunk(
    chunk_id: int,
    db: AsyncSession = Depends(get_db)
):
    await db.rollback()
    chunk = await db.get(Chunk, chunk_id)
    if not chunk:
        return {"error": "Chunk not found"}
    return chunk_to_dict(chunk)


@router.get("/book/{book_id}")
async def get_book_chunks(
    book_id: int,
    db: AsyncSession = Depends(get_db)
):
    await db.rollback()
    result = await db.execute(
        select(Chunk)
        .where(Chunk.book_id == book_id)
        .order_by(Chunk.chunk_index)
    )
    chunks = result.scalars().all()
    return {
        "book_id": book_id,
        "total_chunks": len(chunks),
        "chunks": [chunk_to_dict(c) for c in chunks]
    }