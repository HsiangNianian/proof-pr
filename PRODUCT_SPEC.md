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

Projects commit their verification policy as data:

```toml
[verify]
base = "main"

[[verify.checks]]
name = "tests"
command = ["python", "-m", "pytest", "-q"]
```

Contributors then run:

```bash
proof-pr verify
```

The command:

1. records the repository HEAD and resolved base revision;
2. lists files changed between the base and HEAD;
3. runs each explicitly supplied check without a shell;
4. confirms HEAD and the clean worktree did not change while checks ran;
5. records command, duration, exit code, and bounded output;
6. writes `.proof-pr/report.json` and `.proof-pr/report.md`;
7. returns a failing exit code when any check fails.

`proof-pr status` compares saved evidence with the current HEAD and worktree. It
returns `STALE` when either has changed since verification.

The composite GitHub Action runs the same contract against the pull request
head, publishes `report.md` to the workflow Job Summary even when checks fail,
and fails the job unless the final evidence is current and `VERIFIED`.

## Acceptance criteria

- Reports are deterministic apart from timestamps and command duration.
- Every report is bound to exact HEAD and base commit SHAs.
- A report cannot be `VERIFIED` unless at least one check ran and all checks passed.
- Commands execute as argument vectors, not through `shell=True`.
- Captured output is bounded so reports cannot grow without limit.
- Unit tests cover parsing, passing/failing verdicts, output bounds, and rendering.
- A smoke test runs the CLI against a real temporary Git repository.
- Repository defaults are explicit argv arrays in a reviewable `proof-pr.toml`.
- CLI values override repository defaults for one-off verification.
- Verification refuses a dirty worktree and detects repository changes during checks.
- Saved evidence reports `STALE` after a new commit or uncommitted code change.
- The GitHub Action exposes verdict and report paths as outputs.
- The example PR workflow uses read-only permissions and the exact PR head SHA.

## Non-goals

- Automatically choosing the right test commands.
- Claiming semantic test coverage from filenames alone.
- Posting GitHub comments or creating checks.
- Running untrusted commands in a sandbox.
- Supporting shell pipelines, redirects, or environment interpolation.
- Calling an LLM.

## Next slices

1. Diff-to-test evidence and reusable policy gates.
2. Sticky PR evidence comments through an isolated trusted publisher.
3. Signed provenance and reusable policy gates.
