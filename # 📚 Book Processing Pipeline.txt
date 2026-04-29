# 📚 Book Processing Pipeline

A production-grade AI-powered system to upload books (PDFs), process them into chunks, and chat with them using RAG (Retrieval Augmented Generation) architecture.

---

## 🏗️ Architecture Overview

```
User Query
    ↓
Frontend (React)
    ↓
FastAPI Backend
    ↓
Chat Service (RAG Pipeline)
    ↓
┌─────────────────┬──────────────────┬─────────────────┐
│  Provider 1     │   pgvector DB    │   Provider 2    │
│  Local Embedding│  Vector + Keyword│   Groq Cloud    │
│  BAAI/bge-base  │     Search       │  llama-3.3-70b  │
└─────────────────┴──────────────────┴─────────────────┘
    ↓
Response (Answer + Sources + Time)
    ↓
PostgreSQL (Chat History Save)
```

---

## 🤖 AI Providers

| Provider       | Type           | Model                     | Task                      |
| **Provider 1** | Local          | `BAAI/bge-base-en-v1.5`   | Text Embedding (768 dims) |
| **Provider 2** | Groq Cloud API | `llama-3.3-70b-versatile` | Answer Generation         |

---

## 🗂️ Project Structure

```
book-processing-pipeline/
│
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── books.py          # Book upload & management
│   │       ├── chat.py           # Chat endpoint
│   │       └── chunks.py         # Chunks management
│   ├── core/
│   │   ├── config.py             # App settings & env variables
│   │   └── database.py           # DB connection
│   ├── models/
│   │   ├── books.py              # Book DB model
│   │   ├── chunks.py             # Chunk DB model
│   │   └── chat_history.py       # Chat history DB model
│   ├── schemas/
│   │   ├── books.py              # Request/Response schemas
│   │   └── chunks.py             # Chunk schemas
│   ├── service/
│   │   ├── chat_service.py       # Core RAG logic
│   │   ├── chat_history_service.py # Chat history management
│   │   ├── processor.py          # PDF processing
│   │   ├── splitter.py           # Text chunking
│   │   └── exporter.py           # Export to CSV
│   └── worker/
│       ├── celery.py             # Celery configuration
│       └── task.py               # Background tasks
│
├── frontend/
│   └── src/
│       └── App.js                # React UI
│
├── migrations/                   # Alembic DB migrations
├── tests/
│   ├── conftest.py               # Test configuration
│   ├── test_books.py             # Book tests
│   └── test_chunks.py            # Chunk tests
│
├── uploads/                      # Uploaded PDF files
├── chat_history_csv/             # Exported chat history
├── .env                          # Environment variables
├── docker-compose.yml            # Docker services
├── dockerfile                    # Docker image
├── requirements.txt              # Python dependencies
└── main.py                       # FastAPI entry point
```

---

## ⚙️ Tech Stack

| Layer                         | Technology                                  |
| **Backend**                   | FastAPI (Python 3.10)                       |
| **Frontend**                  | React (App.js)                              |
| **Database**                  | PostgreSQL + pgvector                       |
| **Task Queue**                | Celery + Redis                              |
| **Worker Monitor**            | Flower Dashboard                            |
| **Containerization**          | Docker + Docker Compose                     |
| **Embedding**                 | SentenceTransformer (BAAI/bge-base-en-v1.5) |
| **LLM**                       | Groq API (llama-3.3-70b-versatile)          |
| **Migrations**                | Alembic                                     |

---

## 🚀 Setup & Installation

### Prerequisites
- Docker Desktop installed
- Git installed

### Step 1 — Clone the repository
```bash
git clone <repo-url>
cd book-processing-pipeline
```

### Step 2 — Create `.env` file
```env
DATABASE_URL=postgresql+asyncpg://bookuser:bookpass@db:5432/bookdb
REDIS_URL=redis://redis:6379/0
HF_API_KEY=your_huggingface_key
GROQ_API_KEY=your_groq_key
API_KEY
CHUNK_SIZE=20
OUTPUT_DIR=./output
```

### Step 3 — Start all services
```bash
docker-compose up --build -d
```

### Step 4 — Open the app
| Service           | URL                           |
| Frontend          | http://localhost:3000         |
| Backend API       | http://localhost:8000         |
| API Docs          | http://localhost:8000/docs    |
| Flower Monitor    | http://localhost:5555         |



## 📖 How to Use

### 1. Upload a Book
- Open frontend at `http://localhost:3000`
- Click **Upload Book**
- Select a PDF file
- Wait for processing to complete

### 2. Chat with the Book
- Select a book from the list
- Type your question
- Get AI-powered answers with sources

### Example Questions
```
What is this book about?
What are the main keywords?
What methodology was used?
Give me a summary in 5 points
Who are the authors?
What are the conclusions?
```

---

## 🔍 RAG Pipeline (Data Retrieval)

| Step  | What Happens              | Technology        |
| 1     | User query received       | FastAPI           |
| 2     | Query → 768-dim vector    | Local BAAI model  |
| 3     | Vector similarity search  | pgvector cosine   |
| 4     | Keyword match search      | PostgreSQL ILIKE  |
| 5     | Hybrid merge              | Deduplication     |
| 6     | Context build             | Top 3 chunks      |
| 7     | Answer generation         | Groq llama-3.3-70b|
| 8     | Save to history           | PostgreSQL        |

---

## 🗃️ Database Tables

| Table | Purpose |
|---|---|
| `books` | Uploaded books metadata |
| `chunks` | Book text chunks + embeddings |
| `chat_history` | Q&A history + embeddings |

---

## 🐳 Docker Services

| Service       | Port          | Purpose                   |
| `api`         | 8000          | FastAPI backend           |
| `frontend`    | 3000          | React UI                  |
| `postgres_db` | 5432          | PostgreSQL + pgvector     |
| `redis`       | 6379          | Task queue                |
| `worker`      | —             | Celery background worker  |
| `flower`      | 5555          | Worker monitor            |

---

## 📊 API Endpoints

| Method    | Endpoint                  | Purpose           |
| `POST`    | `/books/upload`           | Upload a PDF book |
| `GET`     | `/chat/books`             | Get all books     |
| `POST`    | `/chat`                   | Chat with a book  |
| `GET`     | `/chat/memory/{book_id}`  | Get book memory   |
| `GET`     | `/chat/history/{book_id}` | Get chat history  |


Also get BOOK status and Book Processing there in Swagger...
---

## 🧪 Running Tests

```bash
docker-compose exec api pytest tests/ -v
```

---

## 📤 Export Chat History

Chat history can be exported to CSV:

```bash
docker exec postgres_db psql -U bookuser -d bookdb -c "\COPY (SELECT id, book_id, question, answer, created_at FROM chat_history ORDER BY created_at DESC) TO '/tmp/chat_history.csv' CSV HEADER;"

docker cp postgres_db:/tmp/chat_history.csv ./chat_history_csv/
```

---

## 👨‍💻 Developer Notes

- Embedding model loads once at startup for performance
- Vector search uses cosine similarity (`<=>` operator)
- Hybrid search combines vector + keyword results
- Chat history is also embedded for similar question lookup
- `CHUNK_SIZE=20` means 20 page = 1 chunk (recommended)

---

## 📝 License

This project is for educational and research purposes.