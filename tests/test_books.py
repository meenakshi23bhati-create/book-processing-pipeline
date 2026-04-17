import pytest   # type: ignore
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_root():
    """API chal rahi hai ya nahi check karo"""
    async with AsyncClient(app=app, base_url="http://test") as client: # pyright: ignore[reportCallIssue]
        response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Book Processing Pipeline Running!"}


@pytest.mark.asyncio
async def test_health():
    """Health endpoint check karo"""
    async with AsyncClient(app=app, base_url="http://test") as client: # pyright: ignore[reportCallIssue]
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_upload_no_file():
    """Bina file ke upload karo — error aana chahiye"""
    async with AsyncClient(app = app, base_url="http://test") as client: # pyright: ignore[reportCallIssue]
        response = await client.post("/books/upload")
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_book_status_not_found():
    """Jo book exist nahi karta uska status check karo"""
    async with AsyncClient(app=app, base_url="http://test") as client: # pyright: ignore[reportCallIssue]
        response = await client.get("/books/99999/status")
    assert response.status_code == 200
    assert "error" in response.json()