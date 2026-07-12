"""SQLite database setup with SQLAlchemy and FTS5 virtual table.

Provides engine, SessionLocal, Base, get_db dependency, and init_db().
"""
import logging
import os
from sqlalchemy import create_engine, event, text, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from typing import Generator
from backend.config import settings

logger = logging.getLogger(__name__)

DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL.startswith("sqlite:///./"):
    path = DATABASE_URL.replace("sqlite:///./", "")
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
    except Exception:
        pass


def get_db() -> Generator:
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all ORM tables and FTS5 virtual tables."""
    from backend import models as _models  # noqa: F401 – triggers table registration
    Base.metadata.create_all(bind=engine)
    logger.info("ORM tables created")

    with engine.begin() as conn:
        conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS transcripts_fts "
            "USING fts5(meeting_id UNINDEXED, speaker, text, content='transcripts', "
            "content_rowid='id');"
        ))
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS transcript_embeddings ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "meeting_id INTEGER NOT NULL, "
            "segment_index INTEGER NOT NULL, "
            "speaker TEXT, "
            "start_time REAL, "
            "end_time REAL, "
            "text TEXT NOT NULL, "
            "embedding TEXT NOT NULL, "
            "FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE);"
        ))
    logger.info("FTS5 and embeddings tables created")
