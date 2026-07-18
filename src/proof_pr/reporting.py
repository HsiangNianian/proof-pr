from __future__ import annotations

import json
from pathlib import Path

from proof_pr.models import EvidenceReport


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
