from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from proof_pr.config import load_config
from proof_pr.git_context import GitContextError, resolve_git_context
from proof_pr.models import EvidenceReport
from proof_pr.reporting import write_report
from proof_pr.runner import parse_check, run_check


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proof-pr",
        description="Generate commit-bound verification evidence for a pull request.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify", help="run checks and write an evidence report")
    verify.add_argument("--repo", type=Path, default=Path.cwd())
    verify.add_argument("--config", type=Path, default=Path("proof-pr.toml"))
    verify.add_argument("--base", help="Git base ref or commit; overrides repository config")
    verify.add_argument(
        "--check",
        action="append",
        metavar="NAME::COMMAND",
        help="named command to execute; overrides configured checks and may be repeated",
    )
    verify.add_argument("--timeout", type=int, help="seconds per check")
    verify.add_argument("--output-dir", type=Path)
    return parser


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _verify(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    config_path = args.config
    if not config_path.is_absolute():
        config_path = repo / config_path
    config = load_config(config_path)

    base = args.base if args.base is not None else config.base
    if base is None:
        raise ValueError("no base configured; pass --base or set verify.base")

    if args.check is not None:
        parsed_checks = tuple(parse_check(value) for value in args.check)
    else:
        parsed_checks = config.checks
    if not parsed_checks:
        raise ValueError("no checks configured; pass --check or add [[verify.checks]]")

    timeout = args.timeout if args.timeout is not None else config.timeout_seconds
    if timeout is None:
        timeout = 600
    if timeout <= 0:
        raise ValueError("--timeout must be greater than zero")

    context = resolve_git_context(repo, base)
    results = tuple(
        run_check(name, command, cwd=repo, timeout_seconds=timeout)
        for name, command in parsed_checks
    )
    report = EvidenceReport(
        head_sha=context.head_sha,
        base_sha=context.base_sha,
        base_ref=base,
        changed_files=context.changed_files,
        checks=results,
        generated_at=_timestamp(),
    )

    output_dir = args.output_dir if args.output_dir is not None else config.output_dir
    if output_dir is None:
        output_dir = Path(".proof-pr")
    if not output_dir.is_absolute():
        output_dir = repo / output_dir
    json_path, markdown_path = write_report(report, output_dir)

    print(f"proof-pr: {report.verdict}")
    print(f"HEAD: {report.head_sha}")
    print(f"Evidence: {json_path}")
    print(f"Summary: {markdown_path}")
    for check in report.checks:
        status = "PASS" if check.passed else f"FAIL ({check.exit_code})"
        print(f"- {check.name}: {status} in {check.duration_ms} ms")
    return 0 if report.verified else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            return _verify(args)
    except (GitContextError, OSError, ValueError) as exc:
        print(f"proof-pr: error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unsupported command: {args.command}")
    return 2
