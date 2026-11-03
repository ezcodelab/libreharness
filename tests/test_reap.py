# SPDX-License-Identifier: MIT
from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
import tasks  # noqa: E402


class ReapTests(unittest.TestCase):
    def setUp(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git not installed")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "state"
        (self.root / "work/tasks").mkdir(parents=True)
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.git("commit", "-q", "--allow-empty", "-m", "base")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def git(self, *args: str, cwd: Path | None = None) -> str:
        result = subprocess.run(
            ["git", "-C", str(cwd or self.repo), *args],
            check=True,
            text=True,
            capture_output=True,
        )
        return result.stdout.strip()

    def lane(self, title: str, *, parent: str = "", owns: str = "") -> dict:
        task = tasks.new_task(
            self.root,
            title,
            parent=parent,
            owns=owns,
            acceptance="- lane works",
        )
        return tasks.lane_task(
            self.root, task["meta"]["id"], repo=self.repo, owner="lane-a", quiet=True
        )

    def commit(self, worktree: Path, name: str) -> None:
        (worktree / name).write_text(name)
        self.git("add", name, cwd=worktree)
        self.git("commit", "-q", "-m", f"add {name}", cwd=worktree)

    def merge(self, branch: str) -> None:
        self.git("merge", "--no-ff", branch, "-m", f"merge {branch}")

    def test_reaps_clean_merged_lane(self) -> None:
        task = self.lane("Clean work")
        self.commit(Path(task["meta"]["worktree"]), "work.txt")
        self.merge(task["meta"]["branch"])
        tasks.set_status(self.root, task["meta"]["id"], "review")
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 0)
        self.assertFalse(Path(task["meta"]["worktree"]).exists())
        self.assertEqual(
            self.git("branch", "--list", task["meta"]["branch"]),
            "",
        )
        stored = tasks.find_task(self.root, task["meta"]["id"])
        self.assertEqual(stored["meta"]["worktree"], "")
        self.assertEqual(stored["meta"]["branch"], "")

    def test_reaps_lane_merged_into_integration_branch(self) -> None:
        task = self.lane("Integration work")
        self.commit(Path(task["meta"]["worktree"]), "integration.txt")
        self.git("switch", "-c", "integration")
        self.merge(task["meta"]["branch"])
        self.git("switch", "main")
        tasks.set_status(self.root, task["meta"]["id"], "review")
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 0)
        self.assertFalse(Path(task["meta"]["worktree"]).exists())
        self.assertEqual(self.git("branch", "--list", task["meta"]["branch"]), "")

    def test_retains_ignored_file(self) -> None:
        (self.repo / ".gitignore").write_text("ignored.txt\n")
        self.git("add", ".gitignore")
        self.git("commit", "-q", "-m", "ignore")
        task = self.lane("Ignored work")
        (Path(task["meta"]["worktree"]) / "ignored.txt").write_text("local")
        tasks.set_status(self.root, task["meta"]["id"], "review")
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 1)
        self.assertTrue(Path(task["meta"]["worktree"]).exists())

    def test_retains_modified_tracked_file(self) -> None:
        (self.repo / "tracked.txt").write_text("base\n")
        self.git("add", "tracked.txt")
        self.git("commit", "-q", "-m", "tracked")
        task = self.lane("Tracked work")
        (Path(task["meta"]["worktree"]) / "tracked.txt").write_text("changed\n")
        tasks.set_status(self.root, task["meta"]["id"], "review")
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 1)
        self.assertTrue(Path(task["meta"]["worktree"]).exists())

    def test_retains_unmerged_tip_after_partial_merge(self) -> None:
        task = self.lane("Partial work")
        worktree = Path(task["meta"]["worktree"])
        self.commit(worktree, "first.txt")
        self.merge(task["meta"]["branch"])
        self.commit(worktree, "second.txt")
        tasks.set_status(self.root, task["meta"]["id"], "review")
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 1)
        self.assertTrue(worktree.exists())

    def test_retains_dirty_lane(self) -> None:
        task = self.lane("Dirty work")
        worktree = Path(task["meta"]["worktree"])
        (worktree / "dirty.txt").write_text("uncommitted")
        tasks.set_status(self.root, task["meta"]["id"], "review")
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 1)
        self.assertTrue(worktree.exists())
        self.assertIn(task["meta"]["branch"], self.git("branch"))

    def test_retains_unmerged_lane(self) -> None:
        task = self.lane("Unmerged work")
        self.commit(Path(task["meta"]["worktree"]), "unmerged.txt")
        tasks.set_status(self.root, task["meta"]["id"], "review")
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 1)
        self.assertTrue(Path(task["meta"]["worktree"]).exists())
        self.assertIn(task["meta"]["branch"], self.git("branch"))

    def test_retains_active_lane(self) -> None:
        task = self.lane("Active work")
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 1)
        self.assertTrue(Path(task["meta"]["worktree"]).exists())

    def test_retains_missing_and_no_worktree_as_skips(self) -> None:
        task = tasks.new_task(self.root, "No lane")
        tasks.claim_task(self.root, task["meta"]["id"], owner="lane-a")
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 0)

    def test_reaps_goal_and_retains_unmerged_child(self) -> None:
        goal = tasks.goal_task(self.root, "Reap goal", acceptance="- goal done")
        clean = self.lane("Clean child", parent=goal["meta"]["id"], owns="clean.txt")
        dirty = self.lane("Dirty child", parent=goal["meta"]["id"], owns="dirty.txt")
        self.commit(Path(clean["meta"]["worktree"]), "clean.txt")
        self.merge(clean["meta"]["branch"])
        (Path(dirty["meta"]["worktree"]) / "dirty.txt").write_text("uncommitted")
        tasks.set_status(self.root, clean["meta"]["id"], "review")
        tasks.set_status(self.root, dirty["meta"]["id"], "review")
        self.assertEqual(tasks.reap(self.root, goal["meta"]["id"]), 1)
        self.assertFalse(Path(clean["meta"]["worktree"]).exists())
        self.assertTrue(Path(dirty["meta"]["worktree"]).exists())

    def test_dry_run_does_not_remove(self) -> None:
        task = self.lane("Dry work")
        self.commit(Path(task["meta"]["worktree"]), "dry.txt")
        self.merge(task["meta"]["branch"])
        tasks.set_status(self.root, task["meta"]["id"], "review")
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"], dry_run=True), 0)
        self.assertTrue(Path(task["meta"]["worktree"]).exists())
        self.assertIn(task["meta"]["branch"], self.git("branch"))

    def test_cli_json(self) -> None:
        task = self.lane("CLI work")
        self.commit(Path(task["meta"]["worktree"]), "cli.txt")
        self.merge(task["meta"]["branch"])
        tasks.set_status(self.root, task["meta"]["id"], "review")
        out = io.StringIO()
        argv = [
            "tasks.py",
            "--root",
            str(self.root),
            "reap",
            task["meta"]["id"],
            "--repo",
            str(self.repo),
            "--json",
        ]
        with mock.patch.object(sys, "argv", argv), redirect_stdout(out):
            self.assertEqual(tasks.main(), 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["task"], task["meta"]["id"])
        self.assertEqual(payload["removed"][0]["outcome"], "removed")


if __name__ == "__main__":
    unittest.main()
