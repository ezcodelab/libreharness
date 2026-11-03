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


class GoalStartTests(unittest.TestCase):
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

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            text=True,
            capture_output=True,
        )
        return result.stdout.strip()

    def child(
        self,
        key: str,
        *,
        owns: list[str],
        lane: str = "docs",
        depends_on: list[str] | None = None,
    ) -> dict:
        return {
            "key": key,
            "title": f"Child {key}",
            "scope": f"Change {key}.",
            "acceptance": f"- {key} works",
            "priority": 2,
            "depends_on": depends_on or [],
            "owns": owns,
            "lane": lane,
        }

    def plan(self, children: list[dict]) -> dict:
        lanes: dict[str, list[str]] = {}
        for child in children:
            lanes.setdefault(child["lane"], []).append(child["key"])
        return {
            "goal": {
                "title": "Auto lane goal",
                "project": "demo",
                "scope": "Ready children run in lanes.",
                "acceptance": "- all children pass",
                "priority": 1,
                "autorun": False,
                "max_continuations": 12,
            },
            "children": children,
            "lanes": [{"name": name, "tasks": keys} for name, keys in lanes.items()],
        }

    def create(self, children: list[dict]) -> str:
        result = tasks.create_plan(self.root, self.plan(children))
        return result["goal"]

    def test_creates_lanes_for_ready_children_and_defers_the_rest(self) -> None:
        goal_id = self.create(
            [
                self.child("a", owns=["docs/a.md"]),
                self.child("b", owns=["docs/b.md"]),
                self.child("c", owns=["tests/c.py"], lane="tests"),
                self.child("d", owns=["tests/d.py"], lane="tests"),
                self.child("e", owns=[], lane="docs"),
            ]
        )
        result = tasks.goal_start(self.root, goal_id, repo=self.repo, as_json=True)
        self.assertEqual(result["mode"], "lanes")
        self.assertEqual(len(result["lanes"]), 3)
        self.assertEqual(len(result["ready"]), 5)
        self.assertEqual(result["deferred"][0].rsplit("-", 1)[-1], "d")
        self.assertEqual(result["skipped"][0].rsplit("-", 1)[-1], "e")
        self.assertEqual(
            [item["task"].rsplit("-", 1)[-1] for item in result["lanes"]],
            ["a", "b", "c"],
        )
        for item in result["lanes"]:
            task = tasks.find_task(self.root, item["task"])
            self.assertEqual(task["meta"]["status"], "active")
            self.assertEqual(task["meta"]["branch"], item["branch"])
            self.assertTrue(Path(item["worktree"]).is_dir())
            self.assertIn(item["branch"], self.git("branch", "--list", item["branch"]))
        self.assertEqual(tasks.find_task(self.root, result["deferred"][0])["meta"]["status"], "ready")

    def test_serial_creates_no_worktrees(self) -> None:
        goal_id = self.create(
            [
                self.child("a", owns=["docs/a.md"]),
                self.child("b", owns=["docs/b.md"]),
            ]
        )
        result = tasks.goal_start(self.root, goal_id, repo=self.repo, serial=True, as_json=True)
        self.assertEqual(result["mode"], "serial")
        self.assertEqual(result["lanes"], [])
        self.assertFalse((self.repo.parent / "repo-a").exists())
        self.assertNotIn("feature/a", self.git("branch", "--list", "feature/a"))

    def test_fewer_than_two_laneable_children_is_serial(self) -> None:
        goal_id = self.create(
            [
                self.child("a", owns=["docs/a.md"]),
                self.child("b", owns=[], lane="docs"),
            ]
        )
        result = tasks.goal_start(self.root, goal_id, repo=self.repo, as_json=True)
        self.assertEqual(result["mode"], "serial")
        self.assertIn("fewer than two", result["reason"])
        self.assertEqual(result["lanes"], [])

    def test_open_dependency_is_not_laned(self) -> None:
        goal_id = self.create(
            [
                self.child("a", owns=["docs/a.md"]),
                self.child("b", owns=["docs/b.md"], depends_on=["a"]),
            ]
        )
        result = tasks.goal_start(self.root, goal_id, repo=self.repo, as_json=True)
        self.assertEqual(result["mode"], "serial")
        self.assertEqual(len(result["ready"]), 1)
        self.assertEqual(result["ready"][0].rsplit("-", 1)[-1], "a")
        self.assertNotIn("feature/b", self.git("branch", "--list", "feature/b"))

    def test_max_lanes_caps_the_batch(self) -> None:
        goal_id = self.create(
            [
                self.child("a", owns=["docs/a.md"]),
                self.child("b", owns=["docs/b.md"]),
                self.child("c", owns=["tests/c.py"], lane="tests"),
                self.child("d", owns=["tests/d.py"], lane="tests"),
            ]
        )
        result = tasks.goal_start(self.root, goal_id, repo=self.repo, max_lanes=2, as_json=True)
        self.assertEqual(result["mode"], "lanes")
        self.assertEqual(len(result["lanes"]), 2)
        self.assertEqual(result["deferred"], [result["ready"][2], result["ready"][3]])

    def test_serial_ignores_preexisting_branch(self) -> None:
        goal_id = self.create(
            [
                self.child("a", owns=["docs/a.md"]),
                self.child("b", owns=["docs/b.md"]),
            ]
        )
        self.git("branch", "feature/child-a")
        result = tasks.goal_start(
            self.root, goal_id, repo=self.repo, serial=True, as_json=True
        )
        self.assertEqual(result["mode"], "serial")
        self.assertEqual(result["lanes"], [])

    def test_max_lanes_one_creates_one_lane(self) -> None:
        goal_id = self.create(
            [
                self.child("a", owns=["docs/a.md"]),
                self.child("b", owns=["docs/b.md"]),
            ]
        )
        result = tasks.goal_start(
            self.root, goal_id, repo=self.repo, max_lanes=1, as_json=True
        )
        self.assertEqual(result["mode"], "lanes")
        self.assertEqual(len(result["lanes"]), 1)
        self.assertEqual(len(result["deferred"]), 1)

    def test_partial_lane_failure_keeps_first_lane_visible(self) -> None:
        goal_id = self.create(
            [
                self.child("a", owns=["docs/a.md"]),
                self.child("b", owns=["docs/b.md"]),
            ]
        )
        real_lane = tasks.lane_task
        calls = []

        def flaky_lane(*args, **kwargs):
            calls.append(args[1])
            if len(calls) == 2:
                raise SystemExit("second lane failed")
            return real_lane(*args, **kwargs)

        with mock.patch.object(tasks, "lane_task", side_effect=flaky_lane):
            with self.assertRaises(SystemExit):
                tasks.goal_start(self.root, goal_id, repo=self.repo, as_json=True)
        tasks_by_suffix = {
            task["meta"]["id"].rsplit("-", 1)[-1]: task
            for task in tasks.children_of(self.root, goal_id)
        }
        self.assertEqual(tasks_by_suffix["a"]["meta"]["status"], "active")
        self.assertEqual(tasks_by_suffix["b"]["meta"]["status"], "ready")
        self.assertTrue(Path(tasks_by_suffix["a"]["meta"]["worktree"]).is_dir())

    def test_rejects_existing_worktree_path_before_creating_any_lane(self) -> None:
        goal_id = self.create(
            [
                self.child("a", owns=["docs/a.md"]),
                self.child("b", owns=["docs/b.md"]),
            ]
        )
        (self.repo.parent / "repo-child-a").mkdir()
        with self.assertRaises(SystemExit) as caught:
            tasks.goal_start(self.root, goal_id, repo=self.repo, as_json=True)
        self.assertIn("worktree path already exists", str(caught.exception))
        self.assertFalse((self.repo.parent / "repo-child-b").exists())

    def test_rejects_non_goal(self) -> None:
        task = tasks.new_task(self.root, "One task")
        with self.assertRaises(SystemExit):
            tasks.goal_start(self.root, task["meta"]["id"], repo=self.repo, as_json=True)

    def test_rejects_existing_branch_before_creating_any_lane(self) -> None:
        goal_id = self.create(
            [
                self.child("a", owns=["docs/a.md"]),
                self.child("b", owns=["docs/b.md"]),
            ]
        )
        self.git("branch", "feature/child-a")
        with self.assertRaises(SystemExit) as caught:
            tasks.goal_start(self.root, goal_id, repo=self.repo, as_json=True)
        self.assertIn("branch already exists", str(caught.exception))
        self.assertFalse((self.repo.parent / "repo-child-b").exists())

    def test_rejects_overlapping_owns_before_creating_a_lane(self) -> None:
        goal = tasks.goal_task(self.root, "Overlap", acceptance="- done")
        tasks.new_task(
            self.root,
            "Left",
            parent=goal["meta"]["id"],
            owns="src/",
            lane="docs",
        )
        tasks.new_task(
            self.root,
            "Right",
            parent=goal["meta"]["id"],
            owns="src/main.py",
            lane="docs",
        )
        with self.assertRaises(SystemExit) as caught:
            tasks.goal_start(self.root, goal["meta"]["id"], repo=self.repo, as_json=True)
        self.assertIn("ownership overlaps", str(caught.exception))
        self.assertEqual(self.git("branch", "--list", "feature/left"), "")

    def test_cli_json(self) -> None:
        goal_id = self.create(
            [
                self.child("a", owns=["docs/a.md"]),
                self.child("b", owns=["docs/b.md"]),
            ]
        )
        out = io.StringIO()
        argv = [
            "tasks.py",
            "--root",
            str(self.root),
            "goal-start",
            goal_id,
            "--repo",
            str(self.repo),
            "--json",
        ]
        with mock.patch.object(sys, "argv", argv), redirect_stdout(out):
            self.assertEqual(tasks.main(), 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["goal"], goal_id)
        self.assertEqual(payload["mode"], "lanes")
        self.assertEqual(len(payload["lanes"]), 2)


if __name__ == "__main__":
    unittest.main()
