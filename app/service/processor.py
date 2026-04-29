import re
from typing import Dict,Any
import time 
from sentence_transformers import SentenceTransformer

print("🤖 Embedding model load ho raha hai...")
_model = SentenceTransformer('BAAI/bge-base-en-v1.5')
print("✅ Model ready!")

def clean_text(text: str) -> str:
    """Text ko clean karta hai"""
    if not text:
        return ""
    
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s.,!?:;()\-\'\"@#%&+=/<>]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def generate_embedding(text: str) -> list:
    """Text ka embedding banao"""
    start = time.time()
    truncated = " ".join(text.split()[:512])
    print(f"  🔢 Embedding generate ho rahi hai ({len(text)} chars)...")
    embedding = _model.encode(text, normalize_embeddings=True)
    elapsed = time.time() - start
    print(f"  ✅ Embedding done! ({len(embedding)} dims, {elapsed:.2f}s)")
    return embedding.tolist()


def process_chunk(book_id: int, chunk_data: dict,total_chunks: int = 1, processed_chunks: int = 0) -> dict:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.core.config import settings
    from app.models.chunks import Chunk
    from app.models.books import Book
    total_start = time.time()
    chunk_idx = chunk_data['chunk_index']
    
    print(f"\n{'='*40}")
    print(f"⚙️  Chunk {chunk_idx}/{total_chunks} processing shuru...")
    print(f"   Pages: {chunk_data['start_page']} → {chunk_data['end_page']}")
    
    # Step 1: Text clean
    step_start = time.time()
    print(f"  📝 Step 1/4: Text clean ho raha hai...")
    row_text = " ".join(chunk_data.get("pages_text", []))
    cleaned_text = clean_text(row_text)

    
    if not cleaned_text:
        print(f"   ⚠️  Chunk {chunk_idx} empty — skip!")
        return {"chunk_id": None, "status": "skipped", "time_taken": 0}
    
    print(f"  ✅ Text ready: {len(cleaned_text)} chars, {len(cleaned_text.split())} words ({time.time()-step_start:.2f}s)")

    # Step 2: Summary
    step_start = time.time()
    print(f"   📋 Step 2/4: Summary bana raha hai...")
    summary = cleaned_text[:500] + "..." if len(cleaned_text) > 500 else cleaned_text
    print(f"   ✅ Summary ready ({time.time()-step_start:.2f}s)")
    
    # Step 3: Embedding
    print(f"  🔢 Step 3/3: Embedding bana raha hai...")
    embedding = generate_embedding(cleaned_text)
    
    # Step 4: DB save
    step_start = time.time()
    print(f"  💾 Step 4/4: DB mein save ho raha hai...")
    engine = create_engine(settings.SYNC_DATABASE_URL)

    with Session(engine) as session:
        chunk = Chunk(
            book_id=book_id,
            chunk_index=chunk_data["chunk_index"],
            start_page=chunk_data["start_page"],
            end_page=chunk_data["end_page"],
            row_text=cleaned_text,
            summary=summary,
            embedding=embedding,
            meta_data={
                "start_page": chunk_data["start_page"],
                "end_page": chunk_data["end_page"],
                "char_count": len(cleaned_text),
                "word_count": len(cleaned_text.split()),
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_dims": len(embedding),
            }
        )
        session.add(chunk)
        book= session.get(Book,book_id)
        if book:
            elapsed_total = time.time() - total_start
            avg_time_per_chunk = elapsed_total  # is chunk ka time
            remaining_chunks = total_chunks - (processed_chunks + 1)
            estimated_remaining = avg_time_per_chunk * remaining_chunks

            book.status = f"processing {chunk_idx+1}/{total_chunks}"  # type: ignore
            book.meta_data = {  # type: ignore
                "chunks_done": processed_chunks + 1,
                "total_chunks": total_chunks,
                "estimated_remaining_seconds": round(estimated_remaining),
                "estimated_remaining_minutes": round(estimated_remaining / 60, 1),
            }
            
        session.commit()
        session.refresh(chunk)
    chunk_total_time = time.time() - total_start
    print(f"   ✅ DB save done! ({time.time()-step_start:.2f}s)")
    print(f"   🎉 Chunk {chunk_idx+1}/{total_chunks} complete! Total: {chunk_total_time:.2f}s")
    print(f"{'='*45}\n")
    return {"chunk_id": chunk.id,
             "status": "saved",
             "time_taken": round(chunk_total_time, 2)
            }
