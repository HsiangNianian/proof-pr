from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


class GitContextError(RuntimeError):
    """Raised when repository evidence cannot be resolved."""


@dataclass(frozen=True)
class GitContext:
    head_sha: str
    base_sha: str
    changed_files: tuple[str, ...]


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ("git", *args),
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise GitContextError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def current_head(repo: Path) -> str:
    return _git(repo.resolve(), "rev-parse", "HEAD")


def worktree_changes(repo: Path, *, excluded_paths: Sequence[Path] = ()) -> tuple[str, ...]:
    repo = repo.resolve()
    pathspecs = ["."]
    for path in excluded_paths:
        try:
            relative = path.resolve().relative_to(repo)
        except ValueError:
            continue
        pathspecs.append(f":(exclude){relative.as_posix()}")

    output = _git(
        repo,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        *pathspecs,
    )
    return tuple(line for line in output.splitlines() if line)


def assert_clean_worktree(repo: Path, *, excluded_paths: Sequence[Path] = ()) -> None:
    changes = worktree_changes(repo, excluded_paths=excluded_paths)
    if changes:
        preview = ", ".join(changes[:3])
        if len(changes) > 3:
            preview += f", and {len(changes) - 3} more"
        raise GitContextError(f"worktree has uncommitted changes: {preview}")


def assert_repository_unchanged(
    repo: Path,
    expected_head: str,
    *,
    excluded_paths: Sequence[Path] = (),
) -> None:
    actual_head = current_head(repo)
    if actual_head != expected_head:
        raise GitContextError(
            f"HEAD changed while checks ran: expected {expected_head}, found {actual_head}"
        )
    assert_clean_worktree(repo, excluded_paths=excluded_paths)


def resolve_git_context(repo: Path, base_ref: str) -> GitContext:
    repo = repo.resolve()
    head_sha = current_head(repo)
    base_sha = _git(repo, "rev-parse", base_ref)
    changed_output = _git(repo, "diff", "--name-only", f"{base_sha}...{head_sha}")
    changed_files = tuple(line for line in changed_output.splitlines() if line)
    return GitContext(head_sha=head_sha, base_sha=base_sha, changed_files=changed_files)
