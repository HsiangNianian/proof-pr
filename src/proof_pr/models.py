from __future__ import annotations

import shlex
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CheckResult:
    """Evidence captured from one verification command."""

    name: str
    command: tuple[str, ...]
    exit_code: int
    duration_ms: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["command"] = list(self.command)
        payload["passed"] = self.passed
        return payload


@dataclass(frozen=True)
class EvidenceReport:
    """Verification evidence bound to an exact Git revision pair."""

    head_sha: str
    base_sha: str
    base_ref: str
    changed_files: tuple[str, ...]
    checks: tuple[CheckResult, ...]
    generated_at: str

    @property
    def verified(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)

    @property
    def verdict(self) -> str:
        return "VERIFIED" if self.verified else "FAILED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "generated_at": self.generated_at,
            "head_sha": self.head_sha,
            "base_ref": self.base_ref,
            "base_sha": self.base_sha,
            "changed_files": list(self.changed_files),
            "checks": [check.to_dict() for check in self.checks],
            "verdict": self.verdict,
        }

    def to_markdown(self) -> str:
        changed = "\n".join(f"- `{path}`" for path in self.changed_files) or "- None"
        rows = ["| Check | Result | Duration | Command |", "|---|---:|---:|---|"]
        for check in self.checks:
            result = "PASS" if check.passed else f"FAIL ({check.exit_code})"
            command = shlex.join(check.command).replace("|", "\\|")
            rows.append(f"| {check.name} | {result} | {check.duration_ms} ms | `{command}` |")

        return "\n".join(
            [
                "# proof-pr evidence",
                "",
                f"**Verdict:** `{self.verdict}`",
                f"**HEAD:** `{self.head_sha}`",
                f"**Base:** `{self.base_ref}` (`{self.base_sha}`)",
                f"**Generated:** `{self.generated_at}`",
                "",
                "## Changed files",
                "",
                changed,
                "",
                "## Checks",
                "",
                *rows,
                "",
            ]
        )
