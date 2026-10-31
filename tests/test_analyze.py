# SPDX-License-Identifier: MIT
import contextlib
import csv
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("analyze", ROOT / "bench/analyze.py")
analyze = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(analyze)


class AnalyzeTests(unittest.TestCase):
    def test_bootstrap_ci_is_degenerate_for_constant_values(self) -> None:
        self.assertEqual(analyze.bootstrap_ci([1.0, 1.0, 1.0], 100, 0), (1.0, 1.0))
        self.assertIsNone(analyze.bootstrap_ci([], 100, 0))

    def test_paired_diffs_use_per_task_means(self) -> None:
        rows = [
            {"arm": "plain", "task": "a", "reward": "1"},
            {"arm": "plain", "task": "a", "reward": "0"},
            {"arm": "current", "task": "a", "reward": "1"},
            {"arm": "current", "task": "a", "reward": "1"},
            {"arm": "plain", "task": "b", "reward": "0"},
            {"arm": "current", "task": "b", "reward": "0"},
        ]
        diffs = analyze.paired_diffs(rows, "plain", "current")
        self.assertEqual(len(diffs), 2)
        self.assertEqual(diffs[0][0], "a")
        self.assertAlmostEqual(diffs[0][3], 0.5)
        self.assertAlmostEqual(diffs[1][3], 0.0)

    def test_coding_report_prints_paired_interval(self) -> None:
        rows = [
            {"arm": "plain", "task": "a", "reward": "1", "test_first": "0"},
            {"arm": "current", "task": "a", "reward": "1", "test_first": "1"},
            {"arm": "plain", "task": "b", "reward": "0", "test_first": "unknown"},
            {"arm": "current", "task": "b", "reward": "1", "test_first": "1"},
        ]
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            analyze.coding_report(rows, "plain", "current", 100, 0)
        output = buffer.getvalue()
        self.assertIn("Paired by task", output)
        self.assertIn("95% bootstrap CI", output)
        self.assertIn("tasks: 2", output)

    def test_main_reads_coding_runs_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runs.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "arm",
                        "task",
                        "reward",
                        "exception",
                        "cost_usd",
                        "input_tokens",
                        "output_tokens",
                        "wall_seconds",
                        "test_first",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "arm": "plain",
                        "task": "a",
                        "reward": "1",
                        "exception": "",
                        "cost_usd": "0.01",
                        "input_tokens": "10",
                        "output_tokens": "5",
                        "wall_seconds": "1.0",
                        "test_first": "0",
                    }
                )
                writer.writerow(
                    {
                        "arm": "current",
                        "task": "a",
                        "reward": "1",
                        "exception": "",
                        "cost_usd": "0.01",
                        "input_tokens": "10",
                        "output_tokens": "5",
                        "wall_seconds": "1.0",
                        "test_first": "1",
                    }
                )
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = analyze.main(["--input", str(path)])
        self.assertEqual(code, 0)
        self.assertIn("Coding benchmark summary", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
