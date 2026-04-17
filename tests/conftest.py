import pytest
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    """Async tests ke liye event loop"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()