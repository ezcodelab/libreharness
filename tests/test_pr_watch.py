# SPDX-License-Identifier: MIT
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "pr_watch.py"
SHA = "a" * 40


class PRWatchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.gh = self.bin / "gh"
        self.merge_log = self.base / "merge.log"
        self.gh.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "args = sys.argv[1:]\n"
            "if args[:2] == ['pr', 'view']:\n"
            "    print(os.environ['FAKE_PR_JSON'])\n"
            "elif args[:2] == ['pr', 'merge']:\n"
            "    with open(os.environ['FAKE_MERGE_LOG'], 'a') as log:\n"
            "        log.write(' '.join(args) + '\\n')\n"
            "else:\n"
            "    sys.exit(2)\n",
            encoding="utf-8",
        )
        self.gh.chmod(self.gh.stat().st_mode | stat.S_IXUSR)
        self.verifier = self.base / "verifier.txt"
        self.evidence = self.base / "evidence.txt"
        self.verifier.write_text(f"PASS {SHA}\n", encoding="utf-8")
        self.evidence.write_text("python3 -m unittest: OK\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_watch(self, pr, *extra, path=None):
        env = os.environ.copy()
        env["PATH"] = path or f"{self.bin}:{env['PATH']}"
        env["FAKE_PR_JSON"] = json.dumps(pr)
        env["FAKE_MERGE_LOG"] = str(self.merge_log)
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--pr",
                "7",
                "--verifier-pass",
                str(self.verifier),
                "--evidence",
                str(self.evidence),
                *extra,
            ],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def pr(self, **overrides):
        data = {
            "state": "OPEN",
            "isDraft": False,
            "mergeable": "MERGEABLE",
            "headRefOid": SHA,
            "statusCheckRollup": [
                {"name": "test", "status": "COMPLETED", "conclusion": "SUCCESS"}
            ],
            "url": "https://example.invalid/pr/7",
        }
        data.update(overrides)
        return data

    def test_green_pr_merges(self):
        result = self.run_watch(self.pr(), "--merge")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("merged PR 7", result.stdout)
        self.assertIn("pr merge 7 --squash --match-head-commit " + SHA,
                      self.merge_log.read_text(encoding="utf-8"))

    def test_dry_run_does_not_merge(self):
        result = self.run_watch(self.pr())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dry run", result.stdout)
        self.assertFalse(self.merge_log.exists())

    def test_missing_verifier_pass_blocks(self):
        self.verifier.write_text(f"FAIL {SHA}\n", encoding="utf-8")
        result = self.run_watch(self.pr(), "--merge")
        self.assertEqual(result.returncode, 2)
        self.assertIn("did not return PASS", result.stderr)
        self.assertFalse(self.merge_log.exists())

    def test_verifier_sha_must_match_head(self):
        self.verifier.write_text("PASS " + "b" * 40 + "\n", encoding="utf-8")
        result = self.run_watch(self.pr(), "--merge")
        self.assertEqual(result.returncode, 2)
        self.assertIn("does not match PR head", result.stderr)

    def test_fail_mentioning_pass_blocks(self):
        self.verifier.write_text(
            f"FAIL: independent verifier did not PASS {SHA}\n", encoding="utf-8"
        )
        result = self.run_watch(self.pr(), "--merge")
        self.assertEqual(result.returncode, 2)
        self.assertIn("did not return PASS", result.stderr)

    def test_pass_without_sha_blocks(self):
        self.verifier.write_text("PASS\n", encoding="utf-8")
        result = self.run_watch(self.pr(), "--merge")
        self.assertEqual(result.returncode, 2)
        self.assertIn("did not return PASS", result.stderr)

    def test_neutral_check_blocks(self):
        pr = self.pr(statusCheckRollup=[
            {"name": "test", "status": "COMPLETED", "conclusion": "NEUTRAL"}
        ])
        result = self.run_watch(pr, "--merge")
        self.assertEqual(result.returncode, 2)
        self.assertIn("check test: NEUTRAL", result.stderr)

    def test_failed_check_blocks(self):
        pr = self.pr(statusCheckRollup=[
            {"name": "test", "status": "COMPLETED", "conclusion": "FAILURE"}
        ])
        result = self.run_watch(pr, "--merge")
        self.assertEqual(result.returncode, 2)
        self.assertIn("check test: FAILURE", result.stderr)

    def test_conflict_blocks(self):
        result = self.run_watch(self.pr(mergeable="CONFLICTING"), "--merge")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not mergeable", result.stderr)

    def test_missing_evidence_blocks(self):
        self.evidence.write_text("", encoding="utf-8")
        result = self.run_watch(self.pr(), "--merge")
        self.assertEqual(result.returncode, 2)
        self.assertIn("evidence file", result.stderr)

    def test_no_forge_is_a_clear_stop(self):
        empty = self.base / "empty"
        empty.mkdir()
        result = self.run_watch(self.pr(), "--merge", path=str(empty))
        self.assertEqual(result.returncode, 3)
        self.assertIn("gh is not installed", result.stderr)


if __name__ == "__main__":
    unittest.main()
