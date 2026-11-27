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

import tasks


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
        self.git("config", "commit.gpgsign", "false")
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

    def make_task(self, title: str, **kwargs) -> dict:
        kwargs.setdefault("scope", "Test the lane boundary.")
        kwargs.setdefault("acceptance", "- [ ] lane fixture passes")
        task = tasks.new_task(self.root, title, **kwargs)
        task["sections"]["Plan"] = (
            'Data shape: {"state":"idle|running"}\n'
            "Verify: python3 -m unittest tests.test_tasks -v\n"
        )
        tasks.write_task(task)
        return task

    def pass_review(self, task: dict, repo: Path | None = None) -> None:
        worktree = task["meta"].get("worktree", "")
        target = repo or (Path(worktree) if worktree else self.repo)
        verify = tasks.plan_verify(task)
        path = tasks.review_path(self.root, task["meta"]["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "task": task["meta"]["id"],
                    "head": tasks.git_head(target),
                    "diff_sha256": tasks.review_diff(target),
                    "contract_sha256": tasks.review_contract_digest(task),
                    "verdict": "PASS",
                    "checks": [{"command": verify, "exit": 0}],
                }
            )
        )

    def review_status(self, task: dict, repo: Path | None = None) -> dict:
        self.pass_review(task, repo)
        return tasks.set_status(
            self.root, task["meta"]["id"], "review", repo=repo
        )

    def lane(self, title: str, *, parent: str = "", owns: str = "") -> dict:
        task = self.make_task(
            title,
            parent=parent,
            owns=owns,
            acceptance="- [ ] lane works",
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
        self.review_status(task)
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
        self.review_status(task)
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 0)
        self.assertFalse(Path(task["meta"]["worktree"]).exists())
        self.assertEqual(self.git("branch", "--list", task["meta"]["branch"]), "")

    def test_reports_branch_removal_failure_after_worktree_removal(self) -> None:
        task = self.lane("Branch failure")
        self.commit(Path(task["meta"]["worktree"]), "branch.txt")
        self.merge(task["meta"]["branch"])
        self.review_status(task)
        real_git = tasks.run_git

        def flaky_git(args, cwd):
            if args[:2] == ["branch", "-D"]:
                raise SystemExit("branch delete blocked")
            return real_git(args, cwd)

        with mock.patch.object(tasks, "run_git", side_effect=flaky_git):
            self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 1)
        stored = tasks.find_task(self.root, task["meta"]["id"])
        self.assertEqual(stored["meta"]["worktree"], "")
        self.assertIn(task["meta"]["branch"], self.git("branch"))

    def test_retains_ignored_file(self) -> None:
        (self.repo / ".gitignore").write_text("ignored.txt\n")
        self.git("add", ".gitignore")
        self.git("commit", "-q", "-m", "ignore")
        task = self.lane("Ignored work")
        (Path(task["meta"]["worktree"]) / "ignored.txt").write_text("local")
        self.review_status(task)
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 1)
        self.assertTrue(Path(task["meta"]["worktree"]).exists())

    def test_retains_modified_tracked_file(self) -> None:
        (self.repo / "tracked.txt").write_text("base\n")
        self.git("add", "tracked.txt")
        self.git("commit", "-q", "-m", "tracked")
        task = self.lane("Tracked work")
        (Path(task["meta"]["worktree"]) / "tracked.txt").write_text("changed\n")
        self.review_status(task)
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 1)
        self.assertTrue(Path(task["meta"]["worktree"]).exists())

    def test_retains_unmerged_tip_after_partial_merge(self) -> None:
        task = self.lane("Partial work")
        worktree = Path(task["meta"]["worktree"])
        self.commit(worktree, "first.txt")
        self.merge(task["meta"]["branch"])
        self.commit(worktree, "second.txt")
        self.review_status(task)
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 1)
        self.assertTrue(worktree.exists())

    def test_retains_dirty_lane(self) -> None:
        task = self.lane("Dirty work")
        worktree = Path(task["meta"]["worktree"])
        (worktree / "dirty.txt").write_text("uncommitted")
        self.review_status(task)
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 1)
        self.assertTrue(worktree.exists())
        self.assertIn(task["meta"]["branch"], self.git("branch"))

    def test_retains_unmerged_lane(self) -> None:
        task = self.lane("Unmerged work")
        self.commit(Path(task["meta"]["worktree"]), "unmerged.txt")
        self.review_status(task)
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 1)
        self.assertTrue(Path(task["meta"]["worktree"]).exists())
        self.assertIn(task["meta"]["branch"], self.git("branch"))

    def test_retains_active_lane(self) -> None:
        task = self.lane("Active work")
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 1)
        self.assertTrue(Path(task["meta"]["worktree"]).exists())

    def test_retains_missing_and_no_worktree_as_skips(self) -> None:
        task = self.make_task("No lane")
        tasks.claim_task(self.root, task["meta"]["id"], owner="lane-a")
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"]), 0)

    def test_reaps_goal_and_retains_unmerged_child(self) -> None:
        goal = tasks.goal_task(self.root, "Reap goal", acceptance="- goal done")
        clean = self.lane("Clean child", parent=goal["meta"]["id"], owns="clean.txt")
        dirty = self.lane("Dirty child", parent=goal["meta"]["id"], owns="dirty.txt")
        self.commit(Path(clean["meta"]["worktree"]), "clean.txt")
        self.merge(clean["meta"]["branch"])
        (Path(dirty["meta"]["worktree"]) / "dirty.txt").write_text("uncommitted")
        self.review_status(clean)
        self.review_status(dirty)
        self.assertEqual(tasks.reap(self.root, goal["meta"]["id"]), 1)
        self.assertFalse(Path(clean["meta"]["worktree"]).exists())
        self.assertTrue(Path(dirty["meta"]["worktree"]).exists())

    def test_dry_run_does_not_remove(self) -> None:
        task = self.lane("Dry work")
        self.commit(Path(task["meta"]["worktree"]), "dry.txt")
        self.merge(task["meta"]["branch"])
        self.review_status(task)
        self.assertEqual(tasks.reap(self.root, task["meta"]["id"], dry_run=True), 0)
        self.assertTrue(Path(task["meta"]["worktree"]).exists())
        self.assertIn(task["meta"]["branch"], self.git("branch"))

    def test_cli_json(self) -> None:
        task = self.lane("CLI work")
        self.commit(Path(task["meta"]["worktree"]), "cli.txt")
        self.merge(task["meta"]["branch"])
        self.review_status(task)
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
