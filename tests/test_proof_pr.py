from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from proof_pr.cli import main
from proof_pr.models import CheckResult, EvidenceReport
from proof_pr.runner import parse_check, run_check


class CheckParsingTests(unittest.TestCase):
    def test_parse_check_splits_name_and_command(self) -> None:
        name, command = parse_check("tests::python -m unittest -q")

        self.assertEqual(name, "tests")
        self.assertEqual(command, ("python", "-m", "unittest", "-q"))

    def test_parse_check_rejects_missing_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "NAME::COMMAND"):
            parse_check("python -m unittest")


class CheckExecutionTests(unittest.TestCase):
    def test_run_check_records_success(self) -> None:
        result = run_check(
            "example",
            (sys.executable, "-c", "print('verified')"),
            cwd=Path.cwd(),
            timeout_seconds=10,
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout.strip(), "verified")

    def test_run_check_bounds_output(self) -> None:
        result = run_check(
            "bounded",
            (sys.executable, "-c", "import sys; sys.stdout.write('x' * 100)"),
            cwd=Path.cwd(),
            timeout_seconds=10,
            output_limit=20,
        )

        self.assertLessEqual(len(result.stdout), 20)
        self.assertTrue(result.stdout.endswith("x" * 20))


class ReportTests(unittest.TestCase):
    def test_report_is_verified_only_when_all_checks_pass(self) -> None:
        passed = CheckResult("tests", ("test",), 0, 10, "", "")
        failed = CheckResult("lint", ("lint",), 1, 20, "", "failure")

        report = EvidenceReport(
            head_sha="a" * 40,
            base_sha="b" * 40,
            base_ref="main",
            changed_files=("src/app.py",),
            checks=(passed, failed),
            generated_at="2026-01-01T00:00:00Z",
        )

        self.assertEqual(report.verdict, "FAILED")
        self.assertFalse(report.verified)
        self.assertIn("lint", report.to_markdown())


class CliSmokeTests(unittest.TestCase):
    def test_verify_writes_commit_bound_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Proof PR Test"], cwd=repo, check=True)
            subprocess.run(
                ["git", "config", "user.email", "proof-pr@example.invalid"],
                cwd=repo,
                check=True,
            )
            (repo / "example.txt").write_text("first\n", encoding="utf-8")
            subprocess.run(["git", "add", "example.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "test: add fixture"], cwd=repo, check=True)
            base_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            (repo / "example.txt").write_text("second\n", encoding="utf-8")
            subprocess.run(["git", "add", "example.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "test: update fixture"], cwd=repo, check=True)

            exit_code = main(
                [
                    "verify",
                    "--repo",
                    str(repo),
                    "--base",
                    base_sha,
                    "--check",
                    f"smoke::{sys.executable} -c \"print('ok')\"",
                ]
            )

            self.assertEqual(exit_code, 0)
            report_path = repo / ".proof-pr" / "report.json"
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["base_sha"], base_sha)
            self.assertEqual(payload["changed_files"], ["example.txt"])
            self.assertEqual(payload["verdict"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
