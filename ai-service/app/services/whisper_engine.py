from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

try:  # pragma: no cover
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover
    WhisperModel = None

from app.core.exceptions import ModelLoadError


class WhisperEngine:
    """Wrapper around faster-whisper for local ASR inference."""

    def __init__(
        self,
        model_name: str,
        device: str = "auto",
        compute_type: str = "int8",
        model_dir: str | Path = "/models/whisper",
        beam_size: int = 5,
        best_of: int = 5,
        vad_filter: bool = True,
        vad_parameters: dict[str, Any] | None = None,
        chunk_length: int = 30,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.model_dir = Path(model_dir)
        self.beam_size = beam_size
        self.best_of = best_of
        self.vad_filter = vad_filter
        self.vad_parameters = vad_parameters or {}
        self.chunk_length = chunk_length
        self._model: Any | None = None

    def load(self) -> None:
        """Load the faster-whisper model; raises ModelLoadError on failure."""
        if WhisperModel is None:
            raise ModelLoadError("faster-whisper is not installed")
        try:
            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                download_root=str(self.model_dir),
            )
        except Exception as exc:
            raise ModelLoadError(f"failed to load whisper model {self.model_name}: {exc}") from exc

    def transcribe(
        self,
        audio_path: Path,
        language: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Transcribe an audio file and yield segment dictionaries."""
        if self._model is None:
            self.load()
        if self._model is None:
            raise ModelLoadError("whisper model is not available")

        segments, _info = self._model.transcribe(
            str(audio_path),
            language=language,
            beam_size=self.beam_size,
            best_of=self.best_of,
            vad_filter=self.vad_filter,
            vad_parameters=self.vad_parameters,
            chunk_length=self.chunk_length,
            condition_on_previous_text=True,
        )
        for segment in segments:
            yield {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "confidence": segment.avg_logprob,
            }
