# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "bin/jev_route.py"


class JevRouteTests(unittest.TestCase):
    def run_route(self, text: str, *args: str) -> dict:
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write(text)
            path = Path(handle.name)
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(CLIENT),
                    "--state",
                    str(path),
                    "--fallback-playbook",
                    "feature",
                    *args,
                ],
                text=True,
                capture_output=True,
                env={"HARNESS_HOME": str(ROOT), "PATH": "/usr/bin:/bin"},
            )
        finally:
            path.unlink()
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_good_mock_returns_fixed_choices(self) -> None:
        result = self.run_route("Fix the redirect bug", "--mock", "good")
        self.assertEqual(result["source"], "jev")
        self.assertEqual(result["playbook"], "bug-fix")
        self.assertEqual(result["tier"], "workhorse")
        self.assertGreaterEqual(result["confidence"], 0.7)

    def test_invalid_choices_fall_back(self) -> None:
        result = self.run_route("Do the work", "--mock", "bad")
        self.assertEqual(result["source"], "deterministic")
        self.assertEqual(result["playbook"], "feature")
        self.assertEqual(result["tier"], "hold")
        self.assertIn("fixed option set", result["fallback_reason"])

    def test_timeout_falls_back(self) -> None:
        result = self.run_route("Do the work", "--mock", "timeout")
        self.assertEqual(result["tier"], "hold")
        self.assertEqual(result["fallback_reason"], "mock timeout")

    def test_secret_shaped_state_never_calls_out(self) -> None:
        field = "api_" + "key"
        result = self.run_route(
            f'fix with {field} = "abcdefgh1234"', "--mock", "good"
        )
        self.assertEqual(result["source"], "deterministic")
        self.assertEqual(result["fallback_reason"], "secret-shaped state")

    def test_dry_run_uses_only_fixed_options(self) -> None:
        payload = self.run_route(
            "Fix the redirect bug", "--dry-run", "--model", "jev-test"
        )
        self.assertEqual(payload["model"], "jev-test")
        questions = payload["questions"]
        self.assertIn("bug-fix", questions["playbook"]["criteria"])
        self.assertIn("workhorse", questions["tier"]["criteria"])
        self.assertIn("hold", questions["tier"]["criteria"])
        self.assertNotIn("invented", questions["playbook"]["criteria"])


if __name__ == "__main__":
    unittest.main()
