"""FastAPI application for MeetingGhost."""
import asyncio
import json
import logging
import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from backend.config import settings, Settings
from backend.database import SessionLocal, init_db, get_db
from backend.models import Meeting, Transcript, MeetingRead, TranscriptRead, SearchResultSchema
from backend.audio.recorder import AudioRecorder
from backend.pipeline.processor import MeetingProcessor, get_progress
from backend.intelligence.embedder import TextEmbedder
from backend.search.search_engine import MeetingSearchEngine

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DATA_DIR = Path("data/recordings")
DATA_DIR.mkdir(parents=True, exist_ok=True)

_recorder = AudioRecorder()
_processing_tasks: dict[int, asyncio.Task] = {}  # type: ignore[type-arg]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    logger.info("Database initialized")
    yield


app = FastAPI(title="MeetingGhost API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/meetings", response_model=list[MeetingRead])
def list_meetings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list:
    meetings = db.query(Meeting).order_by(Meeting.created_at.desc()).offset(skip).limit(limit).all()
    results = []
    for m in meetings:
        results.append(MeetingRead(
            id=m.id, title=m.title,
            created_at=str(m.created_at) if m.created_at else None,
            audio_path=m.audio_path, duration_seconds=m.duration_seconds,
            summary=m.summary, one_liner=m.one_liner,
            key_points=m.key_points, decisions=m.decisions,
            action_items=m.action_items, status=m.status,
        ))
    return results


@app.get("/meetings/{meeting_id}")
def get_meeting(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    transcripts = db.query(Transcript).filter(
        Transcript.meeting_id == meeting_id
    ).order_by(Transcript.start_time).all()

    return {
        "meeting": MeetingRead.model_validate(meeting).model_dump(),
        "transcripts": [TranscriptRead.model_validate(t).model_dump() for t in transcripts],
    }


@app.post("/meetings/upload")
async def upload_meeting(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
) -> dict:
    filename = Path(file.filename or "upload.wav").name
    out_path = DATA_DIR / filename
    with out_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    meeting = Meeting(audio_path=str(out_path), status="processing")
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    async def _process(mid: int, path: str) -> None:
        proc_db = SessionLocal()
        try:
            processor = MeetingProcessor(settings, proc_db)
            await processor.process_audio_file(path, mid)
        except Exception as exc:
            logger.error("Processing failed for meeting %d: %s", mid, exc)
            m = proc_db.query(Meeting).filter(Meeting.id == mid).first()
            if m:
                m.status = "error"
                proc_db.commit()
        finally:
            proc_db.close()

    task = asyncio.create_task(_process(meeting.id, str(out_path)))
    _processing_tasks[meeting.id] = task

    return {"meeting_id": meeting.id, "status": "processing"}


@app.get("/meetings/{meeting_id}/status")
async def meeting_status_stream(meeting_id: int) -> EventSourceResponse:
    async def event_generator() -> AsyncGenerator[dict, None]:
        last_idx = 0
        while True:
            progress = get_progress(meeting_id)
            while last_idx < len(progress):
                yield {"data": progress[last_idx]}
                last_idx += 1
            if any(p.startswith("Processing complete") for p in progress):
                yield {"data": "[DONE]"}
                return
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())


@app.delete("/meetings/{meeting_id}")
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)) -> dict:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    db.query(Transcript).filter(Transcript.meeting_id == meeting_id).delete()
    db.delete(meeting)
    db.commit()
    return {"deleted": meeting_id}


@app.post("/record/start")
def start_recording() -> dict:
    _recorder.start_recording()
    return {"status": "recording"}


@app.post("/record/stop")
async def stop_recording(db: Session = Depends(get_db)) -> dict:
    path = _recorder.stop_recording()
    if not path:
        raise HTTPException(status_code=400, detail="No recording to stop or save failed")

    meeting = Meeting(audio_path=path, status="processing")
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    async def _process(mid: int, audio_path: str) -> None:
        proc_db = SessionLocal()
        try:
            processor = MeetingProcessor(settings, proc_db)
            await processor.process_audio_file(audio_path, mid)
        except Exception as exc:
            logger.error("Processing failed: %s", exc)
            m = proc_db.query(Meeting).filter(Meeting.id == mid).first()
            if m:
                m.status = "error"
                proc_db.commit()
        finally:
            proc_db.close()

    task = asyncio.create_task(_process(meeting.id, path))
    _processing_tasks[meeting.id] = task

    return {"meeting_id": meeting.id, "status": "processing"}


@app.get("/search")
def search_meetings(
    q: str = Query(..., min_length=1),
    mode: str = Query("hybrid", pattern="^(fts|semantic|hybrid)$"),
    db: Session = Depends(get_db),
) -> list[dict]:
    embedder = TextEmbedder(settings.SENTENCE_TRANSFORMER_MODEL)
    engine = MeetingSearchEngine(db, embedder)

    if mode == "fts":
        results = engine.search_fts(q)
    elif mode == "semantic":
        results = engine.search_semantic(q)
    else:
        results = engine.search_hybrid(q)

    return [
        {"meeting_id": r.meeting_id, "snippet": r.snippet, "score": r.score,
         "speaker": r.speaker, "timestamp": r.timestamp}
        for r in results
    ]
