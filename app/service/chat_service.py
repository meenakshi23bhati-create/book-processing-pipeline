import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.chat_history import ChatHistory
import requests

from sentence_transformers import SentenceTransformer
print("🤖 Embedding model load ho raha hai...")
_embedding_model = SentenceTransformer('BAAI/bge-base-en-v1.5')
print("✅ Embedding model loaded! (BAAI/bge-base-en-v1.5 — 768 dims)")

def get_hf_embedding(text_input: str) -> list:
    """Provider 1: Local BAAI/bge-base-en-v1.5 embedding"""
    embedding = _embedding_model.encode(text_input, normalize_embeddings=True).tolist()
    print(f"✅ Local Embedding done! (dims: {len(embedding)})")
    return embedding



def search_similar_chunks(query: str, book_id: int, top_k: int = 10) -> list:
    """Vector + Keyword hybrid search"""
    query_embedding = get_hf_embedding(query)

    engine = create_engine(settings.SYNC_DATABASE_URL)
    with engine.connect() as conn:

        # Vector search
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
        vector_chunks = [dict(r) for r in result]

        # Keyword search
        keywords = [w for w in query.split() if len(w) > 3]
        keyword = keywords[0] if keywords else query.split()[0]

        keyword_result = conn.execute(
            text("""
                SELECT 
                    id, chunk_index, start_page, end_page,
                    row_text, summary, meta_data,
                    0.5 as similarity
                FROM chunks
                WHERE book_id = :book_id
                  AND row_text ILIKE :keyword
                LIMIT 5
            """),
            {
                "book_id": book_id,
                "keyword": f"%{keyword}%"
            }
        ).mappings().all()
        keyword_chunks = [dict(r) for r in keyword_result]

        # Combine — duplicates hatao
        seen_ids = set()
        combined = []
        for c in vector_chunks + keyword_chunks:
            if c['id'] not in seen_ids:
                seen_ids.add(c['id'])
                combined.append(c)

    print(f"✅ {len(combined)} chunks mile! (vector: {len(vector_chunks)}, keyword: {len(keyword_chunks)})")
    return combined[:top_k]


def get_similar_past_questions(query: str, book_id: int, top_k: int = 3) -> list:
    """Pehle pooche gaye similar questions dhundho"""
    try:
        query_embedding = get_hf_embedding(query)
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
    except Exception as e:
        print(f"[WARN] Similar questions error: {e}")
        return []


def save_chat_history(book_id: int, question: str, answer: str):
    """Chat history save karo"""
    try:
        q_embedding = get_hf_embedding(question)
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
    except Exception as e:
        print(f"[WARN] Chat history save error: {e}")


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
            text("""SELECT row_text, start_page, end_page
                FROM chunks WHERE book_id = :bid
                ORDER BY chunk_index ASC LIMIT 2"""),
            {"bid": book_id}
        ).mappings().all()

        mid = total // 2
        middle_chunks = conn.execute(
            text("""SELECT row_text, start_page, end_page
                FROM chunks WHERE book_id = :bid
                ORDER BY chunk_index ASC
                LIMIT 2 OFFSET :offset"""),
            {"bid": book_id, "offset": mid}
        ).mappings().all()

        end_chunks = conn.execute(
            text("""SELECT row_text, start_page, end_page
                FROM chunks WHERE book_id = :bid
                ORDER BY chunk_index DESC LIMIT 2"""),
            {"bid": book_id}
        ).mappings().all()

    return {
        "start": [dict(c) for c in start_chunks],
        "middle": [dict(c) for c in middle_chunks],
        "end": [dict(c) for c in end_chunks],
        "total_chunks": total
    }


def simple_extractive_answer(query: str, context_chunks: list) -> str:
    """Simple fallback — context se best matching sentence nikalo"""
    if not context_chunks:
        return "Koi relevant information nahi mili."

    query_words = set(query.lower().split())
    best_sentence = ""
    best_score = 0

    for chunk in context_chunks[:3]:
        sentences = chunk['row_text'].split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            score = len(query_words & set(sentence.lower().split()))
            if score > best_score:
                best_score = score
                best_sentence = sentence

    return best_sentence if best_sentence else context_chunks[0]['row_text'][:300]


def generate_answer(query: str, context_chunks: list) -> str:
    """Groq LLaMA3 se answer generate karo — fallback extractive"""
    if not context_chunks:
        return "Koi relevant information nahi mili."

    context = " ".join([c['row_text'][:800] for c in context_chunks[:3]])

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "user",
                "content": f"You are a helpful assistant. Answer questions based on the given context only. Be concise and accurate.\n\nContext: {context[:2000]}\n\nQuestion: {query}\n\nAnswer clearly and completely."
            }
        ],
        "temperature": 0.3,
        "max_tokens": 2048
    }

    try:
        print(f"🤖 Groq LLaMA3 API call...")
        start = time.time()
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        elapsed = time.time() - start
        print(f"Status: {response.status_code} ({elapsed:.2f}s)")

        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content'].strip()
            print(f"✅ Groq answer: {answer[:500]}")
            return answer

        print(f"⚠️ Groq failed (status {response.status_code}) — fallback to extractive")
        return simple_extractive_answer(query, context_chunks)

    except Exception as e:
        print(f"❌ Groq error: {e} — fallback to extractive")
        return simple_extractive_answer(query, context_chunks)


def chat_with_book(book_id: int, query: str) -> dict:
    """Main chat function"""
    start_time = time.time()

    print(f"\n{'='*60}")
    print(f"📩 USER QUERY  : {query}")
    print(f"📚 BOOK ID     : {book_id}")
    print(f"{'='*60}")

    # Similar past questions
    similar_qs = get_similar_past_questions(query, book_id)

    # Context chunks search
    context_chunks = search_similar_chunks(query, book_id)

    # Answer generate karo
    answer = generate_answer(query, context_chunks)

    # Sources
    sources = [
        {
            "pages": f"Pages {c['start_page']}-{c['end_page']}",
            "similarity": round(float(c['similarity']), 3)
        }
        for c in context_chunks[:6]
    ]

    # Chat history save
    save_chat_history(book_id, query, answer)

    total_time = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"🤖 AI RESPONSE : {answer[:500]}")
    print(f"⏱️  TIME TAKEN  : {total_time:.2f}s")
    print(f"{'='*60}\n")

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
            if float(q["similarity"]) > 0.7
        ],
        "time_taken": round(total_time, 2)
    }


