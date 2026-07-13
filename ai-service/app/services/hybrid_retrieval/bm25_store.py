from __future__ import annotations

import logging
from typing import Any

from app.models.hybrid_retrieval import SearchResult

logger = logging.getLogger(__name__)

_TOKENIZERS = ("jieba", "whitespace")


class BM25Store:
    """In-process BM25 sparse retrieval backed by ``rank-bm25`` + ``jieba``.

    The store is cheap to construct; call :meth:`index` with the chunk corpus
    for the requested resource scope, then :meth:`search` to retrieve Top-K
    candidates tokenized with the configured tokenizer.
    """

    def __init__(self, tokenizer: str = "jieba", user_dict: str = "") -> None:
        if tokenizer not in _TOKENIZERS:
            raise ValueError(f"unsupported tokenizer: {tokenizer}")
        self._tokenizer = tokenizer
        self._user_dict = user_dict
        self._docs: list[SearchResult] = []
        self._tokenized_corpus: list[list[str]] = []
        self._bm25: Any = None
        if user_dict:
            self._load_user_dict(user_dict)

    def index(self, docs: list[SearchResult]) -> None:
        """Build a BM25 index over the given chunk texts (tokenized)."""
        self._docs = list(docs)
        self._tokenized_corpus = [self._tokenize(doc.text) for doc in self._docs]
        if not self._tokenized_corpus:
            self._bm25 = None
            return
        # rank-bm25 is imported lazily so the module loads even before the
        # dependency is installed (e.g. in environments that only mock BM25).
        from rank_bm25 import BM25Okapi

        self._bm25 = BM25Okapi(self._tokenized_corpus)

    def search(
        self,
        query: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Tokenize ``query`` and return up to ``top_k`` BM25 matches.

        Hits with a non-positive score are dropped, and remaining hits are
        filtered by ``user_id`` / ``resource_ids`` when provided.
        """
        if self._bm25 is None or not self._docs:
            return []
        tokens = self._tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:top_k]
        results: list[SearchResult] = []
        for idx, score in ranked:
            if score <= 0:
                continue
            doc = self._docs[idx]
            if not _matches_filters(doc, filters):
                continue
            results.append(doc.model_copy(update={"score": float(score), "source": "bm25"}))
        return results

    def _tokenize(self, text: str) -> list[str]:
        if not text:
            return []
        if self._tokenizer == "whitespace":
            return text.split()
        # jieba is imported lazily to avoid its startup cost when only the
        # whitespace tokenizer is used or the store is mocked in tests.
        import jieba

        return [token for token in jieba.cut(text) if token.strip()]

    @staticmethod
    def _load_user_dict(path: str) -> None:
        import jieba

        try:
            jieba.load_userdict(path)
        except Exception:
            logger.warning("Failed to load jieba user dict %s", path, exc_info=True)


def _matches_filters(doc: SearchResult, filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True
    resource_ids = filters.get("resource_ids")
    if resource_ids and doc.resource_id not in resource_ids:
        return False
    user_id = filters.get("user_id")
    return not (user_id and doc.user_id != user_id)
