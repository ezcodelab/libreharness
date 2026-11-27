# SPDX-License-Identifier: MIT
from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

import check_wait


def run(
    status: str,
    conclusion: str | None,
    completed_at: str | None = "2026-11-25T00:00:00Z",
) -> dict:
    return {
        "status": status,
        "conclusion": conclusion,
        "completed_at": completed_at,
        "started_at": "2026-11-25T00:00:00Z",
    }


class Clock:
    def __init__(self) -> None:
        self.now = 0

    def __call__(self) -> int:
        return self.now

    def sleep(self, seconds: int) -> None:
        self.now += seconds


class CheckWaitTests(unittest.TestCase):
    def test_terminal_success_with_stale_status_is_accepted(self) -> None:
        state = check_wait.evaluate(
            ["links"],
            {"links": run("in_progress", "success")},
        )
        self.assertEqual(state["stale"], ["links=in_progress/success"])
        self.assertEqual(state["pending"], [])
        self.assertEqual(state["failed"], [])

    def test_check_runs_uses_the_api_and_keeps_the_latest_run(self) -> None:
        payload = {
            "check_runs": [
                {
                    "name": "links",
                    "status": "in_progress",
                    "conclusion": None,
                    "completed_at": None,
                    "started_at": "2026-11-25T00:00:00Z",
                },
                {
                    "name": "links",
                    "status": "completed",
                    "conclusion": "success",
                    "completed_at": "2026-11-25T00:01:00Z",
                    "started_at": "2026-11-25T00:00:30Z",
                },
            ]
        }
        with mock.patch.object(check_wait, "gh_json", return_value=payload) as gh:
            runs = check_wait.check_runs("owner/repo", "a" * 40, repo_path=Path("/tmp"))
        gh.assert_called_once_with(
            ["api", f"repos/owner/repo/commits/{'a' * 40}/check-runs?per_page=100"],
            repo_path=Path("/tmp"),
        )
        self.assertEqual(runs["links"]["status"], "completed")

    def test_failure_missing_and_pending_are_distinct(self) -> None:
        state = check_wait.evaluate(
            ["failed", "missing", "pending"],
            {
                "failed": run("completed", "failure"),
                "pending": run("in_progress", None, None),
            },
        )
        self.assertEqual(state["failed"], ["failed=completed/failure"])
        self.assertEqual(state["missing"], ["missing"])
        self.assertEqual(state["pending"], ["pending=in_progress/pending"])

    def test_wait_returns_when_all_success_checks_are_terminal(self) -> None:
        clock = Clock()
        required = ["test", "links"]
        runs = {
            "test": run("completed", "success"),
            "links": run("in_progress", "success"),
        }
        stale = check_wait.wait_for_checks(
            repo="owner/repo",
            pr="1",
            head="a" * 40,
            required_fn=lambda: required,
            runs_fn=lambda: runs,
            clock=clock,
            sleep=clock.sleep,
            log=lambda _line: None,
        )
        self.assertEqual(stale, ["links=in_progress/success"])
        self.assertEqual(clock.now, 0)

    def test_wait_fails_immediately_on_a_failed_required_check(self) -> None:
        clock = Clock()
        with self.assertRaisesRegex(
            check_wait.CheckWaitError, "required checks failed: test=completed/failure"
        ):
            check_wait.wait_for_checks(
                repo="owner/repo",
                pr="1",
                head="a" * 40,
                required_fn=lambda: ["test"],
                runs_fn=lambda: {"test": run("completed", "failure")},
                clock=clock,
                sleep=clock.sleep,
                log=lambda _line: None,
            )
        self.assertEqual(clock.now, 0)

    def test_wait_times_out_with_the_stalled_check_names(self) -> None:
        clock = Clock()
        with self.assertRaisesRegex(
            check_wait.CheckWaitError,
            r"still pending after 5s: links=in_progress/pending",
        ):
            check_wait.wait_for_checks(
                repo="owner/repo",
                pr="1",
                head="a" * 40,
                timeout=5,
                interval=1,
                required_fn=lambda: ["links"],
                runs_fn=lambda: {"links": run("in_progress", None, None)},
                clock=clock,
                sleep=clock.sleep,
                log=lambda _line: None,
            )

    def test_wait_fails_when_no_required_checks_register(self) -> None:
        clock = Clock()
        with self.assertRaisesRegex(
            check_wait.CheckWaitError, "no required checks were reported"
        ):
            check_wait.wait_for_checks(
                repo="owner/repo",
                pr="1",
                head="a" * 40,
                timeout=10,
                interval=1,
                no_check_grace=2,
                required_fn=lambda: [],
                runs_fn=lambda: {},
                clock=clock,
                sleep=clock.sleep,
                log=lambda _line: None,
            )


if __name__ == "__main__":
    unittest.main()
