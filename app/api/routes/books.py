from fastapi import APIRouter,UploadFile,File,Depends,BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.books import Book
from app.workers.task import process_book
import shutil, os

router=APIRouter(prefix="/books",tags=["books"])

@router.post("/Upload")
async def upload_book(
    file : UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # PDF save karo

    upload_dir ="/app/uploads"
    os.makedirs(upload_dir, exist_ok= True)
    pdf_path= f"{upload_dir}/{file.filename}"


    with open (pdf_path,"wb") as f:
        shutil.copyfileobj(file.file,f)

    # DB mein book record banao
    book =Book(title=file.filename,status="pending")
    db.add(book)
    await db.commit()
    await db.refresh(book)

    book_id = book.id

# Celery task dispatch karna (async, non-blocking)
    process_book.delay(book_id,pdf_path)            # type: ignore[attr-defined]

    return {
        "book_id":book.id,
        "message":"Processing start in BackGround"
        }


@router.get("/{book_id}/chunks")
async def get_chunks(
    book_id:int,
    db: AsyncSession= Depends(get_db)
):
    from app.models.chunks import Chunk
    await db.rollback() 
    result= await db.execute(
        select(Chunk).where(Chunk.book_id== book_id).order_by(Chunk.chunk_index)
    )
    chunks= result.scalars().all()
    return{
        "book_id":book_id,
        "total_chunks":len(chunks),
        "chunks":chunks
    }