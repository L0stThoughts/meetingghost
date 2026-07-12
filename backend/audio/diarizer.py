"""Speaker diarization using pyannote.audio with graceful fallback."""
import logging
from dataclasses import dataclass
from typing import List, Optional

from backend.audio.transcriber import TranscriptSegment

logger = logging.getLogger(__name__)


@dataclass
class SpeakerSegment:
    speaker_label: str
    start: float
    end: float


@dataclass
class DiarizedSegment:
    speaker: str
    start: float
    end: float
    text: str


class SpeakerDiarizer:
    def __init__(self, hf_token: Optional[str] = None, num_speakers: Optional[int] = None) -> None:
        self.hf_token = hf_token
        self.num_speakers = num_speakers
        self._pipeline = None
        self._available = True
        self._load_pipeline()

    def _load_pipeline(self) -> None:
        try:
            from pyannote.audio import Pipeline
            if not self.hf_token:
                logger.warning("No HF token provided; diarization may fail for gated models")
            self._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.hf_token,
            )
            logger.info("Pyannote diarization pipeline loaded")
        except Exception as exc:
            logger.warning("Pyannote unavailable (%s), will use fallback", exc)
            self._available = False

    def diarize(self, audio_path: str) -> List[SpeakerSegment]:
        if not self._available or self._pipeline is None:
            logger.info("Using single-speaker fallback")
            return [SpeakerSegment(speaker_label="Speaker 1", start=0.0, end=999999.0)]

        try:
            params = {}
            if self.num_speakers is not None:
                params["num_speakers"] = self.num_speakers
            diarization = self._pipeline(audio_path, **params)

            segments: List[SpeakerSegment] = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append(SpeakerSegment(
                    speaker_label=speaker,
                    start=turn.start,
                    end=turn.end,
                ))
            logger.info("Diarization complete: %d segments", len(segments))
            return segments if segments else [SpeakerSegment("Speaker 1", 0.0, 999999.0)]
        except Exception as exc:
            logger.error("Diarization failed: %s", exc)
            return [SpeakerSegment(speaker_label="Speaker 1", start=0.0, end=999999.0)]

    def assign_speakers_to_transcript(
        self,
        transcript_segments: List[TranscriptSegment],
        speaker_segments: List[SpeakerSegment],
    ) -> List[DiarizedSegment]:
        result: List[DiarizedSegment] = []
        for ts in transcript_segments:
            mid = (ts.start + ts.end) / 2.0
            best_speaker = "Speaker 1"
            best_overlap = 0.0
            for ss in speaker_segments:
                overlap_start = max(ts.start, ss.start)
                overlap_end = min(ts.end, ss.end)
                overlap = max(0.0, overlap_end - overlap_start)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = ss.speaker_label
            result.append(DiarizedSegment(
                speaker=best_speaker,
                start=ts.start,
                end=ts.end,
                text=ts.text,
            ))
        return result
