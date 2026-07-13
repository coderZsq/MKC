from app.models.citation import Citation
from app.services.citation_validator import CitationValidator


def _citation(index: int, resource_id: str) -> Citation:
    return Citation(
        index=index,
        chunk_id=f"c-{index}",
        resource_id=resource_id,
        resource_type="pdf",
        score=0.9,
    )


def test_validator_drops_unauthorized_resources() -> None:
    validator = CitationValidator(max_citations=8, log_dropped=False)

    valid = validator.validate(
        [_citation(1, "allowed"), _citation(2, "blocked")],
        {"allowed"},
    )

    assert [citation.resource_id for citation in valid] == ["allowed"]


def test_validator_truncates_to_max_citations() -> None:
    validator = CitationValidator(max_citations=2, log_dropped=False)

    valid = validator.validate(
        [_citation(1, "r"), _citation(2, "r"), _citation(3, "r")],
        {"r"},
    )

    assert [citation.index for citation in valid] == [1, 2]
