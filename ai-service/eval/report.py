from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from eval.types import EvalReport

SECRET_MARKERS = ("api_key", "secret", "token", "password")


class ReportWriter:
    def __init__(self, report_dir: Path) -> None:
        self._report_dir = report_dir

    def write(self, report: EvalReport) -> tuple[Path, Path]:
        self._report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
        json_path = self._report_dir / f"eval_report_{timestamp}.json"
        markdown_path = self._report_dir / f"eval_report_{timestamp}.md"

        json_text = report.model_dump_json(indent=2)
        _assert_no_secret_markers(json_text)
        json_path.write_text(json_text + "\n", encoding="utf-8")

        markdown_text = render_markdown(report)
        _assert_no_secret_markers(markdown_text)
        markdown_path.write_text(markdown_text, encoding="utf-8")
        return json_path, markdown_path


def render_markdown(report: EvalReport) -> str:
    summary = report.summary
    lines = [
        "# MKC RAG Evaluation Report",
        "",
        "## Summary",
        "",
        f"- Total cases: {summary.total_cases}",
        f"- Passed cases: {summary.passed_cases}",
        f"- Failed cases: {summary.failed_cases}",
        f"- Recall: {summary.recall:.4f}",
        f"- Faithfulness: {summary.faithfulness:.4f}",
        f"- Relevance: {summary.relevance:.4f}",
        f"- Citation accuracy: {summary.citation_accuracy:.4f}",
        "",
        "## By Tag",
        "",
    ]
    if summary.by_tag:
        lines.append("| Tag | Count | Recall | Faithfulness | Relevance | Citation Accuracy |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for tag in sorted(summary.by_tag):
            row = summary.by_tag[tag]
            lines.append(
                "| {tag} | {count} | {recall:.4f} | {faithfulness:.4f} | {relevance:.4f} | {citation_accuracy:.4f} |".format(
                    tag=tag,
                    count=int(row["count"]),
                    recall=float(row["recall"]),
                    faithfulness=float(row["faithfulness"]),
                    relevance=float(row["relevance"]),
                    citation_accuracy=float(row["citation_accuracy"]),
                )
            )
    else:
        lines.append("No tag metrics.")

    lines.extend(["", "## Cases", ""])
    lines.append(
        "| Case | Status | Recall | Faithfulness | Relevance | Citation Accuracy | Error |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---|")
    for result in report.cases:
        scores = result.scores
        lines.append(
            "| {case_id} | {status} | {recall} | {faithfulness} | {relevance} | {citation_accuracy} | {error} |".format(
                case_id=result.case_id,
                status=result.status,
                recall=_fmt(scores.recall if scores else None),
                faithfulness=_fmt(scores.faithfulness if scores else None),
                relevance=_fmt(scores.relevance if scores else None),
                citation_accuracy=_fmt(scores.citation_accuracy if scores else None),
                error=result.error_code or "",
            )
        )
    return "\n".join(lines) + "\n"


def load_report(path: Path) -> EvalReport:
    return EvalReport.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _fmt(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.4f}"


def _assert_no_secret_markers(text: str) -> None:
    lowered = text.lower()
    for marker in SECRET_MARKERS:
        if marker in lowered:
            raise ValueError(f"report contains sensitive marker: {marker}")
