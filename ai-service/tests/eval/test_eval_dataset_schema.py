from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from eval.models import EvalCase
from eval.validate_dataset import DatasetValidationError, load_jsonl, validate_dataset

AI_SERVICE_ROOT = Path(__file__).resolve().parents[2]
RAG_DATASET = AI_SERVICE_ROOT / "eval" / "datasets" / "rag_eval.jsonl"
SMOKE_DATASET = AI_SERVICE_ROOT / "eval" / "datasets" / "smoke_eval.jsonl"
SCHEMA_PATH = AI_SERVICE_ROOT / "eval" / "schemas" / "eval_case.schema.json"


def test_schema_file_is_valid_json() -> None:
    # MKC-TC-S5-1-003: schema is present and parseable for CI/tooling reuse.
    payload = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert payload["title"] == "MKC RAG Evaluation Case"
    assert "expected_citations" in payload["required"]


def test_rag_eval_dataset_count_and_required_tags() -> None:
    # MKC-TC-S5-1-001, MKC-TC-S5-1-004, MKC-TC-S5-1-006, MKC-TC-S5-1-007.
    cases = validate_dataset(RAG_DATASET)

    assert 50 <= len(cases) <= 100
    tags = {tag for case in cases for tag in case.tags}
    assert {"audio", "pdf", "citation", "no_answer"}.issubset(tags)


def test_every_dataset_case_has_required_fields() -> None:
    # MKC-TC-S5-1-002: every JSONL row validates through the Pydantic contract.
    loaded = load_jsonl(RAG_DATASET)

    assert loaded
    for loaded_case in loaded:
        case = loaded_case.case
        assert case.id
        assert case.question
        assert case.expected_answer
        assert case.resource_ids
        assert case.tags
        assert case.difficulty in {"easy", "medium", "hard"}


def test_smoke_dataset_validates_with_relaxed_count() -> None:
    # MKC-TC-S5-1-005: smoke dataset is small and can run without an external LLM key.
    cases = validate_dataset(SMOKE_DATASET, min_cases=5, max_cases=10)

    assert len(cases) == 5


def test_cli_validates_smoke_dataset() -> None:
    # MKC-TC-S5-1-005: CLI exits successfully for the CI smoke fixture.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "eval.validate_dataset",
            "--dataset",
            str(SMOKE_DATASET),
            "--min-cases",
            "5",
            "--max-cases",
            "10",
        ],
        cwd=AI_SERVICE_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "OK: validated 5 eval cases" in result.stdout


def test_bad_json_reports_line_number(tmp_path: Path) -> None:
    # MKC-TC-S5-1-008: JSONL parse errors include the failing line number.
    dataset = tmp_path / "bad.jsonl"
    dataset.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "rag-temp-001",
                        "question": "valid?",
                        "expected_answer": "valid",
                        "resource_ids": ["res_demo"],
                        "expected_citations": [{"resource_id": "res_demo", "chunk_id": "chunk-1"}],
                        "tags": ["audio", "citation"],
                        "difficulty": "easy",
                    }
                ),
                "{bad json}",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(DatasetValidationError) as exc_info:
        load_jsonl(dataset)

    assert exc_info.value.code == "DATASET_PARSE_FAILED"
    assert "line 2" in exc_info.value.message


def test_duplicate_id_is_rejected(tmp_path: Path) -> None:
    # MKC-TC-S5-1-009: duplicate IDs fail with DATASET_SCHEMA_INVALID.
    case = {
        "id": "rag-temp-001",
        "question": "What is duplicated?",
        "expected_answer": "The ID is duplicated.",
        "resource_ids": ["res_demo"],
        "expected_citations": [{"resource_id": "res_demo", "chunk_id": "chunk-1"}],
        "tags": ["audio", "citation"],
        "difficulty": "easy",
    }
    dataset = tmp_path / "duplicate.jsonl"
    dataset.write_text(
        f"{json.dumps(case)}\n{json.dumps(case)}\n",
        encoding="utf-8",
    )

    with pytest.raises(DatasetValidationError) as exc_info:
        validate_dataset(dataset, min_cases=1, max_cases=10, required_tags=set())

    assert exc_info.value.code == "DATASET_SCHEMA_INVALID"
    assert "duplicate eval case id" in exc_info.value.message


def test_secret_like_values_are_rejected(tmp_path: Path) -> None:
    # MKC-TC-S5-1-006: hardcoded key/token/secret patterns are rejected.
    payload = {
        "id": "rag-temp-001",
        "question": "Does this contain a key?",
        "expected_answer": "api_key=sk-demo0123456789abcdef should be rejected",
        "resource_ids": ["res_demo"],
        "expected_citations": [{"resource_id": "res_demo", "chunk_id": "chunk-1"}],
        "tags": ["audio", "citation"],
        "difficulty": "easy",
    }
    dataset = tmp_path / "secret.jsonl"
    dataset.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DatasetValidationError) as exc_info:
        validate_dataset(dataset, min_cases=1, max_cases=10, required_tags=set())

    assert exc_info.value.code == "DATASET_SECRET_DETECTED"


def test_no_answer_cases_cannot_have_citations() -> None:
    with pytest.raises(ValueError, match="no_answer cases"):
        EvalCase.model_validate(
            {
                "id": "rag-temp-001",
                "question": "Unknown?",
                "expected_answer": "No answer.",
                "resource_ids": ["res_demo"],
                "expected_citations": [{"resource_id": "res_demo", "chunk_id": "chunk-1"}],
                "tags": ["no_answer"],
                "difficulty": "easy",
            }
        )
