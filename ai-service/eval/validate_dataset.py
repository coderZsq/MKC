from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from eval.models import EvalCase

DEFAULT_REQUIRED_TAGS = frozenset({"audio", "pdf", "citation", "no_answer"})
SECRET_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
    re.compile(r"\b(?:sk|ak)-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{20,}\b"),
)


class DatasetValidationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class LoadedEvalCase:
    line_number: int
    case: EvalCase


def load_jsonl(path: Path) -> list[LoadedEvalCase]:
    loaded: list[LoadedEvalCase] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DatasetValidationError(
            "DATASET_PARSE_FAILED", f"failed to read {path}: {exc}"
        ) from exc

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetValidationError(
                "DATASET_PARSE_FAILED",
                f"line {line_number}: invalid JSONL: {exc.msg}",
            ) from exc
        try:
            loaded.append(
                LoadedEvalCase(line_number=line_number, case=EvalCase.model_validate(payload))
            )
        except ValidationError as exc:
            raise DatasetValidationError(
                "DATASET_SCHEMA_INVALID",
                f"line {line_number}: schema validation failed: {exc.errors()}",
            ) from exc
    return loaded


def scan_for_secrets(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for pattern in SECRET_PATTERNS:
        match = pattern.search(text)
        if match:
            raise DatasetValidationError(
                "DATASET_SECRET_DETECTED",
                f"sensitive-looking value matched near offset {match.start()}",
            )


def validate_cases(
    loaded_cases: Iterable[LoadedEvalCase],
    *,
    min_cases: int,
    max_cases: int,
    required_tags: set[str],
) -> list[EvalCase]:
    cases = [loaded.case for loaded in loaded_cases]
    if len(cases) < min_cases:
        raise DatasetValidationError(
            "DATASET_CASES_TOO_FEW",
            f"dataset has {len(cases)} cases; expected at least {min_cases}",
        )
    if len(cases) > max_cases:
        raise DatasetValidationError(
            "DATASET_SCHEMA_INVALID",
            f"dataset has {len(cases)} cases; expected at most {max_cases}",
        )

    seen_ids: dict[str, int] = {}
    for loaded in loaded_cases:
        case_id = loaded.case.id
        if case_id in seen_ids:
            raise DatasetValidationError(
                "DATASET_SCHEMA_INVALID",
                f"duplicate eval case id {case_id!r} at lines {seen_ids[case_id]} and {loaded.line_number}",
            )
        seen_ids[case_id] = loaded.line_number

    tags = {tag for case in cases for tag in case.tags}
    missing_tags = required_tags.difference(tags)
    if missing_tags:
        raise DatasetValidationError(
            "DATASET_SCHEMA_INVALID",
            f"dataset missing required tags: {sorted(missing_tags)}",
        )
    return cases


def validate_dataset(
    dataset: Path,
    *,
    min_cases: int = 50,
    max_cases: int = 100,
    required_tags: set[str] | None = None,
) -> list[EvalCase]:
    required = set(DEFAULT_REQUIRED_TAGS if required_tags is None else required_tags)
    scan_for_secrets(dataset)
    loaded = load_jsonl(dataset)
    return validate_cases(loaded, min_cases=min_cases, max_cases=max_cases, required_tags=required)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate MKC RAG evaluation JSONL datasets.")
    parser.add_argument("--dataset", required=True, type=Path, help="Path to JSONL dataset.")
    parser.add_argument("--min-cases", type=int, default=50)
    parser.add_argument("--max-cases", type=int, default=100)
    parser.add_argument(
        "--required-tag",
        action="append",
        default=[],
        help="Required tag. Can be provided multiple times. Defaults to core tags.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    required_tags = set(args.required_tag) if args.required_tag else set(DEFAULT_REQUIRED_TAGS)
    try:
        cases = validate_dataset(
            args.dataset,
            min_cases=args.min_cases,
            max_cases=args.max_cases,
            required_tags=required_tags,
        )
    except DatasetValidationError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return 1

    print(f"OK: validated {len(cases)} eval cases from {args.dataset}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
