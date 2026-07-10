from __future__ import annotations

import logging
from typing import Any, cast

logger = logging.getLogger(__name__)


class TokenEstimator:
    """Token-length estimator with a tiktoken-first, character-count fallback.

    When ``tiktoken`` is available the ``cl100k_base`` encoding is used. If the
    encoder cannot be loaded (missing dependency, unsupported platform, etc.) the
    estimator falls back to a one-character-per-token approximation so that
    chunkers can still enforce size limits.
    """

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        self._encoder: Any | None = None
        try:
            import tiktoken

            self._encoder = tiktoken.get_encoding(encoding_name)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning(
                "Failed to load tiktoken encoding %s: %s. "
                "Falling back to character-count token estimation.",
                encoding_name,
                exc,
            )

    def encode(self, text: str) -> list[int]:
        """Return a token id sequence for ``text``.

        The fallback representation is one id per Unicode code point so that the
        length of the returned list equals the character count.
        """
        if self._encoder is not None:
            return cast(list[int], self._encoder.encode(text))
        return self._fallback_encode(text)

    def decode(self, tokens: list[int]) -> str:
        """Decode a token id sequence back to text."""
        if self._encoder is not None:
            return cast(str, self._encoder.decode(tokens))
        return "".join(chr(token) for token in tokens)

    def count(self, text: str) -> int:
        """Estimate the number of tokens in ``text``."""
        return len(self.encode(text))

    @staticmethod
    def _fallback_encode(text: str) -> list[int]:
        return [ord(char) for char in text]
