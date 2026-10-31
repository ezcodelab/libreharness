# SPDX-License-Identifier: MIT
import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("coding", ROOT / "bench/coding.py")
coding = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(coding)


def event(tool, **tool_input):
    return json.dumps(
        {
            "type": "tool_use",
            "part": {"tool": tool, "state": {"input": tool_input}},
        }
    )


class CodingBenchTests(unittest.TestCase):
    def _log(self, root: Path, lines: list[str]) -> Path:
        path = root / "opencode.txt"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_test_first_parser_detects_test_before_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self._log(
                Path(temp),
                [
                    event("write", filePath="tests/test_feature.py", content="..."),
                    event("write", filePath="src/feature.py", content="..."),
                ],
            )
            result = coding.test_first_from_log(path)
        self.assertEqual(result["test_first"], "1")
        self.assertEqual(result["test_files_changed"], 1)
        self.assertEqual(result["source_files_changed"], 1)

    def test_test_first_parser_detects_source_before_test(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self._log(
                Path(temp),
                [
                    event("write", filePath="src/feature.py", content="..."),
                    event("write", filePath="tests/test_feature.py", content="..."),
                ],
            )
            result = coding.test_first_from_log(path)
        self.assertEqual(result["test_first"], "0")

    def test_test_first_parser_reads_patch_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self._log(
                Path(temp),
                [
                    event(
                        "patch",
                        patchText="*** Add File: tests/test_api.py\n+def test_api():\n+    pass\n",
                    ),
                    event(
                        "patch",
                        patchText="*** Update File: app/api.py\n@@\n+pass\n",
                    ),
                ],
            )
            result = coding.test_first_from_log(path)
        self.assertEqual(result["test_first"], "1")
        self.assertEqual(result["test_files_changed"], 1)

    def test_test_first_parser_returns_unknown_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = self._log(Path(temp), [json.dumps({"type": "text"})])
            result = coding.test_first_from_log(path)
        self.assertEqual(result["test_first"], "unknown")
        self.assertEqual(result["test_files_changed"], 0)

    def test_dry_run_writes_manifest_and_calls_no_model(self) -> None:
        out = Path("bench/results/test-coding-dry")
        shutil.rmtree(out, ignore_errors=True)
        try:
            with patch.object(coding.subprocess, "run") as run:
                code = coding.main(["--dry-run", "--out", str(out)])
            self.assertEqual(code, 0)
            run.assert_not_called()
            data = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(out, ignore_errors=True)
        self.assertEqual(data["status"], "dry-run")
        self.assertEqual(data["suite"], "terminal-bench-coding-pilot")
        self.assertEqual(len(data["tasks"]), 3)
        self.assertEqual(len(data["arms"]), 5)
        self.assertIn("plain", [arm["name"] for arm in data["arms"]])
        self.assertEqual(len(data["run_order"]), 5)

    def test_run_arm_uses_repo_pythonpath_and_absolute_jobs_dir(self) -> None:
        out = Path("bench/results/test-coding-run").resolve()
        shutil.rmtree(out, ignore_errors=True)
        suite = coding.load_suite(ROOT / "bench/coding-suite.json")
        task = suite["tasks"][0]
        trial_dir = out / "plain-r1" / "job" / f"{task}__abc"
        trial_dir.mkdir(parents=True)
        (trial_dir / "result.json").write_text(
            json.dumps(
                {
                    "task_name": task,
                    "verifier_result": {"rewards": {"reward": 1.0}},
                    "agent_result": {
                        "cost_usd": 0.01,
                        "n_input_tokens": 10,
                        "n_output_tokens": 5,
                        "n_cache_tokens": 0,
                    },
                    "agent_execution": {
                        "started_at": "2026-10-31T00:00:00Z",
                        "finished_at": "2026-10-31T00:00:10Z",
                    },
                }
            ),
            encoding="utf-8",
        )
        captured = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            captured["env"] = kwargs["env"]
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        try:
            with patch.object(coding.subprocess, "run", side_effect=fake_run):
                rows = coding.run_arm(
                    suite=suite,
                    arm={"name": "plain", "agent": "opencode"},
                    model="test/model",
                    repetition=1,
                    sequence=1,
                    out=out,
                    timeout=10,
                    n_concurrent=1,
                )
        finally:
            shutil.rmtree(out, ignore_errors=True)
        self.assertIn(str(coding.ROOT.parent), captured["env"]["PYTHONPATH"])
        jobs_index = captured["command"].index("-o")
        self.assertTrue(Path(captured["command"][jobs_index + 1]).is_absolute())
        self.assertEqual(next(row for row in rows if row["task"] == task)["reward"], 1.0)

    def test_planned_order_is_seeded(self) -> None:
        arms = [
            {"name": "plain", "agent": "opencode"},
            {"name": "current", "agent": "adapter"},
            {"name": "egm", "agent": "adapter"},
            {"name": "superpowers", "agent": "adapter"},
            {"name": "both", "agent": "adapter"},
        ]
        first = coding.planned_order(arms, 2, 7)
        self.assertEqual(first, coding.planned_order(arms, 2, 7))
        self.assertEqual(len(first), 10)
        self.assertNotEqual(first, coding.planned_order(arms, 2, 8))


if __name__ == "__main__":
    unittest.main()
