from fastapi import FastAPI
from app.models import books
from app.api.routes import books, chunks
from app.core.database import init_db


app= FastAPI(
    title="Book processing pipline",
    description="500 page book ko chunk mein split kar ke process karna",
    version= "1.0.0",
)



app.include_router(books.router)
app.include_router(chunks.router)

@app.on_event("startup")
async def on_startup():
    await init_db()
@app.get("/")
async def root():
    return{"message":"Book processing pipline running!"}

@app.get("/health")
async def health():
    return{"status": "ok"}