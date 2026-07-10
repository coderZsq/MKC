from __future__ import annotations

from unittest.mock import patch

from app.services.chunking.token_estimator import TokenEstimator


class TestTokenEstimator:
    def test_count_returns_non_negative(self) -> None:
        estimator = TokenEstimator()
        assert estimator.count("") == 0

    def test_count_english_text(self) -> None:
        estimator = TokenEstimator()
        text = "Hello world"
        assert estimator.count(text) > 0

    def test_count_chinese_text(self) -> None:
        estimator = TokenEstimator()
        text = "你好世界"
        assert estimator.count(text) > 0
        assert estimator.count(text) >= 1

    def test_encode_returns_integer_list(self) -> None:
        estimator = TokenEstimator()
        tokens = estimator.encode("test")
        assert isinstance(tokens, list)
        assert all(isinstance(token, int) for token in tokens)

    def test_decode_round_trips_text(self) -> None:
        estimator = TokenEstimator()
        text = "Round trip test."
        tokens = estimator.encode(text)
        assert estimator.decode(tokens) == text

    def test_fallback_when_tiktoken_unavailable(self) -> None:
        with patch("tiktoken.get_encoding", side_effect=RuntimeError("unavailable")):
            estimator = TokenEstimator()

        text = "abc"
        assert estimator.count(text) == len(text)
        assert estimator.encode(text) == [ord(char) for char in text]
        assert estimator.decode([ord(char) for char in text]) == text

    def test_fallback_decode_with_non_ascii(self) -> None:
        with patch("tiktoken.get_encoding", side_effect=ImportError("no module")):
            estimator = TokenEstimator()

        text = "中文"
        tokens = [ord(char) for char in text]
        assert estimator.decode(tokens) == text
        assert estimator.count(text) == len(text)
