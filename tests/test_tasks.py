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
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "Test"], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "commit.gpgsign", "false"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "-q", "--allow-empty", "-m", "base"],
            check=True,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def make_task(self, title: str, *, tags: str = "", **kwargs) -> dict:
        kwargs.setdefault("scope", "Test the task boundary.")
        kwargs.setdefault("acceptance", "- [ ] test fixture passes")
        task = tasks.new_task(self.root, title, tags=tags, **kwargs)
        task["sections"]["Plan"] = (
            'Data shape: {"state":"idle|running"}\n'
            "Verify: python3 -m unittest tests.test_tasks -v\n"
        )
        tasks.write_task(task)
        return task

    def pass_review(self, task: dict, repo: Path | None = None) -> None:
        verify = tasks.plan_verify(task)
        path = tasks.review_path(self.root, task["meta"]["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "task": task["meta"]["id"],
                    "head": tasks.git_head(repo or self.repo),
                    "diff_sha256": tasks.review_diff(repo or self.repo),
                    "contract_sha256": tasks.review_contract_digest(task),
                    "verdict": "PASS",
                    "checks": [{"command": verify, "exit": 0}],
                }
            )
        )

    def test_claim_rejects_placeholder_scope_and_acceptance(self) -> None:
        placeholder_scope = self.make_task("Placeholder scope", scope="")
        with self.assertRaises(SystemExit) as caught:
            tasks.claim_task(
                self.root, placeholder_scope["meta"]["id"], owner="lane-a"
            )
        self.assertIn("concrete Scope", str(caught.exception))

        auto_scope = self.make_task(
            "Auto scope",
            scope="Auto-captured prompt; confirm scope and acceptance.",
        )
        with self.assertRaises(SystemExit) as caught:
            tasks.claim_task(self.root, auto_scope["meta"]["id"], owner="lane-a")
        self.assertIn("concrete Scope", str(caught.exception))

        placeholder_acceptance = self.make_task(
            "Placeholder acceptance", acceptance="- [ ] TBD: confirm before claiming."
        )
        with self.assertRaises(SystemExit) as caught:
            tasks.claim_task(
                self.root, placeholder_acceptance["meta"]["id"], owner="lane-a"
            )
        self.assertIn("TBD", str(caught.exception))

        missing_item = self.make_task(
            "Missing item", acceptance="The widget works."
        )
        with self.assertRaises(SystemExit) as caught:
            tasks.claim_task(self.root, missing_item["meta"]["id"], owner="lane-a")
        self.assertIn("at least one", str(caught.exception))

        concrete = self.make_task(
            "Concrete", scope="Only the widget.", acceptance="- [ ] widget works"
        )
        self.assertEqual(
            tasks.claim_task(self.root, concrete["meta"]["id"], owner="lane-a")[
                "meta"
            ]["status"],
            "active",
        )

    def test_create_claim_review_done(self) -> None:
        task = self.make_task(
            "Fix the widget",
            project="demo",
            scope="Only the widget.",
            acceptance="- [x] widget works",
        )
        self.assertEqual(task["meta"]["status"], "ready")
        claimed = tasks.claim_task(self.root, task["meta"]["id"], owner="lane-a")
        self.assertEqual(claimed["meta"]["status"], "active")
        self.pass_review(task)
        tasks.set_status(self.root, task["meta"]["id"], "review", repo=self.repo)
        done = tasks.set_status(
            self.root,
            task["meta"]["id"],
            "done",
            evidence="make test: 12 passed",
            repo=self.repo,
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
        task = self.make_task(
            "Needs proof", acceptance="- [x] proof exists"
        )
        with self.assertRaises(SystemExit):
            tasks.set_status(self.root, task["meta"]["id"], "done")
        tasks.claim_task(self.root, task["meta"]["id"], owner="lane-a")
        with self.assertRaises(SystemExit):
            tasks.set_status(self.root, task["meta"]["id"], "done", evidence="none")
        with self.assertRaises(SystemExit):
            tasks.set_status(self.root, task["meta"]["id"], "done", evidence="tests pass")
        self.pass_review(task)
        done = tasks.set_status(
            self.root,
            task["meta"]["id"],
            "done",
            evidence="make check: 42 passed",
            repo=self.repo,
        )
        self.assertEqual(done["meta"]["status"], "done")

    def test_done_requires_review_artifact(self) -> None:
        task = self.make_task("Needs review", acceptance="- [x] proof exists")
        tasks.claim_task(self.root, task["meta"]["id"], owner="lane-a")
        with self.assertRaises(SystemExit) as caught:
            tasks.set_status(
                self.root,
                task["meta"]["id"],
                "done",
                evidence="make check: 42 passed",
                repo=self.repo,
            )
        self.assertIn("review artifact", str(caught.exception))
        self.pass_review(task)
        done = tasks.set_status(
            self.root,
            task["meta"]["id"],
            "done",
            evidence="make check: 42 passed",
            repo=self.repo,
        )
        self.assertEqual(done["meta"]["status"], "done")

    def test_done_rejects_unchecked_acceptance(self) -> None:
        task = self.make_task(
            "Unfinished", acceptance="- [ ] widget works\n- [x] docs"
        )
        tasks.claim_task(self.root, task["meta"]["id"], owner="lane-a")
        with self.assertRaises(SystemExit) as caught:
            tasks.set_status(
                self.root,
                task["meta"]["id"],
                "done",
                evidence="make check: 42 passed",
            )
        self.assertIn("widget works", str(caught.exception))

    def test_done_rejects_tbd_acceptance(self) -> None:
        task = self.make_task("Placeholder")
        tasks.claim_task(self.root, task["meta"]["id"], owner="lane-a")
        task = tasks.find_task(self.root, task["meta"]["id"])
        task["sections"]["Acceptance"] = "- TBD"
        tasks.write_task(task)
        with self.assertRaises(SystemExit) as caught:
            tasks.set_status(
                self.root,
                task["meta"]["id"],
                "done",
                evidence="make check: 42 passed",
            )
        self.assertIn("TBD", str(caught.exception))

    def test_done_rejects_deferred_section(self) -> None:
        task = self.make_task(
            "Deferred", acceptance="- [x] main work"
        )
        task["sections"]["Deferred"] = "- cleanup later"
        tasks.write_task(task)
        tasks.claim_task(self.root, task["meta"]["id"], owner="lane-a")
        with self.assertRaises(SystemExit) as caught:
            tasks.set_status(
                self.root,
                task["meta"]["id"],
                "done",
                evidence="make check: 42 passed",
            )
        self.assertIn("deferred", str(caught.exception).lower())

    def test_claim_records_base_and_rejects_equivalent_worktree(self) -> None:
        first = self.make_task("First lane")
        second = self.make_task("Second lane")
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
        task = self.make_task(
            "Reopened", acceptance="- [x] reopened"
        )
        tasks.claim_task(self.root, task["meta"]["id"], owner="lane-a")
        self.pass_review(task)
        tasks.set_status(
            self.root,
            task["meta"]["id"],
            "done",
            evidence="make check: 1 passed",
            repo=self.repo,
        )
        tasks.set_status(self.root, task["meta"]["id"], "active")
        tasks.set_status(
            self.root,
            task["meta"]["id"],
            "done",
            evidence="make check: 2 passed",
            repo=self.repo,
        )
        rows = (self.root / "metrics/workflow-log.csv").read_text().splitlines()
        self.assertEqual(len(rows), 2)  # header + one task row

    def test_dependencies_gate_ready(self) -> None:
        first = self.make_task("First", acceptance="- [x] first")
        second = self.make_task(
            "Second",
            depends_on=first["meta"]["id"],
            acceptance="- [ ] second",
        )
        self.assertFalse(tasks.is_unblocked(self.root, second)[0])
        tasks.claim_task(self.root, first["meta"]["id"], owner="lane-a")
        self.pass_review(first)
        tasks.set_status(
            self.root,
            first["meta"]["id"],
            "done",
            evidence="unit: ok",
            repo=self.repo,
        )
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
            ["git", "-C", str(repo), "config", "commit.gpgsign", "false"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "--allow-empty", "-m", "base"],
            check=True,
        )
        task = self.make_task("Race work", acceptance="- [ ] race")
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
            acceptance="- [x] demo runs",
            autorun=True,
        )
        self.assertEqual(goal["meta"]["kind"], "goal")
        self.assertEqual(goal["meta"]["autorun"], "true")
        with self.assertRaises(SystemExit):
            tasks.claim_task(self.root, goal["meta"]["id"], owner="lane-a")
        child = self.make_task(
            "Demo endpoint",
            parent=goal["meta"]["id"],
            acceptance="- [x] endpoint answers",
        )
        self.assertEqual(child["meta"]["parent"], goal["meta"]["id"])
        with self.assertRaises(SystemExit):
            tasks.set_status(
                self.root, goal["meta"]["id"], "done", evidence="demo: not yet"
            )
        tasks.claim_task(self.root, child["meta"]["id"], owner="lane-a")
        self.pass_review(child)
        tasks.set_status(
            self.root,
            child["meta"]["id"],
            "done",
            evidence="pytest: 4 passed",
            repo=self.repo,
        )
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
        self.assertEqual(goal["meta"]["max_continuations"], "")

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

    def test_handoff_requires_structured_fields_and_packet_context(self) -> None:
        task = tasks.new_task(
            self.root,
            "Handoff",
            scope="Do the thing",
            acceptance="- [ ] thing works",
        )
        with self.assertRaises(SystemExit) as caught:
            tasks.write_handoff(
                self.root,
                task["meta"]["id"],
                "- **State:** active\n- **Next:** run the live check.",
            )
        self.assertIn("missing Decisions", str(caught.exception))

        text = "\n".join(
            [
                "- **State:** in progress",
                "- **Decisions:** keep the queue boundary",
                "- **Files:** bin/tasks.py",
                "- **Checks:** python3 -m unittest tests.test_tasks -v: PASS",
                "- **Open:** none",
                "- **Next:** run the live check",
                "- **Context:** task packet",
            ]
        )
        written = tasks.write_handoff(self.root, task["meta"]["id"], text)
        self.assertEqual(written["meta"]["id"], task["meta"]["id"])
        shown = tasks.packet(tasks.find_task(self.root, task["meta"]["id"]))
        self.assertIn("Do the thing", shown)
        self.assertIn("- [ ] thing works", shown)
        self.assertIn("run the live check", shown)
        self.assertEqual(tasks.validate(self.root), 0)
        checked = subprocess.run(
            [
                sys.executable,
                str(Path(tasks.__file__)),
                "--root",
                str(self.root),
                "handoff",
                task["meta"]["id"],
                "--check",
            ],
            text=True,
            capture_output=True,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn("handoff: OK", checked.stdout)
        self.assertIn("no task matching", self._bad_lookup())

    def test_handoff_check_rejects_an_incomplete_edit(self) -> None:
        task = self.make_task("Broken handoff")
        tasks.claim_task(self.root, task["meta"]["id"], owner="lane-a")
        task = tasks.find_task(self.root, task["meta"]["id"])
        task["sections"]["Handoff"] = "- **Next:** keep going"
        tasks.write_task(task)
        checked = subprocess.run(
            [
                sys.executable,
                str(Path(tasks.__file__)),
                "--root",
                str(self.root),
                "handoff",
                task["meta"]["id"],
                "--check",
            ],
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(checked.returncode, 0)
        self.assertIn("missing State", checked.stderr)
        self.assertEqual(tasks.validate(self.root), 0)

    def _bad_lookup(self) -> str:
        try:
            tasks.find_task(self.root, "missing")
        except SystemExit as exc:
            return str(exc)
        return ""

    def test_lane_lifecycle(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git not installed")
        repo = self.repo
        task = self.make_task("Lane work", acceptance="- [ ] lane works")
        tasks.lane_task(self.root, task["meta"]["id"], repo=repo, owner="lane-a")
        worktree = Path(tasks.find_task(self.root, task["meta"]["id"])["meta"]["worktree"])
        self.assertTrue((worktree / ".git").exists())
        self.pass_review(task, repo=worktree)
        tasks.set_status(self.root, task["meta"]["id"], "review", repo=worktree)
        tasks.remove_lane(self.root, task["meta"]["id"])
        self.assertFalse(worktree.exists())
        self.assertNotIn("feature/lane-work", tasks.run_git(["branch"], repo))


class PlanContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "state"
        (self.root / "work/tasks").mkdir(parents=True)
        self.repo = Path(self.tmp.name) / "repo"
        (self.repo / "src").mkdir(parents=True)
        (self.repo / "src/widget.py").write_text(
            "class Widget:\n    pass\n\n"
            "# def CommentOnly(\n"
        )
        (self.repo / "src/widget.js").write_text(
            "export function buildWidget() {}\n"
        )
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "Test"], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "commit.gpgsign", "false"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "-q", "--allow-empty", "-m", "base"],
            check=True,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def task(self, plan: str, tags: str = "") -> dict:
        task = tasks.new_task(
            self.root,
            "Plan contract",
            tags=tags,
            scope="Only the plan contract.",
            acceptance="- [x] contract holds",
        )
        task["sections"]["Plan"] = plan
        tasks.write_task(task)
        return task

    def claim(self, task: dict) -> dict:
        return tasks.claim_task(
            self.root, task["meta"]["id"], owner="lane-a", repo=self.repo
        )

    def test_claim_requires_structured_data_shape(self) -> None:
        verify = "Verify: python3 -m unittest tests.test_tasks -v\n"
        with self.assertRaises(SystemExit):
            self.claim(self.task(verify))
        with self.assertRaises(SystemExit):
            self.claim(
                self.task("Data shape: the widget owns a small state\n" + verify)
            )
        with self.assertRaises(SystemExit):
            self.claim(self.task("Data shape: {}\n" + verify))

    def test_claim_accepts_json_and_declaration_paths(self) -> None:
        verify = "Verify: python3 -m unittest tests.test_tasks -v\n"
        json_task = self.task('Data shape: {"state":"idle|running"}\n' + verify)
        self.assertEqual(self.claim(json_task)["meta"]["status"], "active")
        path_task = self.task("Data shape: path src/widget.py#Widget\n" + verify)
        self.assertEqual(self.claim(path_task)["meta"]["status"], "active")
        js_task = self.task("Data shape: path src/widget.js#buildWidget\n" + verify)
        self.assertEqual(self.claim(js_task)["meta"]["status"], "active")

    def test_comment_only_symbol_does_not_pass(self) -> None:
        task = self.task(
            "Data shape: path src/widget.py#CommentOnly\n"
            "Verify: python3 -m unittest tests.test_tasks -v\n"
        )
        with self.assertRaises(SystemExit):
            self.claim(task)

    def test_none_needs_docs_or_chore_tag(self) -> None:
        verify = "Verify: python3 -m unittest tests.test_tasks -v\n"
        with self.assertRaises(SystemExit):
            self.claim(self.task("Data shape: none - prose only\n" + verify))
        docs = self.task("Data shape: none - prose only\n" + verify, tags="docs")
        self.assertEqual(self.claim(docs)["meta"]["status"], "active")

    def test_claim_rejects_unallowlisted_verify(self) -> None:
        task = self.task(
            'Data shape: {"state":"idle"}\n'
            "Verify: bash -c 'echo pass'\n"
        )
        with self.assertRaises(SystemExit):
            self.claim(task)

    def test_ui_check_commands_are_allowlisted(self) -> None:
        for argv in (
            ["make", "check"],
            ["make", "ui-smoke"],
            ["make", "ui-test"],
            ["npm", "run", "smoke"],
            ["npm", "run", "ui-smoke"],
            ["npm", "run", "test:ui"],
        ):
            self.assertTrue(tasks.allowed_command(argv), argv)
        for argv in (
            ["make", "deploy"],
            ["make", "ui-smoke", "destroy"],
            ["npm", "run", "deploy"],
        ):
            self.assertFalse(tasks.allowed_command(argv), argv)

    def test_review_status_gate_consumes_the_artifact(self) -> None:
        task = self.task(
            'Data shape: {"state":"idle"}\n'
            "Verify: python3 -m unittest tests.test_tasks -v\n"
        )
        self.claim(task)
        with self.assertRaises(SystemExit):
            tasks.set_status(self.root, task["meta"]["id"], "review", repo=self.repo)
        path = tasks.review_path(self.root, task["meta"]["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "task": task["meta"]["id"],
                    "head": tasks.git_head(self.repo),
                    "diff_sha256": tasks.review_diff(self.repo),
                    "contract_sha256": tasks.review_contract_digest(task),
                    "verdict": "PASS",
                    "checks": [
                        {
                            "command": "python3 -m unittest tests.test_tasks -v",
                            "exit": 0,
                        }
                    ],
                }
            )
        )
        self.assertEqual(
            tasks.set_status(
                self.root, task["meta"]["id"], "review", repo=self.repo
            )["meta"]["status"],
            "review",
        )


class ReviewArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.root = base / "state"
        (self.root / "work/tasks").mkdir(parents=True)
        self.repo = base / "repo"
        (self.repo / "tests").mkdir(parents=True)
        (self.repo / "tests/test_ok.py").write_text(
            "import unittest\n\n"
            "class Ok(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            "        self.assertTrue(True)\n"
        )
        (self.repo / "tests/test_goal_start.py").write_text(
            "import unittest\n\n"
            "class GoalStart(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            "        self.assertTrue(True)\n"
        )
        (self.repo / "tests/test_bad.py").write_text(
            "import unittest\n\n"
            "class Bad(unittest.TestCase):\n"
            "    def test_bad(self):\n"
            "        self.assertTrue(False)\n"
        )
        (self.repo / ".gitignore").write_text("__pycache__/\n*.pyc\n")
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "Test"], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "commit.gpgsign", "false"],
            check=True,
        )
        subprocess.run(["git", "-C", str(self.repo), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "-q", "-m", "base"],
            check=True,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def make_task(self, verify: str) -> dict:
        task = tasks.new_task(
            self.root,
            f"Review {verify}",
            project="demo",
            scope="Only the review artifact.",
            acceptance="- [x] review runs",
        )
        task["sections"]["Plan"] = (
            'Data shape: {"state":"idle|running"}\n'
            f"Verify: {verify}\n"
        )
        tasks.write_task(task)
        return task

    def artifact(self, task: dict) -> dict:
        path = self.root / "work/reviews" / f"{task['meta']['id']}.json"
        return json.loads(path.read_text())

    def test_pass_records_observed_exits_at_head(self) -> None:
        verify = "python3 -m unittest tests.test_ok -v"
        task = self.make_task(verify)
        result = tasks.review_task(
            self.root, task["meta"]["id"], repo=self.repo, runs=[verify]
        )
        self.assertEqual(result, 0)
        payload = self.artifact(task)
        self.assertEqual(payload["verdict"], "PASS")
        self.assertEqual(payload["head"], tasks.git_head(self.repo))
        self.assertEqual(payload["checks"], [{"command": verify, "exit": 0}])

    def test_changed_worktree_invalidates_pass(self) -> None:
        verify = "python3 -m unittest tests.test_ok -v"
        task = self.make_task(verify)
        task_id = task["meta"]["id"]
        self.assertEqual(
            tasks.review_task(
                self.root, task_id, repo=self.repo, runs=[verify]
            ),
            0,
        )
        untracked = self.repo / "new_file.txt"
        untracked.write_text("new\n")
        self.assertEqual(
            tasks.review_task(self.root, task_id, repo=self.repo), 1
        )
        untracked.unlink()
        self.assertEqual(
            tasks.review_task(self.root, task_id, repo=self.repo), 0
        )
        (self.repo / "tests/test_ok.py").write_text(
            "import unittest\n\n"
            "class Ok(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            "        self.assertTrue(True)\n\n"
        )
        self.assertEqual(
            tasks.review_task(self.root, task_id, repo=self.repo), 1
        )

    def test_contract_change_invalidates_pass(self) -> None:
        verify = "python3 -m unittest tests.test_ok -v"
        task = self.make_task(verify)
        task_id = task["meta"]["id"]
        self.assertEqual(
            tasks.review_task(
                self.root, task_id, repo=self.repo, runs=[verify]
            ),
            0,
        )
        stored = tasks.find_task(self.root, task_id)
        original_scope = stored["sections"]["Scope"]
        original_acceptance = stored["sections"]["Acceptance"]

        stored["sections"]["Acceptance"] = (
            original_acceptance + "\n- [x] a newly claimed outcome"
        )
        tasks.write_task(stored)
        self.assertEqual(
            tasks.review_task(self.root, task_id, repo=self.repo), 1
        )

        stored["sections"]["Acceptance"] = original_acceptance
        stored["sections"]["Scope"] = original_scope + " Also another surface."
        tasks.write_task(stored)
        self.assertEqual(
            tasks.review_task(self.root, task_id, repo=self.repo), 1
        )

        stored["sections"]["Scope"] = original_scope
        tasks.write_task(stored)
        self.assertEqual(
            tasks.review_task(self.root, task_id, repo=self.repo), 0
        )

    def test_second_verify_command_passes_only_when_it_ran(self) -> None:
        verify = "python3 -m unittest tests.test_goal_start -v"
        task = self.make_task(verify)
        with self.assertRaises(SystemExit):
            tasks.review_task(
                self.root,
                task["meta"]["id"],
                repo=self.repo,
                runs=["python3 -m unittest tests.test_ok -v"],
            )
        self.assertEqual(
            tasks.review_task(
                self.root,
                task["meta"]["id"],
                repo=self.repo,
                runs=[verify, "python3 -m unittest tests.test_ok -v"],
            ),
            0,
        )

    def test_nonzero_exit_blocks(self) -> None:
        verify = "python3 -m unittest tests.test_bad -v"
        task = self.make_task(verify)
        result = tasks.review_task(
            self.root, task["meta"]["id"], repo=self.repo, runs=[verify]
        )
        self.assertEqual(result, 1)
        payload = self.artifact(task)
        self.assertEqual(payload["verdict"], "UNVERIFIED")
        self.assertEqual(payload["checks"][0]["exit"], 1)

    def test_unknown_command_is_rejected_before_execution(self) -> None:
        marker = Path(self.tmp.name) / "marker"
        command = f"bash -c 'touch {marker}'"
        task = self.make_task(command)
        with self.assertRaises(SystemExit):
            tasks.review_task(
                self.root, task["meta"]["id"], repo=self.repo, runs=[command]
            )
        self.assertFalse(marker.exists())
        self.assertFalse((self.root / "work/reviews").exists())

    def test_path_outside_repository_is_rejected(self) -> None:
        outside = Path(self.tmp.name) / "outside_test.py"
        outside.write_text("raise SystemExit(0)\n")
        verify = f"python3 -m unittest {outside}"
        task = self.make_task(verify)
        with self.assertRaises(SystemExit):
            tasks.review_task(
                self.root, task["meta"]["id"], repo=self.repo, runs=[verify]
            )

    def test_missing_empty_stale_and_failed_artifacts_block(self) -> None:
        verify = "python3 -m unittest tests.test_ok -v"
        task = self.make_task(verify)
        task_id = task["meta"]["id"]
        self.assertEqual(
            tasks.review_task(self.root, task_id, repo=self.repo), 1
        )
        self.assertEqual(
            tasks.review_task(
                self.root, task_id, repo=self.repo, runs=[verify]
            ),
            0,
        )
        path = self.root / "work/reviews" / f"{task_id}.json"

        path.write_text(
            json.dumps(
                {
                    "task": task_id,
                    "head": tasks.git_head(self.repo),
                    "diff_sha256": tasks.review_diff(self.repo),
                    "contract_sha256": tasks.review_contract_digest(task),
                    "verdict": "PASS",
                    "checks": [],
                }
            )
        )
        self.assertEqual(
            tasks.review_task(self.root, task_id, repo=self.repo), 1
        )

        path.write_text(
            json.dumps(
                {
                    "task": task_id,
                    "head": tasks.git_head(self.repo),
                    "diff_sha256": tasks.review_diff(self.repo),
                    "contract_sha256": tasks.review_contract_digest(task),
                    "verdict": "PASS",
                    "checks": [{"command": verify, "exit": 1}],
                }
            )
        )
        self.assertEqual(
            tasks.review_task(self.root, task_id, repo=self.repo), 1
        )

        path.write_text(
            json.dumps(
                {
                    "task": task_id,
                    "head": tasks.git_head(self.repo),
                    "diff_sha256": tasks.review_diff(self.repo),
                    "contract_sha256": tasks.review_contract_digest(task),
                    "verdict": "PASS",
                    "checks": [
                        {
                            "command": "node tests/harness-ratchets.test.mjs",
                            "exit": 0,
                        }
                    ],
                }
            )
        )
        self.assertEqual(
            tasks.review_task(self.root, task_id, repo=self.repo), 1
        )

        self.assertEqual(
            tasks.review_task(
                self.root, task_id, repo=self.repo, runs=[verify]
            ),
            0,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "-q", "--allow-empty", "-m", "next"],
            check=True,
        )
        self.assertEqual(
            tasks.review_task(self.root, task_id, repo=self.repo), 1
        )

    def test_unverify_downgrades_and_blocks(self) -> None:
        verify = "python3 -m unittest tests.test_ok -v"
        task = self.make_task(verify)
        self.assertEqual(
            tasks.review_task(
                self.root, task["meta"]["id"], repo=self.repo, runs=[verify]
            ),
            0,
        )
        self.assertEqual(
            tasks.review_task(
                self.root,
                task["meta"]["id"],
                repo=self.repo,
                unverify=True,
            ),
            1,
        )
        self.assertEqual(self.artifact(task)["verdict"], "UNVERIFIED")

    def test_cli_records_and_validates(self) -> None:
        verify = "python3 -m unittest tests.test_ok -v"
        task = self.make_task(verify)
        command = [
            sys.executable,
            str(Path(tasks.__file__)),
            "--root",
            str(self.root),
            "review",
            task["meta"]["id"],
            "--repo",
            str(self.repo),
            "--run",
            verify,
        ]
        recorded = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(recorded.returncode, 0, recorded.stdout + recorded.stderr)
        validated = subprocess.run(
            command[:-2], text=True, capture_output=True
        )
        self.assertEqual(validated.returncode, 0, validated.stdout + validated.stderr)


if __name__ == "__main__":
    unittest.main()
