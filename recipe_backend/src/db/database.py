import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def _build_database_url() -> str:
    """
    Construct the async SQLAlchemy database URL from environment variables.

    Env vars are provided by the Postgres container contract:
    POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT

    POSTGRES_URL may already be a DSN; we treat it as authoritative when set.
    """
    postgres_url = os.getenv("POSTGRES_URL")
    if postgres_url:
        # Normalize to asyncpg driver when user provided a sync DSN.
        if postgres_url.startswith("postgresql://"):
            return postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if postgres_url.startswith("postgresql+asyncpg://"):
            return postgres_url
        # If some other scheme is provided, use it as-is.
        return postgres_url

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB")
    port = os.getenv("POSTGRES_PORT")
    # Host is typically a service name in docker, but not provided as env var by contract.
    # For local dev in this environment, Postgres is reachable via localhost.
    host = os.getenv("POSTGRES_HOST", "localhost")

    missing = [k for k, v in {
        "POSTGRES_USER": user,
        "POSTGRES_PASSWORD": password,
        "POSTGRES_DB": db,
        "POSTGRES_PORT": port,
    }.items() if not v]
    if missing:
        raise RuntimeError(
            "Missing required database environment variables: "
            + ", ".join(missing)
            + ". Please ensure .env provides Postgres connection settings."
        )

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


_ENGINE: Optional[AsyncEngine] = None
_SESSIONMAKER: Optional[async_sessionmaker[AsyncSession]] = None


# PUBLIC_INTERFACE
def get_engine() -> AsyncEngine:
    """Get (and lazily initialize) the global AsyncEngine."""
    global _ENGINE, _SESSIONMAKER
    if _ENGINE is None:
        _ENGINE = create_async_engine(
            _build_database_url(),
            pool_pre_ping=True,
        )
        _SESSIONMAKER = async_sessionmaker(_ENGINE, expire_on_commit=False)
    return _ENGINE


# PUBLIC_INTERFACE
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Get the async sessionmaker tied to the global engine."""
    if _SESSIONMAKER is None:
        get_engine()
    assert _SESSIONMAKER is not None
    return _SESSIONMAKER


# PUBLIC_INTERFACE
@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Async context manager that yields an AsyncSession and commits/rolls back safely."""
    session = get_sessionmaker()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
