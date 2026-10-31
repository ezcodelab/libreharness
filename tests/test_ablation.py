# SPDX-License-Identifier: MIT
import contextlib
import csv
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ablation", ROOT / "bench/ablation.py")
ablation = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ablation)


class AblationTests(unittest.TestCase):
    def test_score_findings_counts_true_and_false_positives(self) -> None:
        defects = ablation.load_defects(ROOT / "bench/fixtures/ablation/defects.json")
        sample = json.loads(
            (ROOT / "bench/fixtures/ablation/sample-findings.json").read_text(
                encoding="utf-8"
            )
        )
        scored = ablation.score_findings(sample["findings"], defects)
        self.assertEqual(scored["true_positives"], 3)
        self.assertEqual(scored["false_positives"], 1)
        self.assertEqual(scored["false_blockers"], 0)
        self.assertEqual(scored["false_majors"], 0)
        self.assertEqual(scored["false_nits"], 1)
        self.assertEqual(scored["recall"], 0.6)
        self.assertEqual(scored["precision"], 0.75)
        self.assertEqual(scored["missed"], ["D4", "D5"])
        self.assertEqual(scored["recall_by_severity"]["blocker"], 2 / 3)
        self.assertEqual(scored["recall_by_severity"]["major"], 1 / 2)

    def test_score_findings_counts_false_positives_by_severity(self) -> None:
        defects = ablation.load_defects(ROOT / "bench/fixtures/ablation/defects.json")
        findings = [
            {"severity": "blocker", "issue": "unrelated blocker"},
            {"severity": "major", "issue": "unrelated major"},
            {"severity": "nit", "issue": "unrelated nit"},
        ]
        scored = ablation.score_findings(findings, defects)
        self.assertEqual(scored["false_blockers"], 1)
        self.assertEqual(scored["false_majors"], 1)
        self.assertEqual(scored["false_nits"], 1)
        self.assertEqual(scored["false_unknown"], 0)

    def test_fixture_b_rejects_praise_and_unrelated_logging(self) -> None:
        defects = ablation.load_defects(
            ROOT / "bench/fixtures/ablation/defects-b.json"
        )
        cases = [
            (
                {"severity": "blocker", "issue": "The audit event is not logged."},
                False,
                "B2",
            ),
            (
                {"severity": "blocker", "issue": "The rotation is idempotent."},
                False,
                "B5",
            ),
            (
                {
                    "severity": "major",
                    "issue": "The new key is returned in a query parameter.",
                },
                True,
                "B2",
            ),
            (
                {
                    "severity": "major",
                    "issue": "The old key is revoked immediately with no grace period.",
                },
                True,
                "B3",
            ),
        ]
        for finding, expected, defect_id in cases:
            with self.subTest(defect=defect_id, finding=finding["issue"]):
                scored = ablation.score_findings([finding], defects)
                self.assertEqual(defect_id in scored["matched"], expected)

    def test_duplicate_findings_do_not_lower_precision(self) -> None:
        defects = ablation.load_defects(ROOT / "bench/fixtures/ablation/defects.json")
        findings = [
            {"issue": "RLS and tenant scope are undefined"},
            {"issue": "RLS is still undefined"},
        ]
        scored = ablation.score_findings(findings, defects)
        self.assertEqual(scored["true_positives"], 1)
        self.assertEqual(scored["duplicates"], 1)
        self.assertEqual(scored["false_positives"], 0)
        self.assertEqual(scored["precision"], 1.0)

    def test_extract_findings_accepts_fenced_and_bare_arrays(self) -> None:
        fenced = 'Here is the result:\n```json\n[{"issue": "x"}]\n```\n'
        self.assertEqual(ablation.extract_findings(fenced), [{"issue": "x"}])
        bare = 'Result: [{"issue": "y"}]'
        self.assertEqual(ablation.extract_findings(bare), [{"issue": "y"}])
        self.assertEqual(ablation.extract_findings("not json"), [])
        self.assertTrue(ablation.has_json_answer("[]"))
        self.assertTrue(ablation.has_json_answer('{"findings": []}'))
        self.assertFalse(ablation.has_json_answer("not json"))

    def test_extract_findings_reads_the_assistant_text_event(self) -> None:
        event = {
            "type": "text",
            "part": {"text": '```json\n[{"issue": "from the event"}]\n```'},
        }
        self.assertEqual(
            ablation.extract_findings(json.dumps(event)),
            [{"issue": "from the event"}],
        )

    def test_d4_does_not_match_a_praise_of_object_idempotency(self) -> None:
        defects = ablation.load_defects(ROOT / "bench/fixtures/ablation/defects.json")
        scored = ablation.score_findings(
            [{"issue": "The worker is idempotent at the object level."}],
            defects,
        )
        self.assertEqual(scored["true_positives"], 0)
        self.assertEqual(scored["false_positives"], 1)

    def test_extract_usage_sums_step_finish_events(self) -> None:
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "type": "step_finish",
                        "part": {
                            "tokens": {
                                "input": 100,
                                "output": 20,
                                "reasoning": 5,
                                "cache": {"read": 900, "write": 10},
                            },
                            "cost": 0.001,
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "step_finish",
                        "part": {
                            "tokens": {"input": 50, "output": 5, "cache": {"read": 0}},
                            "cost": 0.0005,
                        },
                    }
                ),
                "not json",
            ]
        )
        usage = ablation.extract_usage(stdout)
        self.assertEqual(usage["input_tokens"], 150)
        self.assertEqual(usage["output_tokens"], 30)
        self.assertEqual(usage["reasoning_tokens"], 5)
        self.assertEqual(usage["cache_read_tokens"], 900)
        self.assertAlmostEqual(usage["cost_usd"], 0.0015)

    def test_dry_run_writes_a_manifest_and_calls_no_model(self) -> None:
        out = Path("bench/results/test-ablation-dry-run")
        shutil.rmtree(out, ignore_errors=True)
        try:
            with patch.object(ablation.subprocess, "run") as run:
                code = ablation.main(["--dry-run", "--out", str(out)])
            self.assertEqual(code, 0)
            run.assert_not_called()
            data = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(out, ignore_errors=True)
        self.assertEqual(data["status"], "dry-run")
        self.assertEqual(data["defect_count"], 5)
        self.assertEqual([arm["name"] for arm in data["arms"]], ["baseline", "candidate"])
        self.assertEqual(len(data["fixture_sha256"]), 64)
        self.assertNotEqual(data["arms"][0]["prompt_sha256"], data["arms"][1]["prompt_sha256"])

    def test_dry_run_accepts_four_named_arms(self) -> None:
        out = Path("bench/results/test-ablation-four-arms")
        shutil.rmtree(out, ignore_errors=True)
        try:
            with tempfile.TemporaryDirectory() as temp:
                arm_paths = {}
                for name in ("egm", "superpowers", "both"):
                    path = Path(temp) / f"{name}.json"
                    path.write_text(
                        json.dumps(
                            {
                                "feature": name,
                                "label": name,
                                "prompt": f"Review as {name}.",
                            }
                        ),
                        encoding="utf-8",
                    )
                    arm_paths[name] = path
                with patch.object(ablation.subprocess, "run") as run:
                    code = ablation.main(
                        [
                            "--dry-run",
                            "--out",
                            str(out),
                            "--arm",
                            f"current={ROOT / 'bench/features/ablation/baseline.json'}",
                            "--arm",
                            f"egm={arm_paths['egm']}",
                            "--arm",
                            f"superpowers={arm_paths['superpowers']}",
                            "--arm",
                            f"both={arm_paths['both']}",
                        ]
                    )
                self.assertEqual(code, 0)
                run.assert_not_called()
                data = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(out, ignore_errors=True)
        self.assertEqual(
            [arm["name"] for arm in data["arms"]],
            ["current", "egm", "superpowers", "both"],
        )
        self.assertEqual(data["seed"], 0)
        self.assertEqual(len(data["run_order"]), 4)

    def test_planned_order_is_seeded_and_deterministic(self) -> None:
        arms = [
            ("current", Path("a.json"), {}),
            ("egm", Path("b.json"), {}),
            ("superpowers", Path("c.json"), {}),
            ("both", Path("d.json"), {}),
        ]
        first = ablation.planned_order(arms, 2, 7)
        second = ablation.planned_order(arms, 2, 7)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 8)
        self.assertEqual(set(first), {(name, rep) for name, *_ in arms for rep in (1, 2)})
        self.assertNotEqual(first, ablation.planned_order(arms, 2, 8))

    def test_summary_includes_per_run_and_spread(self) -> None:
        def row(arm, rep, sequence, recall, precision):
            return {
                "arm": arm,
                "feature": arm,
                "label": arm,
                "model": "test/model",
                "repetition": rep,
                "sequence": sequence,
                "findings": 1,
                "true_positives": 1,
                "false_positives": 0,
                "false_blockers": 0,
                "false_majors": 0,
                "false_nits": 0,
                "duplicates": 0,
                "recall": str(recall),
                "precision": str(precision),
                "input_tokens": 10,
                "output_tokens": 5,
                "reasoning_tokens": 0,
                "cache_read_tokens": 0,
                "cost_usd": "0.0001",
                "wall_seconds": "1.0" if rep == 1 else "2.0",
                "error": "",
            }

        rows = [
            row("a", 1, 2, 0.5, 1.0),
            row("a", 2, 1, 1.0, 1.0),
        ]
        failed = row("a", 3, 3, 0.0, 0.0)
        failed["error"] = "timeout"
        rows.append(failed)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            ablation.print_summary(rows)
        output = buffer.getvalue()
        self.assertIn("Per-run results", output)
        self.assertIn("Spread (min-max)", output)
        self.assertIn("| a | 1 | 2 | 50% |", output)
        self.assertIn("| a | a | 3 | 1 | 75% |", output)
        self.assertIn("| a | 3 | 3 | 0% |", output)

    def test_duplicate_arm_name_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            ablation.main(
                [
                    "--dry-run",
                    "--arm",
                    "same=bench/features/ablation/baseline.json",
                    "--arm",
                    "same=bench/features/ablation/comprehension.json",
                ]
            )

    def test_missing_arm_file_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            ablation.main(["--dry-run", "--arm", "missing=/no/such/feature.json"])

    def test_directory_arm_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(SystemExit):
                ablation.main(["--dry-run", "--arm", f"dir={temp}"])

    def test_rescore_rebuilds_metrics_without_a_model(self) -> None:
        out = Path("bench/results/test-ablation-rescore")
        shutil.rmtree(out, ignore_errors=True)
        run_dir = out / "runs" / "a-r1"
        run_dir.mkdir(parents=True)
        findings = [
            {"severity": "blocker", "issue": "RLS and tenant scope are undefined."},
            {
                "severity": "major",
                "issue": "The create endpoint is GET /exports while polling is POST /exports/{id}.",
            },
            {
                "severity": "blocker",
                "issue": "The migration adds NOT NULL without a backfill or rollback.",
            },
            {"severity": "nit", "issue": "An unrelated style note."},
        ]
        (run_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
        defects = ablation.load_defects(ROOT / "bench/fixtures/ablation/defects.json")
        row = ablation.arm_row(
            arm="a",
            feature={"feature": "a", "label": "a"},
            model="test/model",
            repetition=1,
            findings=[],
            usage={
                "input_tokens": 10,
                "output_tokens": 5,
                "reasoning_tokens": 0,
                "cache_read_tokens": 0,
                "cost_usd": 0.0001,
            },
            wall_seconds=1.0,
            defects=defects,
        )
        try:
            with (out / "runs.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
                writer.writeheader()
                writer.writerow(row)
            with patch.object(ablation.subprocess, "run") as run:
                code = ablation.main(["--rescore", "--out", str(out)])
            self.assertEqual(code, 0)
            run.assert_not_called()
            rescored = list(
                csv.DictReader(
                    (out / "runs-rescored.csv").open(newline="", encoding="utf-8")
                )
            )
        finally:
            shutil.rmtree(out, ignore_errors=True)
        self.assertEqual(rescored[0]["false_blockers"], "0")
        self.assertEqual(rescored[0]["false_nits"], "1")
        self.assertEqual(rescored[0]["recall"], "0.600")

    def test_self_check_passes_and_rejects_a_bad_expectation(self) -> None:
        self.assertEqual(ablation.main(["--self-check"]), 0)
        sample = json.loads(
            (ROOT / "bench/fixtures/ablation/sample-findings.json").read_text(
                encoding="utf-8"
            )
        )
        sample["expected"]["recall"] = 0.99
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text(json.dumps(sample), encoding="utf-8")
            self.assertEqual(
                ablation.main(["--self-check", "--findings", str(path)]),
                1,
            )

    def test_successful_run_without_json_is_an_error(self) -> None:
        out = Path("bench/results/test-ablation-no-json")
        shutil.rmtree(out, ignore_errors=True)
        prose = SimpleNamespace(returncode=0, stdout="The design looks fine.", stderr="")
        try:
            with patch.object(ablation.subprocess, "run", return_value=prose):
                code = ablation.main(
                    ["--live", "--model", "test/model", "--out", str(out)]
                )
            self.assertEqual(code, 1)
            rows = (out / "runs.csv").read_text(encoding="utf-8")
        finally:
            shutil.rmtree(out, ignore_errors=True)
        self.assertIn("no JSON findings", rows)

    def test_live_failure_is_recorded_and_exits_nonzero(self) -> None:
        out = Path("bench/results/test-ablation-live-error")
        shutil.rmtree(out, ignore_errors=True)
        failure = SimpleNamespace(returncode=1, stdout="", stderr="provider down")
        try:
            with patch.object(
                ablation.subprocess, "run", return_value=failure
            ) as run:
                code = ablation.main(
                    [
                        "--live",
                        "--model",
                        "test/model",
                        "--out",
                        str(out),
                    ]
                )
                call = run.call_args_list[0]
                env = call.kwargs["env"]
                command = call.args[0]
                cwd = call.kwargs["cwd"]
            self.assertEqual(code, 1)
            rows = (out / "runs.csv").read_text(encoding="utf-8")
            stderr = (out / "runs/baseline-r1/stderr.txt").read_text(encoding="utf-8")
        finally:
            shutil.rmtree(out, ignore_errors=True)
        self.assertIn("exit 1", rows)
        self.assertIn("provider down", stderr)
        self.assertIn("--standalone", command)
        self.assertIn("XDG_CONFIG_HOME", env)
        self.assertIn("XDG_STATE_HOME", env)
        self.assertNotEqual(env["XDG_CONFIG_HOME"], os.environ.get("XDG_CONFIG_HOME"))
        self.assertNotEqual(Path(cwd).resolve(), ROOT.resolve())
        self.assertTrue(Path(cwd).name.startswith("libreharness-ablation-"))


if __name__ == "__main__":
    unittest.main()
