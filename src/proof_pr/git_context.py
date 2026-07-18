from __future__ import annotations

import subprocess
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


def resolve_git_context(repo: Path, base_ref: str) -> GitContext:
    repo = repo.resolve()
    head_sha = _git(repo, "rev-parse", "HEAD")
    base_sha = _git(repo, "rev-parse", base_ref)
    changed_output = _git(repo, "diff", "--name-only", f"{base_sha}...{head_sha}")
    changed_files = tuple(line for line in changed_output.splitlines() if line)
    return GitContext(head_sha=head_sha, base_sha=base_sha, changed_files=changed_files)
