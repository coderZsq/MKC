from __future__ import annotations

import pytest

from app.core.exceptions import InvalidChunkingStrategyError
from app.services.chunking.chunking_service import ChunkingService
from app.services.chunking.config import ChunkingConfig
from app.services.chunking.factory import build_chunking_config, build_chunking_service


@pytest.fixture
def service() -> ChunkingService:
    return build_chunking_service(ChunkingConfig(chunk_size=100, chunk_overlap=10))


def test_chunking_service_dispatches_paragraph(service: ChunkingService) -> None:
    text = "第一段。\n\n第二段。"
    chunks = service.chunk(text, "res-1", {}, strategy="paragraph")
    assert len(chunks) == 2
    assert chunks[0].text == "第一段。"
    assert chunks[1].text == "第二段。"


def test_chunking_service_dispatches_fixed_token(service: ChunkingService) -> None:
    text = "word " * 100
    chunks = service.chunk(text, "res-1", {}, strategy="fixed_token")
    assert len(chunks) >= 2


def test_chunking_service_dispatches_semantic(service: ChunkingService) -> None:
    text = "# 标题\n正文内容。"
    chunks = service.chunk(text, "res-1", {}, strategy="semantic")
    assert len(chunks) >= 1
    assert chunks[0].text.startswith("#")


def test_chunking_service_default_strategy() -> None:
    custom_service = build_chunking_service(
        ChunkingConfig(default_strategy="fixed_token", chunk_size=50, chunk_overlap=5)
    )
    text = "word " * 50
    chunks = custom_service.chunk(text, "res-1", {})
    assert len(chunks) >= 2


def test_chunking_service_unknown_strategy(service: ChunkingService) -> None:
    with pytest.raises(InvalidChunkingStrategyError) as exc_info:
        service.chunk("text", "res-1", {}, strategy="unknown")
    assert exc_info.value.code == "INVALID_STRATEGY"


def test_chunking_config_empty_text_returns_empty_list(service: ChunkingService) -> None:
    assert service.chunk("", "res-1", {}, strategy="paragraph") == []


def test_chunking_config_validates_chunk_size() -> None:
    with pytest.raises(ValueError, match="chunk_size"):
        ChunkingConfig(chunk_size=0)


def test_chunking_config_validates_overlap() -> None:
    with pytest.raises(ValueError, match="chunk_overlap"):
        ChunkingConfig(chunk_size=10, chunk_overlap=10)


def test_chunking_config_validates_separators() -> None:
    with pytest.raises(ValueError, match="separators"):
        ChunkingConfig(separators=[])


def test_chunking_config_validates_max_input_chars() -> None:
    with pytest.raises(ValueError, match="max_input_chars"):
        ChunkingConfig(max_input_chars=0)


def test_build_chunking_config_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHUNKING_DEFAULT_STRATEGY", "semantic")
    monkeypatch.setenv("CHUNKING_CHUNK_SIZE", "256")
    cfg = build_chunking_config({})
    assert cfg.default_strategy == "semantic"
    assert cfg.chunk_size == 256


def test_build_chunking_config_reads_max_input_chars_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHUNKING_MAX_INPUT_CHARS", "100")
    cfg = build_chunking_config({})
    assert cfg.max_input_chars == 100


def test_build_chunking_config_defaults() -> None:
    cfg = build_chunking_config({})
    assert cfg.default_strategy == "paragraph"
    assert cfg.chunk_size == 512
    assert cfg.chunk_overlap == 50
    assert cfg.preserve_metadata is True
    assert cfg.max_input_chars == 1_000_000
