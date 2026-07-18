from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from proof_pr.models import EvidenceReport


class ReportError(ValueError):
    """Raised when saved evidence cannot be trusted or interpreted."""


@dataclass(frozen=True)
class ReportSummary:
    head_sha: str
    verdict: str


def read_report_summary(path: Path) -> ReportSummary:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReportError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ReportError(f"unsupported or missing report schema in {path}")

    head_sha = payload.get("head_sha")
    if not isinstance(head_sha, str) or not head_sha:
        raise ReportError(f"missing report HEAD in {path}")

    verdict = payload.get("verdict")
    if verdict not in {"VERIFIED", "FAILED"}:
        raise ReportError(f"invalid report verdict in {path}")
    return ReportSummary(head_sha=head_sha, verdict=verdict)


def write_report(report: EvidenceReport, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "report.json"
    markdown_path = output_dir / "report.md"
    json_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(report.to_markdown(), encoding="utf-8")
    return json_path, markdown_path
