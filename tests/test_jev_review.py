# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "bin" / "jev_review.py"


def run_client(*args: str, stdin: str = "") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", str(CLIENT), *args],
        input=stdin,
        text=True,
        capture_output=True,
        cwd=ROOT,
    )


class JevTruncationTests(unittest.TestCase):
    def test_truncated_diff_blocks_pass(self) -> None:
        result = run_client(
            "--diff",
            "-",
            "--task",
            "scope",
            "--model",
            "mock-model",
            "--max-chars",
            "16",
            "--mock",
            "good",
            "--json",
            stdin="0123456789abcdefEXTRA",
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["passed"])
        self.assertTrue(payload["diff_truncated"])
        self.assertFalse(payload["task_truncated"])
        self.assertTrue(
            any("diff truncated" in problem for problem in payload["problems"])
        )

    def test_truncated_task_blocks_pass(self) -> None:
        result = run_client(
            "--diff",
            "-",
            "--task",
            "x" * 64,
            "--model",
            "mock-model",
            "--max-chars",
            "16",
            "--mock",
            "good",
            "--json",
            stdin="short diff",
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["passed"])
        self.assertFalse(payload["diff_truncated"])
        self.assertTrue(payload["task_truncated"])
        self.assertTrue(
            any("task truncated" in problem for problem in payload["problems"])
        )

    def test_text_mode_prints_unverified(self) -> None:
        result = run_client(
            "--diff",
            "-",
            "--task",
            "scope",
            "--model",
            "mock-model",
            "--max-chars",
            "16",
            "--mock",
            "good",
            stdin="0123456789abcdefEXTRA",
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("VERDICT: UNVERIFIED", result.stdout)

    def test_untruncated_mock_still_passes(self) -> None:
        result = run_client(
            "--diff",
            "-",
            "--task",
            "scope",
            "--model",
            "mock-model",
            "--mock",
            "good",
            "--json",
            stdin="small diff",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"])
        self.assertFalse(payload["diff_truncated"])
        self.assertFalse(payload["task_truncated"])
        self.assertEqual(payload["problems"], [])

    def test_secret_guard_and_dry_run_survive(self) -> None:
        secret = run_client(
            "--diff",
            "-",
            "--task",
            "scope",
            "--model",
            "mock-model",
            "--mock",
            "good",
            "--json",
            stdin='api_key = "' + "abcdefgh1234" + '"',
        )
        self.assertEqual(secret.returncode, 3)
        self.assertIn("looks like it contains a secret", secret.stderr)

        dry = run_client(
            "--diff",
            "-",
            "--task",
            "scope",
            "--model",
            "mock-model",
            "--dry-run",
            stdin="small diff",
        )
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn("DIFF", dry.stdout)


if __name__ == "__main__":
    unittest.main()
