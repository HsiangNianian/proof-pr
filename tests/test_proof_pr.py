from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from proof_pr.cli import main
from proof_pr.config import ConfigError, load_config
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


class ConfigTests(unittest.TestCase):
    def test_load_config_reads_repository_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "proof-pr.toml"
            path.write_text(
                """
[verify]
base = "main"
timeout = 120
output_dir = "artifacts/proof-pr"

[[verify.checks]]
name = "tests"
command = ["python3", "-m", "unittest", "-v"]
""".strip(),
                encoding="utf-8",
            )

            config = load_config(path)

            self.assertEqual(config.base, "main")
            self.assertEqual(config.timeout_seconds, 120)
            self.assertEqual(config.output_dir, Path("artifacts/proof-pr"))
            self.assertEqual(
                config.checks,
                (("tests", ("python3", "-m", "unittest", "-v")),),
            )

    def test_load_config_rejects_shell_command_strings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "proof-pr.toml"
            path.write_text(
                """
[verify]

[[verify.checks]]
name = "tests"
command = "python3 -m unittest"
""".strip(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ConfigError, "array of strings"):
                load_config(path)


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
            (repo / "proof-pr.toml").write_text(
                f"""
[verify]
base = "HEAD^"
timeout = 10

[[verify.checks]]
name = "smoke"
command = [{json.dumps(sys.executable)}, "-c", "print('ok')"]
""".strip(),
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "example.txt", "proof-pr.toml"], cwd=repo, check=True)
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
                ]
            )

            self.assertEqual(exit_code, 0)
            report_path = repo / ".proof-pr" / "report.json"
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["base_sha"], base_sha)
            self.assertEqual(payload["changed_files"], ["example.txt"])
            self.assertEqual(payload["verdict"], "VERIFIED")
            self.assertEqual(payload["checks"][0]["name"], "smoke")
            self.assertEqual(main(["status", "--repo", str(repo)]), 0)

            dirty_path = repo / "dirty.txt"
            dirty_path.write_text("uncommitted\n", encoding="utf-8")
            status_output = io.StringIO()
            with redirect_stdout(status_output):
                dirty_status = main(["status", "--repo", str(repo)])
            self.assertEqual(dirty_status, 1)
            self.assertIn("STALE", status_output.getvalue())

            verify_error = io.StringIO()
            with redirect_stderr(verify_error):
                dirty_verify = main(["verify", "--repo", str(repo)])
            self.assertEqual(dirty_verify, 2)
            self.assertIn("worktree", verify_error.getvalue())
            dirty_path.unlink()

            (repo / "proof-pr.toml").write_text(
                f"""
[verify]
base = "missing-ref"

[[verify.checks]]
name = "configured"
command = [{json.dumps(sys.executable)}, "-c", "raise SystemExit(1)"]
""".strip(),
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "proof-pr.toml"], cwd=repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", "test: change verification config"],
                cwd=repo,
                check=True,
            )

            status_output = io.StringIO()
            with redirect_stdout(status_output):
                stale_status = main(["status", "--repo", str(repo)])
            self.assertEqual(stale_status, 1)
            self.assertIn("STALE", status_output.getvalue())

            exit_code = main(
                [
                    "verify",
                    "--repo",
                    str(repo),
                    "--base",
                    base_sha,
                    "--check",
                    f"override::{sys.executable} -c \"print('override')\"",
                    "--output-dir",
                    ".proof-pr/override",
                ]
            )

            self.assertEqual(exit_code, 0)
            override_payload = json.loads(
                (repo / ".proof-pr" / "override" / "report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(override_payload["base_sha"], base_sha)
            self.assertEqual(override_payload["checks"][0]["name"], "override")
            self.assertEqual(
                main(
                    [
                        "status",
                        "--repo",
                        str(repo),
                        "--report",
                        ".proof-pr/override/report.json",
                    ]
                ),
                0,
            )


if __name__ == "__main__":
    unittest.main()
