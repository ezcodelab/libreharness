# SPDX-License-Identifier: MIT
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
import tasks  # noqa: E402


class QueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "state"
        (self.root / "work/tasks").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_claim_review_done(self) -> None:
        task = tasks.new_task(
            self.root,
            "Fix the widget",
            project="demo",
            scope="Only the widget.",
            acceptance="- [ ] widget works",
        )
        self.assertEqual(task["meta"]["status"], "ready")
        claimed = tasks.claim_task(self.root, task["meta"]["id"], owner="lane-a")
        self.assertEqual(claimed["meta"]["status"], "active")
        tasks.set_status(self.root, task["meta"]["id"], "review")
        done = tasks.set_status(
            self.root,
            task["meta"]["id"],
            "done",
            evidence="make test: 12 passed",
        )
        self.assertEqual(done["meta"]["status"], "done")
        log = (self.root / "metrics/workflow-log.csv").read_text()
        rows = list(csv.reader(log.splitlines()))
        self.assertEqual(rows[0][0], "date")
        self.assertEqual(rows[1][1], task["meta"]["id"])
        self.assertEqual(rows[1][5], "done")
        board = (self.root / "work/BOARD.md").read_text()
        self.assertIn(task["meta"]["id"], board)

    def test_done_requires_claim_and_real_evidence(self) -> None:
        task = tasks.new_task(self.root, "Needs proof")
        with self.assertRaises(SystemExit):
            tasks.set_status(self.root, task["meta"]["id"], "done")
        tasks.claim_task(self.root, task["meta"]["id"], owner="lane-a")
        with self.assertRaises(SystemExit):
            tasks.set_status(self.root, task["meta"]["id"], "done", evidence="none")
        with self.assertRaises(SystemExit):
            tasks.set_status(self.root, task["meta"]["id"], "done", evidence="tests pass")
        done = tasks.set_status(
            self.root, task["meta"]["id"], "done", evidence="make check: 42 passed"
        )
        self.assertEqual(done["meta"]["status"], "done")

    def test_claim_records_base_and_rejects_equivalent_worktree(self) -> None:
        first = tasks.new_task(self.root, "First lane")
        second = tasks.new_task(self.root, "Second lane")
        claimed = tasks.claim_task(
            self.root,
            first["meta"]["id"],
            owner="lane-a",
            branch="feature/a",
            base="main",
            worktree="/tmp/lane-a",
        )
        self.assertEqual(claimed["meta"]["base"], "main")
        with self.assertRaises(SystemExit):
            tasks.claim_task(
                self.root,
                second["meta"]["id"],
                owner="lane-b",
                worktree="/tmp/../tmp/lane-a",
            )

    def test_metrics_not_duplicated_on_reopen(self) -> None:
        task = tasks.new_task(self.root, "Reopened")
        tasks.claim_task(self.root, task["meta"]["id"], owner="lane-a")
        tasks.set_status(self.root, task["meta"]["id"], "done", evidence="make check: 1 passed")
        tasks.set_status(self.root, task["meta"]["id"], "active")
        tasks.set_status(self.root, task["meta"]["id"], "done", evidence="make check: 2 passed")
        rows = (self.root / "metrics/workflow-log.csv").read_text().splitlines()
        self.assertEqual(len(rows), 2)  # header + one task row

    def test_dependencies_gate_ready(self) -> None:
        first = tasks.new_task(self.root, "First", acceptance="- [ ] first")
        second = tasks.new_task(
            self.root,
            "Second",
            depends_on=first["meta"]["id"],
            acceptance="- [ ] second",
        )
        self.assertFalse(tasks.is_unblocked(self.root, second)[0])
        tasks.claim_task(self.root, first["meta"]["id"], owner="lane-a")
        tasks.set_status(self.root, first["meta"]["id"], "done", evidence="unit: ok")
        self.assertTrue(tasks.is_unblocked(self.root, second)[0])
        self.assertEqual(tasks.validate(self.root), 0)

    def test_cycle_is_rejected(self) -> None:
        first = tasks.new_task(self.root, "Alpha")
        second = tasks.new_task(self.root, "Beta")
        first["meta"]["depends_on"] = second["meta"]["id"]
        tasks.write_task(first)
        second["meta"]["depends_on"] = first["meta"]["id"]
        tasks.write_task(second)
        self.assertEqual(tasks.validate(self.root), 1)

    def test_ambiguous_prefix_is_clean_error(self) -> None:
        first = tasks.new_task(self.root, "Same one")["meta"]["id"]
        tasks.new_task(self.root, "Same two")
        prefix = first.rsplit("-", 1)[0]
        with self.assertRaises(SystemExit) as caught:
            tasks.find_task(self.root, prefix)
        self.assertIn("ambiguous", str(caught.exception))

    def test_lane_claim_failure_removes_worktree_and_branch(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git not installed")
        repo = Path(self.tmp.name) / "race-repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "--allow-empty", "-m", "base"],
            check=True,
        )
        task = tasks.new_task(self.root, "Race work", acceptance="- [ ] race")
        worktree = Path(self.tmp.name) / "race-repo-race-work"
        with mock.patch.object(tasks, "claim_task", side_effect=SystemExit("lost race")):
            with self.assertRaises(SystemExit):
                tasks.lane_task(self.root, task["meta"]["id"], repo=repo, owner="lane-a")
        self.assertFalse(worktree.exists())
        self.assertNotIn("feature/race-work", tasks.run_git(["branch"], repo))

    def test_goal_requires_all_children(self) -> None:
        goal = tasks.goal_task(
            self.root,
            "Ship the demo",
            scope="The demo works.",
            acceptance="- [ ] demo runs",
            autorun=True,
        )
        self.assertEqual(goal["meta"]["kind"], "goal")
        self.assertEqual(goal["meta"]["autorun"], "true")
        with self.assertRaises(SystemExit):
            tasks.claim_task(self.root, goal["meta"]["id"], owner="lane-a")
        child = tasks.new_task(
            self.root,
            "Demo endpoint",
            parent=goal["meta"]["id"],
            acceptance="- [ ] endpoint answers",
        )
        self.assertEqual(child["meta"]["parent"], goal["meta"]["id"])
        with self.assertRaises(SystemExit):
            tasks.set_status(
                self.root, goal["meta"]["id"], "done", evidence="demo: not yet"
            )
        tasks.claim_task(self.root, child["meta"]["id"], owner="lane-a")
        tasks.set_status(self.root, child["meta"]["id"], "done", evidence="pytest: 4 passed")
        done = tasks.set_status(
            self.root, goal["meta"]["id"], "done", evidence="child evidence checked"
        )
        self.assertEqual(done["meta"]["status"], "done")
        self.assertEqual(tasks.validate(self.root), 0)

    def test_plan_creates_goal_children_lanes_and_deps(self) -> None:
        plan = {
            "goal": {
                "title": "Docs and tests",
                "project": "demo",
                "scope": "Docs are true.",
                "acceptance": "- docs run",
                "autorun": False,
                "max_continuations": 5,
            },
            "children": [
                {
                    "key": "docs",
                    "title": "Docs",
                    "scope": "Write docs.",
                    "acceptance": "- command runs",
                    "owns": ["README.md"],
                    "lane": "docs",
                },
                {
                    "key": "compose",
                    "title": "Compose",
                    "scope": "Add compose.",
                    "acceptance": "- config passes",
                    "depends_on": ["docs"],
                    "owns": ["compose.example.yaml"],
                    "lane": "docs",
                },
                {
                    "key": "tests",
                    "title": "Tests",
                    "scope": "Audit tests.",
                    "acceptance": "- inventory exists",
                    "owns": ["tests/"],
                    "lane": "tests",
                },
            ],
            "lanes": [
                {"name": "docs", "tasks": ["docs", "compose"]},
                {"name": "tests", "tasks": ["tests"]},
            ],
        }
        result = tasks.create_plan(self.root, plan)
        self.assertTrue(result["goal"])
        self.assertEqual(set(result["children"]), {"docs", "compose", "tests"})
        goal = tasks.find_task(self.root, result["goal"])
        self.assertEqual(goal["meta"]["kind"], "goal")
        self.assertEqual(goal["meta"]["max_continuations"], "5")
        self.assertEqual(goal["meta"]["autorun"], "false")
        compose = tasks.find_task(self.root, result["children"]["compose"])
        self.assertEqual(compose["meta"]["parent"], result["goal"])
        self.assertEqual(compose["meta"]["depends_on"], result["children"]["docs"])
        self.assertEqual(compose["meta"]["lane"], "docs")
        self.assertEqual(compose["meta"]["owns"], "compose.example.yaml")
        self.assertEqual(tasks.validate(self.root), 0)

    def test_plan_rejects_cycle_duplicate_ownership_and_dry_run(self) -> None:
        base = {
            "goal": {
                "title": "Bad plan",
                "scope": "x",
                "acceptance": "- y",
            },
            "children": [
                {"key": "a", "title": "A", "scope": "a", "acceptance": "- a", "depends_on": ["b"]},
                {"key": "b", "title": "B", "scope": "b", "acceptance": "- b", "depends_on": ["a"]},
            ],
        }
        with self.assertRaises(SystemExit):
            tasks.validate_plan(self.root, base)
        base["children"][1]["depends_on"] = []
        base["children"][0]["owns"] = ["README.md"]
        base["children"][1]["owns"] = ["README.md"]
        with self.assertRaises(SystemExit):
            tasks.validate_plan(self.root, base)
        base["children"][1]["owns"] = []
        result = tasks.create_plan(self.root, base, dry_run=True)
        self.assertIsNone(result["goal"])
        self.assertEqual(list((self.root / "work/tasks").glob("*.md")), [])

    def test_plan_unattended_override_is_persisted(self) -> None:
        plan = {
            "goal": {
                "title": "Unattended",
                "scope": "x",
                "acceptance": "- y",
                "autorun": False,
            },
            "children": [
                {"key": "one", "title": "One", "scope": "one", "acceptance": "- one"}
            ],
        }
        result = tasks.create_plan(self.root, plan, autorun_override=True)
        goal = tasks.find_task(self.root, result["goal"])
        self.assertEqual(goal["meta"]["autorun"], "true")
        self.assertEqual(goal["meta"]["max_continuations"], "12")

    def test_plan_rejects_bad_lanes_live_ownership_and_autorun_type(self) -> None:
        base = {
            "goal": {
                "title": "Bad plan",
                "scope": "x",
                "acceptance": "- y",
                "autorun": "false",
            },
            "children": [
                {
                    "key": "a",
                    "title": "A",
                    "scope": "a",
                    "acceptance": "- a",
                    "owns": ["README.md"],
                    "lane": "docs",
                }
            ],
            "lanes": [{"name": "docs", "tasks": ["a"]}],
        }
        normalized = tasks.validate_plan(self.root, base)
        self.assertFalse(normalized["goal"]["autorun"])
        with self.assertRaises(SystemExit):
            tasks.validate_plan(
                self.root,
                {
                    **base,
                    "children": [{**base["children"][0], "lane": "tests"}],
                },
            )
        with self.assertRaises(SystemExit):
            tasks.validate_plan(
                self.root,
                {
                    **base,
                    "lanes": [],
                },
            )
        base["children"][0]["owns"] = ["src", "src/api.py"]
        tasks.validate_plan(self.root, base)  # one child may own nested paths
        base["children"][0]["owns"] = ["README.md"]
        base["children"].append(
            {
                "key": "b",
                "title": "B",
                "scope": "b",
                "acceptance": "- b",
                "owns": ["./README.md"],
            }
        )
        with self.assertRaises(SystemExit):
            tasks.validate_plan(self.root, base)
        live = tasks.new_task(self.root, "Live owner", owns="./README.md")
        del base["children"][1]
        base["children"][0]["owns"] = ["README.md"]
        with self.assertRaises(SystemExit):
            tasks.validate_plan(self.root, base)
        self.assertEqual(live["meta"]["owns"], "./README.md")

    def test_plan_cli_json_and_hash(self) -> None:
        plan_path = Path(self.tmp.name) / "plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "goal": {
                        "title": "CLI plan",
                        "scope": "x",
                        "acceptance": "- y",
                    },
                    "children": [
                        {
                            "key": "one",
                            "title": "One",
                            "scope": "one",
                            "acceptance": "- one",
                        }
                    ],
                }
            )
        )
        command = [
            sys.executable,
            str(Path(tasks.__file__)),
            "--root",
            str(self.root),
            "plan",
            "--file",
            str(plan_path),
            "--dry-run",
            "--json",
        ]
        first = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        payload = json.loads(first.stdout)
        self.assertTrue(payload["hash"])
        self.assertIsNone(payload["goal"])
        wrong = subprocess.run(
            [*command[:-2], "--expect-hash", "deadbeef"],
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(wrong.returncode, 0)
        empty_hash = subprocess.run(
            [*command[:-2], "--expect-hash", ""],
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(empty_hash.returncode, 0)
        self.assertEqual(list((self.root / "work/tasks").glob("*.md")), [])

    def test_handoff_and_summary(self) -> None:
        task = tasks.new_task(self.root, "Handoff", scope="Do the thing")
        task["sections"]["Handoff"] = "Next: run the live check."
        tasks.write_task(task)
        shown = tasks.summary(tasks.find_task(self.root, task["meta"]["id"]))
        self.assertIn("Do the thing", shown)
        self.assertIn("no task matching", self._bad_lookup())

    def _bad_lookup(self) -> str:
        try:
            tasks.find_task(self.root, "missing")
        except SystemExit as exc:
            return str(exc)
        return ""

    def test_lane_lifecycle(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git not installed")
        repo = Path(self.tmp.name) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "--allow-empty", "-m", "base"],
            check=True,
        )
        task = tasks.new_task(self.root, "Lane work", acceptance="- [ ] lane works")
        tasks.lane_task(self.root, task["meta"]["id"], repo=repo, owner="lane-a")
        worktree = Path(tasks.find_task(self.root, task["meta"]["id"])["meta"]["worktree"])
        self.assertTrue((worktree / ".git").exists())
        tasks.set_status(self.root, task["meta"]["id"], "review")
        tasks.remove_lane(self.root, task["meta"]["id"])
        self.assertFalse(worktree.exists())
        self.assertNotIn("feature/lane-work", tasks.run_git(["branch"], repo))


if __name__ == "__main__":
    unittest.main()
