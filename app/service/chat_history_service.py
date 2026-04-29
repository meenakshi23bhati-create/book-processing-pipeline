import time
from typing import Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.models.chunks import Chunk
from app.models.books import Book
from app.models.chat_history import ChatHistory

print("🤖 Chat model load ho raha hai...")
_model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Chat model ready!")


def search_similar_chunks(query: str, book_id: int, top_k: int = 5) -> list:
    """Query se similar chunks dhundho"""
    query_embedding = _model.encode(query, normalize_embeddings=True).tolist()

    engine = create_engine(settings.SYNC_DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT 
                    id, chunk_index, start_page, end_page,
                    row_text, summary, meta_data,
                    1 - (embedding <=> CAST(:embedding AS vector)) as similarity
                FROM chunks
                WHERE book_id = :book_id
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """),
            {
                "embedding": str(query_embedding),
                "book_id": book_id,
                "top_k": top_k
            }
        ).mappings().all()

    return [dict(r) for r in result]


def get_similar_past_questions(query: str, book_id: int, top_k: int = 3) -> list:
    """Pehle pooche gaye similar questions dhundho"""
    query_embedding = _model.encode(query, normalize_embeddings=True).tolist()

    engine = create_engine(settings.SYNC_DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT 
                    question, answer,
                    1 - (q_embedding <=> CAST(:embedding AS vector)) as similarity,
                    created_at
                FROM chat_history
                WHERE book_id = :book_id
                ORDER BY q_embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """),
            {
                "embedding": str(query_embedding),
                "book_id": book_id,
                "top_k": top_k
            }
        ).mappings().all()

    return [dict(r) for r in result]


def save_chat_history(book_id: int, question: str, answer: str):
    """Chat history vector DB mein save karo"""
    q_embedding = _model.encode(question, normalize_embeddings=True).tolist()

    engine = create_engine(settings.SYNC_DATABASE_URL)
    with Session(engine) as session:
        history = ChatHistory(
            book_id=book_id,
            question=question,
            answer=answer,
            q_embedding=q_embedding
        )
        session.add(history)
        session.commit()
    print(f"✅ Chat history saved!")


def get_book_memory(book_id: int) -> dict:
    """Book ka start, middle, end memory"""
    engine = create_engine(settings.SYNC_DATABASE_URL)

    with engine.connect() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM chunks WHERE book_id = :bid"),
            {"bid": book_id}
        ).scalar()

        if not total:
            return {"start": None, "middle": None, "end": None, "total_chunks": 0}

        start_chunks = conn.execute(
            text("SELECT row_text, start_page, end_page FROM chunks WHERE book_id = :bid ORDER BY chunk_index ASC LIMIT 2"),
            {"bid": book_id}
        ).mappings().all()

        mid = total // 2
        middle_chunks = conn.execute(
            text("SELECT row_text, start_page, end_page FROM chunks WHERE book_id = :bid ORDER BY chunk_index ASC LIMIT 2 OFFSET :offset"),
            {"bid": book_id, "offset": mid}
        ).mappings().all()

        end_chunks = conn.execute(
            text("SELECT row_text, start_page, end_page FROM chunks WHERE book_id = :bid ORDER BY chunk_index DESC LIMIT 2"),
            {"bid": book_id}
        ).mappings().all()

    return {
        "start": [dict(c) for c in start_chunks],
        "middle": [dict(c) for c in middle_chunks],
        "end": [dict(c) for c in end_chunks],
        "total_chunks": total
    }


def generate_answer(query: str, context_chunks: list) -> str:
    """Context se answer generate karo"""
    if not context_chunks:
        return "Koi relevant information nahi mili."

    try:
        from transformers import pipeline
        qa_pipeline: Any = pipeline(
            "question-answering",    # type: ignore
            model="deepset/roberta-base-squad2",
            device=-1
        )

        best_answer = ""
        best_score = 0

        for chunk in context_chunks[:3]:
            try:
                result = qa_pipeline(
                    question=query,
                    context=chunk['row_text'][:1000]
                )
                if result['score'] > best_score:
                    best_score = result['score']
                    best_answer = result['answer']
            except Exception:
                continue

        if best_answer and best_score > 0.01:
            return best_answer
        else:
            return f"Relevant content (pages {context_chunks[0]['start_page']}-{context_chunks[0]['end_page']}): {context_chunks[0]['summary']}"

    except Exception as e:
        return f"Relevant content: {context_chunks[0]['summary'] if context_chunks else 'Not found'}"


def chat_with_book(book_id: int, query: str) -> dict:
    """Main chat function"""
    total_start = time.time()

    # Step 1: Similar chunks dhundho
    similar_chunks = search_similar_chunks(query, book_id, top_k=5)

    if not similar_chunks:
        return {
            "answer": "Is book mein koi relevant information nahi mili.",
            "sources": [],
            "query": query,
            "similar_questions": [],
            "time_taken": round(time.time() - total_start, 2)
        }

    # Step 2: Pehle similar questions dekho
    similar_qs = get_similar_past_questions(query, book_id, top_k=3)

    # Step 3: Answer generate karo
    answer = generate_answer(query, similar_chunks)

    # Step 4: History save karo
    save_chat_history(book_id, query, answer)

    sources = [
        {
            "chunk_index": c["chunk_index"],
            "pages": f"{c['start_page']}-{c['end_page']}",
            "similarity": round(float(c["similarity"]), 3),
            "summary": c["summary"][:200] if c["summary"] else "",
        }
        for c in similar_chunks
    ]

    return {
        "answer": answer,
        "sources": sources,
        "query": query,
        "book_id": book_id,
        "similar_questions": [
            {
                "question": q["question"],
                "answer": q["answer"],
                "similarity": round(float(q["similarity"]), 3),
            }
            for q in similar_qs
            if float(q["similarity"]) > 0.7  # sirf relevant ones
        ],
        "time_taken": round(time.time() - total_start, 2)
    }