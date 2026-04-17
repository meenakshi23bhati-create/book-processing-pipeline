import pytest  # type: ignore
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_get_chunks_not_found():
    """Jo book nahi hai uske chunks maango"""
    async with AsyncClient(app=app, base_url="http://test") as client: # pyright: ignore[reportCallIssue]
        response = await client.get("/chunks/book/99999")
    assert response.status_code == 200
    assert response.json()["total_chunks"] == 0


@pytest.mark.asyncio
async def test_get_single_chunk_not_found():
    """Jo chunk nahi hai use maango"""
    async with AsyncClient(app=app, base_url="http://test") as client: # pyright: ignore[reportCallIssue]
        response = await client.get("/chunks/99999")
    assert response.status_code == 200
    assert "error" in response.json()