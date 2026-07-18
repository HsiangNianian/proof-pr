# Contributing to proof-pr

Thanks for helping make verification evidence easier to inspect and reproduce.

## Development setup

Use Python 3.11 or newer and install Ruff 0.14.11. The project has no runtime
dependencies.

Run the repository checks before submitting a pull request:

```bash
python3 scripts/run-tests.py
ruff check .
ruff format --check .
```

After committing your changes, generate commit-bound evidence from a clean
worktree:

```bash
python3 scripts/run-proof-pr.py verify --base origin/main
python3 scripts/run-proof-pr.py status
```

## Pull requests

- Keep changes focused and include tests for behavior changes.
- Use Conventional Commit messages such as `feat:`, `fix:`, `docs:`, and `test:`.
- Keep verification commands as explicit argument arrays rather than shell strings.
- Update the README when user-facing behavior or configuration changes.
- Explain what was verified and link hosted evidence when available.

For security-sensitive reports, follow [SECURITY.md](SECURITY.md) instead of
opening a public issue.
