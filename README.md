# proof-pr

Commit-bound verification evidence for pull requests.

AI coding tools often report that tests passed without leaving reviewers a
portable record of what ran or which revision was checked. `proof-pr` executes
explicit local checks and generates JSON and Markdown evidence tied to exact Git
commit SHAs.

## Repository setup

Commit a `proof-pr.toml` file so every contributor runs the same checks:

```toml
[verify]
base = "main"
timeout = 600

[[verify.checks]]
name = "tests"
command = ["python", "-m", "pytest", "-q"]

[[verify.checks]]
name = "lint"
command = ["ruff", "check", "."]
```

Commands are argv arrays by design: they run without a shell, so pipelines,
redirects, and environment interpolation are not accepted.

## Usage

Use the repository defaults:

```bash
proof-pr verify
```

Override the base ref for a local branch or stacked change:

```bash
proof-pr verify --base HEAD^
```

CLI checks replace configured checks when an explicit one-off validation is
needed:

```bash
proof-pr verify \
  --base main \
  --check "tests::python -m pytest -q" \
  --check "lint::ruff check ."
```

## Evidence freshness

Check whether the saved evidence still applies to the current checkout:

```bash
proof-pr status
```

The command returns `STALE` when HEAD changed after verification or the
worktree contains uncommitted files. It exits successfully only when the saved
report is both `VERIFIED` and current.

`proof-pr verify` also requires a clean worktree and confirms that HEAD and the
worktree stayed unchanged while checks ran. Generated `report.json` and
`report.md` files are excluded from that cleanliness check.

Outputs:

- `.proof-pr/report.json` for automation;
- `.proof-pr/report.md` for a pull request body or comment;
- a non-zero exit code when any check fails.

Commands are parsed into argument vectors and run without a shell. Pipelines,
redirects, and environment interpolation are deliberately unsupported in the
MVP.

## Development

```bash
PYTHONPATH=src python -m unittest -v
```

See [PRODUCT_SPEC.md](PRODUCT_SPEC.md) for scope and planned slices.
