# Changelog

All notable changes to this project are documented in this file.

## 0.1.0 - 2026-07-18

### Features

- Generate JSON and Markdown verification evidence bound to exact base and head commits.
- Run repository-defined checks without a shell and reject dirty or changing worktrees.
- Detect stale evidence after the verified commit or worktree changes.
- Provide a composite GitHub Action that publishes evidence to the workflow job summary.

### Documentation

- Document repository configuration, CLI usage, evidence freshness, and secure pull request setup.

### Continuous Integration

- Verify the project with its own action and install pinned hosted-runner tooling.
