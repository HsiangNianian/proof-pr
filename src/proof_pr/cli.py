from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from proof_pr.config import load_config
from proof_pr.git_context import (
    GitContextError,
    assert_clean_worktree,
    assert_repository_unchanged,
    current_head,
    resolve_git_context,
    worktree_changes,
)
from proof_pr.models import EvidenceReport
from proof_pr.reporting import read_report_summary, write_report
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

    status = subparsers.add_parser("status", help="check whether saved evidence is current")
    status.add_argument("--repo", type=Path, default=Path.cwd())
    status.add_argument("--config", type=Path, default=Path("proof-pr.toml"))
    status.add_argument("--report", type=Path, help="report JSON path")
    return parser


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_config(args: argparse.Namespace, repo: Path):
    config_path = args.config
    if not config_path.is_absolute():
        config_path = repo / config_path
    return load_config(config_path)


def _resolve_output_dir(repo: Path, configured: Path | None, override: Path | None) -> Path:
    output_dir = override if override is not None else configured
    if output_dir is None:
        output_dir = Path(".proof-pr")
    if not output_dir.is_absolute():
        output_dir = repo / output_dir
    return output_dir


def _report_files(output_dir: Path) -> tuple[Path, Path]:
    return output_dir / "report.json", output_dir / "report.md"


def _evidence_paths(
    repo: Path,
    configured_output: Path | None,
    selected_output: Path,
) -> tuple[Path, ...]:
    paths = list(_report_files(selected_output))
    configured_dir = _resolve_output_dir(repo, configured_output, None)
    paths.extend(_report_files(configured_dir))
    return tuple(dict.fromkeys(paths))


def _verify(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    config = _load_config(args, repo)

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

    output_dir = _resolve_output_dir(repo, config.output_dir, args.output_dir)
    evidence_paths = _evidence_paths(repo, config.output_dir, output_dir)
    assert_clean_worktree(repo, excluded_paths=evidence_paths)
    context = resolve_git_context(repo, base)
    results = tuple(
        run_check(name, command, cwd=repo, timeout_seconds=timeout)
        for name, command in parsed_checks
    )
    assert_repository_unchanged(
        repo,
        context.head_sha,
        excluded_paths=evidence_paths,
    )
    report = EvidenceReport(
        head_sha=context.head_sha,
        base_sha=context.base_sha,
        base_ref=base,
        changed_files=context.changed_files,
        checks=results,
        generated_at=_timestamp(),
    )

    json_path, markdown_path = write_report(report, output_dir)

    print(f"proof-pr: {report.verdict}")
    print(f"HEAD: {report.head_sha}")
    print(f"Evidence: {json_path}")
    print(f"Summary: {markdown_path}")
    for check in report.checks:
        status = "PASS" if check.passed else f"FAIL ({check.exit_code})"
        print(f"- {check.name}: {status} in {check.duration_ms} ms")
    return 0 if report.verified else 1


def _status(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    config = _load_config(args, repo)
    configured_output = _resolve_output_dir(repo, config.output_dir, None)

    if args.report is None:
        report_path = configured_output / "report.json"
    else:
        report_path = args.report
        if not report_path.is_absolute():
            report_path = repo / report_path

    summary = read_report_summary(report_path)
    head_sha = current_head(repo)
    report_output = report_path.parent
    evidence_paths = _evidence_paths(repo, config.output_dir, report_output)
    changes = worktree_changes(repo, excluded_paths=evidence_paths)

    reasons: list[str] = []
    if summary.head_sha != head_sha:
        reasons.append("HEAD changed after verification")
    if changes:
        reasons.append("worktree has uncommitted changes")

    verdict = "STALE" if reasons else summary.verdict
    print(f"proof-pr: {verdict}")
    print(f"Report HEAD: {summary.head_sha}")
    print(f"Current HEAD: {head_sha}")
    print(f"Evidence: {report_path}")
    for reason in reasons:
        print(f"Reason: {reason}")
    return 0 if verdict == "VERIFIED" else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            return _verify(args)
        if args.command == "status":
            return _status(args)
    except (GitContextError, OSError, ValueError) as exc:
        print(f"proof-pr: error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unsupported command: {args.command}")
    return 2
