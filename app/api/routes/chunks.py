from fastapi import APIRouter,Depends
from  sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Select,text 
from app.core.database import get_db
from app.models.chunks import Chunk

router= APIRouter(prefix="/chunks", tags=["chunks"])

@router.get ("/{chunk_id}")
async def get_chunk(
    chunk_id: int,
    db: AsyncSession= Depends(get_db)
):
    await db.rollback()
    chunk= await db.get(Chunk, chunk_id)
    if not chunk:
        return {"error":"chunk is not found"}
    return chunk

@router.get("/book/{book_id}")
async def get_book_chunks(
    book_id : int,
    db: AsyncSession= Depends(get_db)
):
    await db.rollback()
    result= await db.execute(
        Select (Chunk)
        .where(Chunk.book_id == book_id)
        .order_by(Chunk.chunk_index)
    )
    chunks= result.scalars().all()
    return {
        "book_id":book_id,
        "total_chunks": len(chunks),
        "chunks":chunks
    }   