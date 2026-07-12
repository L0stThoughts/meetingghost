"""Audio recorder using sounddevice."""
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import numpy as np

logger = logging.getLogger(__name__)


class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self._recording = False
        self._frames: List[np.ndarray] = []
        self._thread: Optional[threading.Thread] = None
        self._output_dir = Path("data/recordings")
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _record_loop(self) -> None:
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice not installed")
            return

        block_duration = 0.5
        block_size = int(self.sample_rate * block_duration)
        try:
            stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                blocksize=block_size,
            )
            stream.start()
            logger.info("Recording started")
            while self._recording:
                data, _ = stream.read(block_size)
                self._frames.append(data.copy())
            stream.stop()
            stream.close()
        except Exception as exc:
            logger.error("Recording error: %s", exc)

    def start_recording(self) -> None:
        if self._recording:
            logger.warning("Already recording")
            return
        self._frames = []
        self._recording = True
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def stop_recording(self) -> str:
        if not self._recording:
            logger.warning("Not recording")
            return ""
        self._recording = False
        if self._thread:
            self._thread.join(timeout=5)

        if not self._frames:
            logger.warning("No audio frames captured")
            return ""

        audio_data = np.concatenate(self._frames, axis=0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.wav"
        output_path = self._output_dir / filename

        try:
            from scipy.io import wavfile
            wavfile.write(str(output_path), self.sample_rate, audio_data)
            logger.info("Saved recording to %s", output_path)
        except ImportError:
            logger.error("scipy not installed, cannot save WAV")
            return ""
        except Exception as exc:
            logger.error("Failed to save WAV: %s", exc)
            return ""

        return str(output_path)

    def record_for_duration(self, seconds: int, output_path: str) -> str:
        try:
            import sounddevice as sd
            from scipy.io import wavfile
        except ImportError as exc:
            logger.error("Missing dependency: %s", exc)
            return ""

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            logger.info("Recording %d seconds to %s", seconds, output_path)
            audio = sd.rec(
                int(seconds * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
            )
            sd.wait()
            wavfile.write(output_path, self.sample_rate, audio)
            logger.info("Saved recording to %s", output_path)
            return output_path
        except Exception as exc:
            logger.error("Recording failed: %s", exc)
            return ""
