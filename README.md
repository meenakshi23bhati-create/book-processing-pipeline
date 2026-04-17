# 📚 Book Processing Pipeline

A scalable backend system that uploads PDF books, splits them into chunks, and processes them asynchronously using Celery workers.

## 🚀 Features

- Upload PDF books via REST API
- Automatic chunking of large PDFs (500+ pages)
- Async background processing with Celery
- PostgreSQL + pgvector for storage
- Redis as message broker
- Flower dashboard for task monitoring
- FastAPI with auto-generated Swagger docs

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI |
| Task Queue | Celery |
| Broker | Redis |
| Database | PostgreSQL + pgvector |
| Monitoring | Flower |
| Containerization | Docker + Docker Compose |

## 📁 Project Structure

```
book-processing-pipeline/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── books.py       # Book upload & chunk endpoints
│   │       └── chunks.py      # Chunk retrieval endpoints
│   ├── core/
│   │   ├── config.py          # Environment configuration
│   │   └── database.py        # Async SQLAlchemy setup
│   ├── models/
│   │   ├── books.py           # Book ORM model
│   │   └── chunks.py          # Chunk ORM model
│   ├── service/
│   │   ├── processor.py       # Chunk processing logic
│   │   └── splitter.py        # PDF splitting logic
│   └── workers/
│       ├── celery.py          # Celery app configuration
│       └── task.py            # Celery tasks
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── init.sql
```

## ⚙️ Setup & Installation

### Prerequisites
- Docker & Docker Compose installed

### 1. Clone the repository
```bash
git clone https://github.com/meenakshi23bhati-create/book-processing-pipeline.git
cd book-processing-pipeline
```

### 2. Create `.env` file
```env
DATABASE_URL=postgresql+asyncpg://bookuser:bookpass@db:5432/bookdb
SYNC_DATABASE_URL=postgresql://bookuser:bookpass@db:5432/bookdb
```

### 3. Run with Docker Compose
```bash
docker-compose up --build
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/books/Upload` | Upload a PDF book |
| GET | `/books/{book_id}/chunks` | Get all chunks of a book |
| GET | `/chunks/{chunk_id}` | Get a specific chunk |
| GET | `/chunks/book/{book_id}` | Get all chunks by book ID |

## 🖥️ Access

| Service | URL |
|---------|-----|
| API Docs (Swagger) | http://localhost:8000/docs |
| Flower Dashboard | http://localhost:5555 |

## 📖 How It Works

1. User uploads a PDF via `POST /books/Upload`
2. Book record is created in PostgreSQL with status `pending`
3. Celery task `process_book` is dispatched
4. PDF is split into chunks (by page range)
5. Each chunk is processed by `process_single_chunk` task
6. Chunks are saved to PostgreSQL
7. Book status updated to `done`

## 📊 Monitoring

Open Flower dashboard at `http://localhost:5555` to monitor:
- Active tasks
- Completed tasks
- Failed tasks
- Worker status
