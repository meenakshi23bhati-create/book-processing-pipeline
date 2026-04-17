from celery import group
from app.workers.celery import celery_app    # type: ignore
from app.service.splitter import split_book_into_chunks
from app.service.processor import process_chunk
from app.service.exporter import save_chunks_to_json
from app.models.books import Book 
from app.models.chunks import Chunk  
from app.core.config import settings
from app.core.database import engine



@celery_app.task(bind=True, name="process_single_chunk")
def process_single_chunk(self, book_id: int, chunk_data: dict) -> dict:
    print("Processing chunk:", chunk_data["chunk_index"])   

    """
    One chunk process karta hai
    """
    try:
        process_chunk(book_id, chunk_data)
        return {"status": "done", "chunk_index": chunk_data["chunk_index"]}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5, max_retries=3)


@celery_app.task(name="process_book")
def process_book(book_id: int, pdf_path: str):
    
    """
    Main orchestrator
    """
    chunks = split_book_into_chunks(pdf_path, settings.CHUNK_SIZE)
    print("Chunks:", len(chunks))
    job = group(
        process_single_chunk.si(book_id, { # type: ignore
            "chunk_index": c.chunk_index,
            "start_page": c.start_page,
            "end_page": c.end_page,
            "pages_text": c.pages_text,
        })
        for c in chunks
    )

    job.apply_async()   

    return {"book_id": book_id, "chunks_total": len(chunks)}



# from celery import group
# from app.workers.celery import celery_app
# from app.service.splitter import split_book_into_chunks
# from app.service.processor import process_chunk
# from app.service.exporter import save_chunks_to_json
# from app.core.config import settings
# import sqlalchemy


# @celery_app.task(bind=True,name="process_single_chunk")
# def process_single_chunk(self,book_id:int,chunk_data:dict)->dict:
#     """
#     one chunk process karta hai
#     -Text clean 
#     -Embedding
#     -DB mein save kar
#     """
#     try:
#         result = process_chunk(book_id,chunk_data)
#         return {"status":"done","chunk_index":chunk_data["chunk_index"]}
#     except Exception as exc:
#         raise self.retry(exc=exc,countdown=5,max_retries=3)
    
# @celery_app.task(name="process_book")
# def process_book(book_id: int,pdf_path: str):
#     """"
#     Main orchestrator task:
#     1. PDF split karna
#     2. Har chunk ke liye parallel task dispatch karna (group)
#     3. JSON export karna
#     """
#     chunks=split_book_into_chunks(pdf_path,settings.CHUNK_SIZE)
#     # Parallel execution 
#     job= group(
#         process_single_chunk.si(book_id,{      # type: ignore[attr-defined]
#             "chunk_index":c.chunk_index,
#             "start_page": c.start_page,
#             "end_page": c.end_page,
#             "text":"\n".join(c.pages_text),
#         })
#         for c in chunks
#     )
#     result =job.apply_async()

#     # All complete then  JSON save 
#     result.get()
#     save_chunks_to_json(book_id)
#     return {"book_id":book_id,"chunks_total":len(chunks)}