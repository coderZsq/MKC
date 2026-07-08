from __future__ import annotations

import wave
from pathlib import Path

import ffmpeg

from app.core.exceptions import AudioProcessingError


class AudioProcessor:
    """Convert and inspect audio files for ASR processing."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate

    def convert_to_wav(self, source: Path, target: Path) -> Path:
        """Convert any ffmpeg-readable audio to a 16kHz mono PCM WAV file."""
        try:
            ffmpeg.input(str(source)).output(
                str(target),
                ar=self.sample_rate,
                ac=1,
                acodec="pcm_s16le",
            ).run(overwrite_output=True, quiet=True)
        except ffmpeg.Error as exc:
            stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
            raise AudioProcessingError(f"ffmpeg convert failed: {stderr}") from exc
        except Exception as exc:
            raise AudioProcessingError(f"audio conversion failed: {exc}") from exc
        return target

    def get_duration(self, wav_path: Path) -> float:
        """Return the duration of a WAV file in seconds."""
        try:
            with wave.open(str(wav_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate == 0:
                    raise AudioProcessingError("invalid WAV: zero sample rate")
                return frames / rate
        except AudioProcessingError:
            raise
        except Exception as exc:
            raise AudioProcessingError(f"failed to read audio duration: {exc}") from exc
