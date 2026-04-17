from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


# ✅ Pehle Base define karo
class Base(DeclarativeBase):
    pass


# ✅ models import HATAO — circular import ka cause hai
engine = create_async_engine(settings.DATABASE_URL, echo=True, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=True
)


async def init_db():
    # ✅ Models yahan import karo — circular import avoid hoga
    from app.models import books, chunks  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
        