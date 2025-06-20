"""
Wolfstitch Cloud - Database Configuration
Week 1 implementation with SQLite
"""

import asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

# Create base class for models
Base = declarative_base()

# Create engines
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite for development
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    
    # For async operations, use aiosqlite
    async_engine = create_async_engine(
        settings.database_url_async,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL for production
    engine = create_engine(settings.DATABASE_URL)
    async_engine = create_async_engine(settings.database_url_async)

# Create session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

async def create_tables():
    """Create database tables"""
    try:
        # For Week 1, we'll create tables when we have models
        # For now, just ensure the database file exists for SQLite
        if settings.DATABASE_URL.startswith("sqlite"):
            # SQLite will create the file when we first connect
            pass
        
        logger.info("Database tables initialized")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

def get_sync_db():
    """Get synchronous database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()