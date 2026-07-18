from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class GithubActionContractTests(unittest.TestCase):
    def test_composite_action_runs_verification_and_publishes_summary(self) -> None:
        action = (REPOSITORY_ROOT / "action.yml").read_text(encoding="utf-8")

        self.assertIn('using: "composite"', action)
        self.assertIn("actions/setup-python@v6", action)
        self.assertIn("github.action_path", action)
        self.assertIn('python "$PROOF_PR_RUNNER" verify', action)
        self.assertIn('python "$PROOF_PR_RUNNER" status', action)
        self.assertIn("continue-on-error: true", action)
        self.assertIn("if: always()", action)
        self.assertIn("GITHUB_STEP_SUMMARY", action)
        self.assertIn("GITHUB_OUTPUT", action)
        self.assertIn("steps.verify.outcome", action)
        self.assertNotIn("pip install", action)

    def test_action_passes_inputs_through_environment_variables(self) -> None:
        action = (REPOSITORY_ROOT / "action.yml").read_text(encoding="utf-8")

        self.assertIn("PROOF_PR_BASE: ${{ inputs.base }}", action)
        self.assertIn("PROOF_PR_CONFIG: ${{ inputs.config }}", action)
        self.assertIn("PROOF_PR_OUTPUT_DIR: ${{ inputs.output-dir }}", action)
        self.assertIn('"$PROOF_PR_BASE"', action)
        self.assertIn('"$PROOF_PR_CONFIG"', action)
        self.assertIn('"$PROOF_PR_OUTPUT_DIR"', action)

    def test_action_runner_bootstraps_the_local_package(self) -> None:
        result = subprocess.run(
            [sys.executable, REPOSITORY_ROOT / "scripts/run-proof-pr.py", "--help"],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Generate commit-bound verification evidence", result.stdout)

    def test_example_workflow_uses_read_only_pull_request_permissions(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github/workflows/proof-pr.yml").read_text(encoding="utf-8")

        self.assertIn("pull_request:", workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertIn("contents: read", workflow)
        self.assertNotIn("pull-requests: write", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertIn("actions/checkout@v6", workflow)
        self.assertIn("actions/setup-python@v6", workflow)
        self.assertIn("python -m pip install ruff==0.14.11", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("ref: ${{ github.event.pull_request.head.sha }}", workflow)
        self.assertIn("base: ${{ github.event.pull_request.base.sha }}", workflow)
        self.assertIn("uses: ./", workflow)


if __name__ == "__main__":
    unittest.main()
