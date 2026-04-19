"""
database.py
-----------
Sets up the async SQLAlchemy engine and session factory.
Using async I/O ensures the FastAPI server never blocks on DB queries.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import DATABASE_URL

# The async engine manages the actual SQLite connection pool
engine = create_async_engine(DATABASE_URL, echo=False)

# Session factory — each request gets its own session
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

class Base(DeclarativeBase):
    """All ORM models inherit from this base class."""
    pass


async def get_db():
    """
    FastAPI dependency that yields an async DB session per request.
    The 'finally' block guarantees the session closes even on errors.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables on application startup."""
    async with engine.begin() as conn:
        from models.db_models import Flight, TrajectoryPoint  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)