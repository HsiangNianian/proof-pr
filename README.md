# proof-pr

Commit-bound verification evidence for pull requests.

AI coding tools often report that tests passed without leaving reviewers a
portable record of what ran or which revision was checked. `proof-pr` executes
explicit local checks and generates JSON and Markdown evidence tied to exact Git
commit SHAs.

## MVP usage

```bash
proof-pr verify \
  --base main \
  --check "tests::python -m pytest -q" \
  --check "lint::ruff check ."
```

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
