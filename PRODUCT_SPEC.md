# proof-pr MVP

## Product promise

`proof-pr` turns local verification commands into a commit-bound evidence report
for a pull request. It does not decide whether code is correct; it records what
was checked, against which revision, and whether the checks passed.

## Target user

Developers and maintainers reviewing code produced with AI coding tools who want
machine-readable, reproducible evidence instead of an unverified "tests pass"
claim.

## First workflow

```bash
proof-pr verify \
  --base main \
  --check "tests::python -m pytest -q" \
  --check "lint::ruff check ."
```

The command:

1. records the repository HEAD and resolved base revision;
2. lists files changed between the base and HEAD;
3. runs each explicitly supplied check without a shell;
4. records command, duration, exit code, and bounded output;
5. writes `.proof-pr/report.json` and `.proof-pr/report.md`;
6. returns a failing exit code when any check fails.

## Acceptance criteria

- Reports are deterministic apart from timestamps and command duration.
- Every report is bound to exact HEAD and base commit SHAs.
- A report cannot be `VERIFIED` unless at least one check ran and all checks passed.
- Commands execute as argument vectors, not through `shell=True`.
- Captured output is bounded so reports cannot grow without limit.
- Unit tests cover parsing, passing/failing verdicts, output bounds, and rendering.
- A smoke test runs the CLI against a real temporary Git repository.

## Non-goals

- Automatically choosing the right test commands.
- Claiming semantic test coverage from filenames alone.
- Posting GitHub comments or creating checks.
- Running untrusted commands in a sandbox.
- Supporting shell pipelines, redirects, or environment interpolation.
- Calling an LLM.

## Next slices

1. Repository-native command discovery with explicit user confirmation.
2. Diff-to-test evidence and stale-report detection.
3. GitHub Action and sticky PR evidence comment.
4. Signed provenance and reusable policy gates.
