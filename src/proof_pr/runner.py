from __future__ import annotations

import shlex
import subprocess
import time
from pathlib import Path

from proof_pr.models import CheckResult

DEFAULT_OUTPUT_LIMIT = 4_000


def parse_check(value: str) -> tuple[str, tuple[str, ...]]:
    """Parse a ``NAME::COMMAND`` check without enabling shell execution."""

    if "::" not in value:
        raise ValueError("check must use NAME::COMMAND format")

    raw_name, raw_command = value.split("::", 1)
    name = raw_name.strip()
    command = tuple(shlex.split(raw_command))
    if not name or not command:
        raise ValueError("check must use NAME::COMMAND format with non-empty values")
    return name, command


def _bounded_tail(value: str | bytes | None, limit: int) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    return value[-limit:]


def run_check(
    name: str,
    command: tuple[str, ...],
    *,
    cwd: Path,
    timeout_seconds: int,
    output_limit: int = DEFAULT_OUTPUT_LIMIT,
) -> CheckResult:
    """Run one explicit command and capture bounded verification evidence."""

    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        exit_code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = exc.stdout
        stderr = f"Command timed out after {timeout_seconds} seconds.\n"
        if exc.stderr:
            stderr += _bounded_tail(exc.stderr, output_limit)

    duration_ms = round((time.monotonic() - started) * 1_000)
    return CheckResult(
        name=name,
        command=command,
        exit_code=exit_code,
        duration_ms=duration_ms,
        stdout=_bounded_tail(stdout, output_limit),
        stderr=_bounded_tail(stderr, output_limit),
    )
