# proof-pr

[![proof-pr](https://github.com/HsiangNianian/proof-pr/actions/workflows/proof-pr.yml/badge.svg)](https://github.com/HsiangNianian/proof-pr/actions/workflows/proof-pr.yml)

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

## GitHub Action

The composite action runs repository checks, enforces fresh evidence, and
publishes the Markdown report to the workflow Job Summary:

```yaml
name: proof-pr

on:
  pull_request:

permissions:
  contents: read

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          ref: ${{ github.event.pull_request.head.sha }}
          fetch-depth: 0
          persist-credentials: false

      - uses: HsiangNianian/proof-pr@v0.1.0
        with:
          base: ${{ github.event.pull_request.base.sha }}
```

Pin the action to a release tag or full commit SHA in production. The checkout
must include Git history so `proof-pr` can resolve the base commit.

The included [.github/workflows/proof-pr.yml](.github/workflows/proof-pr.yml)
uses the local action to verify this repository itself. It deliberately uses
the `pull_request` event with a read-only token and does not post PR comments.
Do not switch it to `pull_request_target` while executing checks defined by PR
code; that would combine untrusted commands with a privileged workflow.

Outputs:

- `.proof-pr/report.json` for automation;
- `.proof-pr/report.md` for a pull request body or comment;
- a non-zero exit code when any check fails.

Commands are parsed into argument vectors and run without a shell. Pipelines,
redirects, and environment interpolation are deliberately unsupported in the
MVP.

## Development

```bash
python scripts/run-tests.py
```

See [PRODUCT_SPEC.md](PRODUCT_SPEC.md) for scope and planned slices.
