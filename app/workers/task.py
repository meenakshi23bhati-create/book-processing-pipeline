import time
from celery import group, chord
from app.workers.celery import celery_app
from app.service.splitter import split_book_into_chunks
from app.service.processor import process_chunk
from app.core.config import settings
from app.models.books import Book
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from celery import signature  # type: ignore


def update_book_progress(book_id: int, status: str, meta: dict):
    """Book ki progress DB mein update karo"""
    engine = create_engine(settings.SYNC_DATABASE_URL)
    with Session(engine) as session:
        book = session.get(Book, book_id)
        if book:
            book.status = status      # type: ignore
            book.meta_data = meta     # type: ignore
            session.commit()


@celery_app.task(bind=True, name="process_single_chunk")  # type: ignore[misc]
def process_single_chunk(self, book_id: int, chunk_data: dict, total_chunks: int, processed_so_far: int) -> dict:
    """Ek chunk process karta hai — parallel chalega"""
    try:
        result = process_chunk(
            book_id=book_id,
            chunk_data=chunk_data,
            total_chunks=total_chunks,
            processed_chunks=processed_so_far
        )
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5, max_retries=3)


@celery_app.task(name="on_all_chunks_done")  # type: ignore[misc]
def on_all_chunks_done(results, book_id: int, total_chunks: int, pipeline_start: float):
    """Jab saare chunks complete ho jayein tab chalega"""
    total_time = time.time() - pipeline_start

    saved   = sum(1 for r in results if r and r.get("status") == "saved")
    skipped = sum(1 for r in results if r and r.get("status") == "skipped")

    print(f"\n{'='*50}")
    print(f"🎉 Book {book_id} — COMPLETE!")
    print(f"   ✅ Saved  : {saved}/{total_chunks} chunks")
    print(f"   ⚠️  Skipped: {skipped}/{total_chunks} chunks")
    print(f"   ⏱️  Total  : {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"{'='*50}\n")

    update_book_progress(book_id, "done", {
        "total_chunks": total_chunks,
        "chunks_done": saved,
        "chunks_skipped": skipped,
        "chunks_remaining": 0,
        "total_time_seconds": round(total_time, 2),
        "total_time_minutes": round(total_time / 60, 1),
        "estimated_remaining_seconds": 0,
        "estimated_remaining_minutes": 0,
    })

    return {
        "book_id": book_id,
        "chunks_saved": saved,
        "chunks_skipped": skipped,
        "total_time_seconds": round(total_time, 2),
        "total_time_minutes": round(total_time / 60, 1),
    }


@celery_app.task(name="process_book")  # type: ignore[misc]
def process_book(book_id: int, pdf_path: str):
    pipeline_start = time.time()

    print(f"\n🚀 Book {book_id} processing shuru!")
    print(f"   📁 PDF: {pdf_path}")

    # ── Step 1: PDF Split ─────────────────────────
    print(f"\n📖 Step 1: PDF split ho raha hai...")
    split_start = time.time()
    chunks = split_book_into_chunks(pdf_path, settings.CHUNK_SIZE)
    split_time = time.time() - split_start
    total_chunks = len(chunks)

    print(f"✅ Split done! {total_chunks} chunks ({split_time:.1f}s)")

    update_book_progress(book_id, "processing", {
        "total_chunks": total_chunks,
        "chunks_done": 0,
        "chunks_remaining": total_chunks,
        "split_time_seconds": round(split_time, 2),
        "estimated_remaining_seconds": None,
        "estimated_remaining_minutes": None,
    })

    # ── Step 2: Parallel Processing ───────────────
    print(f"\n⚡ Step 2: {total_chunks} chunks — 4 parallel workers mein...")
    print(f"   🔢 Estimated time: ~{round(total_chunks * 13 / 4 / 60, 1)} minutes")

    
    tasks = [
        signature(                          # type: ignore[call-arg]
            "process_single_chunk",
            args=(
                book_id,
                {
                    "chunk_index": c.chunk_index,
                    "start_page":  c.start_page,
                    "end_page":    c.end_page,
                    "pages_text":  c.pages_text,
                },
                total_chunks,
                i,
            )
        )
        for i, c in enumerate(chunks)
    ]

    # Callback — sab done hone par
    callback = signature(                   # type: ignore[call-arg]
        "on_all_chunks_done",
        kwargs={
            "book_id": book_id,
            "total_chunks": total_chunks,
            "pipeline_start": pipeline_start,
        }
    )

    chord(tasks)(callback)

    elapsed = time.time() - pipeline_start
    print(f"\n✅ {total_chunks} tasks dispatch ho gaye! ({elapsed:.1f}s)")

    return {
        "book_id": book_id,
        "chunks_total": total_chunks,
        "workers": 4,
        "message": f"{total_chunks} chunks 4 parallel workers mein process ho rahe hain"
    }