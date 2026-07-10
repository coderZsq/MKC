from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_SEPARATORS: list[str] = [
    "\n## ",
    "\n# ",
    "\n\n",
    "\n",
    "。",
    "，",
    " ",
    "",
]


@dataclass
class ChunkingConfig:
    """Runtime configuration for text chunking strategies.

    Values are normally loaded from ``config/ai.yaml`` and can be overridden
    by environment variables for containerised deployments.

    Note:
        ``chunk_overlap`` is currently applied by the ``fixed_token`` strategy.
        Boundary-based strategies (``paragraph`` and ``semantic``) preserve
        natural boundaries and do not add overlap between chunks.
    """

    default_strategy: str = "paragraph"
    chunk_size: int = 512
    chunk_overlap: int = 50
    separators: list[str] = field(default_factory=lambda: list(DEFAULT_SEPARATORS))
    preserve_metadata: bool = True
    max_input_chars: int = 1_000_000

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap 不能为负数")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        if self.max_input_chars <= 0:
            raise ValueError("max_input_chars 必须大于 0")
        if not self.separators:
            raise ValueError("separators 不能为空")
        if self.separators[-1] != "":
            raise ValueError('separators 列表末尾必须包含空字符串 "" 作为兜底分隔符')
