# SPDX-License-Identifier: MIT
import importlib.util
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
        self.assertEqual(scored["recall"], 0.6)
        self.assertEqual(scored["precision"], 0.75)
        self.assertEqual(scored["missed"], ["D4", "D5"])

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
