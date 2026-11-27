# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import tasks
import usage_report


class UsageReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "state"
        (self.root / "work/tasks").mkdir(parents=True)
        (self.root / "metrics").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def task(self, title: str, status: str) -> dict:
        task = tasks.new_task(self.root, title, acceptance="- [x] verified")
        task["meta"]["status"] = status
        tasks.write_task(task)
        return task

    def verify(self, task: dict) -> None:
        path = tasks.review_path(self.root, task["meta"]["id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "task": task["meta"]["id"],
                    "head": "a" * 40,
                    "diff_sha256": "b" * 64,
                    "recorded_at": "2026-11-23T12:10:00+00:00",
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

    def write_jsonl(self, name: str, rows: list[dict]) -> None:
        (self.root / "metrics" / name).write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n"
        )

    def test_cost_per_verified_task_includes_failed_work(self) -> None:
        done = self.task("Verified", "done")
        self.verify(done)
        self.task("Failed", "abandoned")
        self.write_jsonl(
            "session-tasks.jsonl",
            [
                {
                    "observed_at": "2026-11-23T12:00:00+00:00",
                    "session": "s1",
                    "task": done["meta"]["id"],
                },
                {
                    "observed_at": "2026-11-23T12:30:00+00:00",
                    "session": "s2",
                    "task": "failed-task",
                },
            ],
        )
        self.write_jsonl(
            "usage-log.jsonl",
            [
                {
                    "observed_at": "2026-11-23T12:05:00+00:00",
                    "session": "s1",
                    "cost": 0.3,
                    "input": 100,
                    "output": 20,
                    "reasoning": 5,
                    "cache_read": 40,
                    "cache_write": 8,
                    "calls": 3,
                    "retries": 0,
                },
                {
                    "observed_at": "2026-11-23T12:35:00+00:00",
                    "session": "s2",
                    "cost": 0.1,
                    "input": 50,
                    "output": 10,
                    "reasoning": 2,
                    "cache_read": 20,
                    "cache_write": 4,
                    "calls": 2,
                    "retries": 1,
                },
            ],
        )
        result = usage_report.report_data(self.root)
        self.assertEqual(result["tasks_verified"], 1)
        self.assertEqual(result["tasks_measured"], 1)
        self.assertAlmostEqual(result["model_cost"], 0.4)
        self.assertAlmostEqual(result["attributed_cost"], 0.3)
        self.assertAlmostEqual(result["cost_per_verified_task"], 0.4)
        self.assertEqual(result["tokens"]["input"], 150)
        self.assertEqual(result["model_calls"], 5)
        self.assertEqual(result["retries"], 1)
        self.assertEqual(result["median_minutes_to_verify"], 10)

    def test_no_verified_tasks_has_no_cost_ratio(self) -> None:
        result = usage_report.report_data(self.root)
        self.assertEqual(result["tasks_verified"], 0)
        self.assertIsNone(result["cost_per_verified_task"])


if __name__ == "__main__":
    unittest.main()
