"""Processing pipeline: audio → transcription → diarization → intelligence → index."""
import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from sqlalchemy.orm import Session

from backend.config import Settings
from backend.audio.transcriber import WhisperTranscriber, TranscriptSegment
from backend.audio.diarizer import SpeakerDiarizer, DiarizedSegment
from backend.intelligence.action_extractor import ActionExtractor, ActionItem
from backend.intelligence.summarizer import MeetingSummarizer, MeetingSummary
from backend.intelligence.embedder import TextEmbedder
from backend.search.search_engine import MeetingSearchEngine

logger = logging.getLogger(__name__)

# Simple in-memory event queue for SSE
_progress: Dict[int, List[str]] = defaultdict(list)


def get_progress(meeting_id: int) -> List[str]:
    return _progress.get(meeting_id, [])


def _emit(meeting_id: int, msg: str) -> None:
    _progress[meeting_id].append(msg)
    logger.info("Meeting %d: %s", meeting_id, msg)


@dataclass
class ProcessingResult:
    meeting_id: int
    transcript_segments: List[DiarizedSegment]
    action_items: List[ActionItem]
    summary: MeetingSummary
    duration_seconds: float
    processing_time_seconds: float


class MeetingProcessor:
    def __init__(self, settings: Settings, db_session: Session) -> None:
        self.settings = settings
        self.db = db_session
        self.transcriber = WhisperTranscriber(device=settings.TRANSCRIBER_DEVICE)
        self.diarizer = SpeakerDiarizer()
        self.summarizer = MeetingSummarizer(settings.OLLAMA_API_URL, settings.OLLAMA_MODEL)
        self.action_extractor = ActionExtractor(settings.OLLAMA_API_URL, settings.OLLAMA_MODEL)
        self.embedder = TextEmbedder(settings.SENTENCE_TRANSFORMER_MODEL)
        self.search_engine = MeetingSearchEngine(db_session, self.embedder)

    async def process_audio_file(self, audio_path: str, meeting_id: int) -> ProcessingResult:
        start_time = time.time()

        # 1. Transcribe
        _emit(meeting_id, "Transcribing audio...")
        transcription = await asyncio.to_thread(self.transcriber.transcribe, audio_path)
        _emit(meeting_id, f"Transcription done: {len(transcription.segments)} segments")

        # 2. Diarize
        _emit(meeting_id, "Diarizing speakers...")
        try:
            speaker_segments = await asyncio.to_thread(self.diarizer.diarize, audio_path)
            diarized = self.diarizer.assign_speakers_to_transcript(
                transcription.segments, speaker_segments
            )
        except Exception as exc:
            logger.warning("Diarization failed, using undiarized: %s", exc)
            diarized = [
                DiarizedSegment(speaker="Speaker 1", start=s.start, end=s.end, text=s.text)
                for s in transcription.segments
            ]
        _emit(meeting_id, f"Diarization done: {len(diarized)} segments")

        full_transcript = "\n".join(f"[{s.speaker}] {s.text}" for s in diarized)
        speakers = list({s.speaker for s in diarized})

        # 3. Extract action items
        _emit(meeting_id, "Extracting action items...")
        action_items = await self.action_extractor.extract(full_transcript, speakers)
        _emit(meeting_id, f"Found {len(action_items)} action items")

        # 4. Summarize
        _emit(meeting_id, "Summarizing...")
        summary = await self.summarizer.summarize(
            full_transcript, int(transcription.duration_seconds)
        )
        _emit(meeting_id, "Summary complete")

        # 5. Embed & index
        _emit(meeting_id, "Indexing for search...")
        await asyncio.to_thread(self.search_engine.index_transcript, meeting_id, diarized)

        # 6. Store in DB
        from backend.models import Meeting, Transcript
        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if meeting:
            meeting.title = summary.title
            meeting.one_liner = summary.one_liner
            meeting.summary = full_transcript[:500]
            meeting.key_points = json.dumps(summary.key_points)
            meeting.decisions = json.dumps(summary.decisions)
            meeting.action_items = json.dumps([
                {"description": a.description, "assignee": a.assignee,
                 "due_date": a.due_date, "priority": a.priority}
                for a in action_items
            ])
            meeting.duration_seconds = int(transcription.duration_seconds)
            meeting.status = "complete"
            self.db.commit()

        for i, seg in enumerate(diarized):
            t = Transcript(
                meeting_id=meeting_id, speaker=seg.speaker,
                start_time=seg.start, end_time=seg.end, text=seg.text,
            )
            self.db.add(t)
        self.db.commit()

        processing_time = time.time() - start_time
        _emit(meeting_id, f"Processing complete in {processing_time:.1f}s")

        return ProcessingResult(
            meeting_id=meeting_id,
            transcript_segments=diarized,
            action_items=action_items,
            summary=summary,
            duration_seconds=transcription.duration_seconds,
            processing_time_seconds=processing_time,
        )

    async def process_recording(self, recording_path: str) -> ProcessingResult:
        from backend.models import Meeting
        meeting = Meeting(audio_path=recording_path, status="processing")
        self.db.add(meeting)
        self.db.commit()
        self.db.refresh(meeting)
        return await self.process_audio_file(recording_path, meeting.id)
