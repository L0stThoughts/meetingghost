"""SQLAlchemy models and Pydantic schemas for MeetingGhost."""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from backend.database import Base
from pydantic import BaseModel
from typing import Optional, List


class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    audio_path = Column(String(1024), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    one_liner = Column(String(512), nullable=True)
    key_points = Column(Text, nullable=True)
    decisions = Column(Text, nullable=True)
    action_items = Column(Text, nullable=True)
    status = Column(String(32), default="pending")


class Transcript(Base):
    __tablename__ = "transcripts"
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, nullable=False, index=True)
    speaker = Column(String(128), nullable=True)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    text = Column(Text, nullable=False)


# --- Pydantic schemas ---

class MeetingCreate(BaseModel):
    title: Optional[str] = None
    audio_path: Optional[str] = None


class MeetingRead(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: Optional[str] = None
    audio_path: Optional[str] = None
    duration_seconds: Optional[int] = None
    summary: Optional[str] = None
    one_liner: Optional[str] = None
    key_points: Optional[str] = None
    decisions: Optional[str] = None
    action_items: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


class TranscriptRead(BaseModel):
    id: int
    meeting_id: int
    speaker: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    text: str

    class Config:
        from_attributes = True


class SearchResultSchema(BaseModel):
    meeting_id: int
    snippet: str
    score: float
    speaker: Optional[str] = None
    timestamp: Optional[float] = None
