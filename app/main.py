from fastapi import FastAPI
from app.models import books
from app.models import chunks
from app.api.routes import books, chunks,chat
from app.core.database import Base, init_db,engine
from fastapi.middleware.cors import CORSMiddleware
from app.models.chat_history import ChatHistory
import sqlalchemy
from app.core.config import settings

sync_engine = sqlalchemy.create_engine(settings.SYNC_DATABASE_URL)
Base.metadata.create_all(bind=sync_engine)
app= FastAPI(
    title="Book processing pipline",
    description="500 page book ko chunk mein split kar ke process karna",
    version= "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(books.router)
app.include_router(chunks.router)
app.include_router(chat.router, tags=["Chat"])

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.get("/")
async def root():
    return{"message":"Book processing pipline running!"}

@app.get("/health")
async def health():
    return{"status": "ok"}