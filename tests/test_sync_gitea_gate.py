# SPDX-License-Identifier: MIT
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "sync_gitea_gate.py"


class SyncGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(self.tmp.name) / "repo"
        (self.target / ".github").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write_policy(self, protected):
        (self.target / ".github/merge-policy.json").write_text(
            '{"protected_paths": ' + repr(protected).replace("'", '"') + "}"
        )

    def run_sync(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--target", str(self.target), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_writes_github_layout_and_checks_clean(self):
        self.write_policy([])
        result = self.run_sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            (self.target / ".github/workflows/auto-merge.yml").is_file()
        )
        check = self.run_sync("--check")
        self.assertEqual(check.returncode, 0, check.stderr)

    def test_gitea_layout_requires_protected_gate_path(self):
        (self.target / ".gitea/workflows").mkdir(parents=True)
        self.write_policy([".github/"])
        result = self.run_sync()
        self.assertEqual(result.returncode, 1)
        self.assertIn(".gitea/", result.stderr)

    def test_gitea_layout_with_protected_path_passes(self):
        (self.target / ".gitea/workflows").mkdir(parents=True)
        self.write_policy([".gitea/"])
        result = self.run_sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            (self.target / ".gitea/workflows/auto-merge.yml").is_file()
        )
        self.assertFalse(
            (self.target / ".github/workflows/auto-merge.yml").exists()
        )

    def test_stale_gate_in_inactive_layout_fails(self):
        (self.target / ".gitea/workflows").mkdir(parents=True)
        self.write_policy([".gitea/"])
        stale = self.target / ".github/workflows/auto-merge.yml"
        stale.parent.mkdir(parents=True)
        stale.write_text("stale\n")
        result = self.run_sync("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("non-scanned", result.stderr)

    def test_workflow_in_non_scanned_directory_fails(self):
        (self.target / ".gitea/workflows").mkdir(parents=True)
        self.write_policy([".gitea/"])
        inactive = self.target / ".github/workflows/other.yml"
        inactive.parent.mkdir(parents=True)
        inactive.write_text("name: other\n")
        result = self.run_sync("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("non-scanned", result.stderr)

    def test_missing_policy_fails(self):
        result = self.run_sync()
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing", result.stderr)


if __name__ == "__main__":
    unittest.main()
