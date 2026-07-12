"""Whisper transcriber using faster-whisper."""
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    words: Optional[List[dict]] = None


@dataclass
class TranscriptionResult:
    full_text: str
    segments: List[TranscriptSegment]
    language: str
    duration_seconds: float


class WhisperTranscriber:
    VALID_SIZES = ("tiny", "base", "small", "medium")

    def __init__(self, model_size: str = "base", device: str = "cpu") -> None:
        if model_size not in self.VALID_SIZES:
            logger.warning("Unknown model size '%s', falling back to 'base'", model_size)
            model_size = "base"
        self.model_size = model_size
        self.device = device
        self._model = None

    def _load_model(self):  # type: ignore[no-untyped-def]
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
            logger.info("Loading Whisper model '%s' on '%s'...", self.model_size, self.device)
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type="int8" if self.device == "cpu" else "float16",
            )
            logger.info("Whisper model loaded")
        except ImportError:
            logger.error("faster-whisper not installed")
            raise
        return self._model

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        model = self._load_model()
        segments_gen, info = model.transcribe(audio_path, beam_size=5)

        segments: List[TranscriptSegment] = []
        full_parts: List[str] = []
        for seg in segments_gen:
            text = seg.text.strip()
            words = None
            if hasattr(seg, "words") and seg.words:
                words = [{"start": w.start, "end": w.end, "word": w.word} for w in seg.words]
            segments.append(TranscriptSegment(start=seg.start, end=seg.end, text=text, words=words))
            full_parts.append(text)

        return TranscriptionResult(
            full_text=" ".join(full_parts),
            segments=segments,
            language=info.language,
            duration_seconds=info.duration,
        )

    def transcribe_with_timestamps(self, audio_path: str) -> List[TranscriptSegment]:
        result = self.transcribe(audio_path)
        return result.segments
