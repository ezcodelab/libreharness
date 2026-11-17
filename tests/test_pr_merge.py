# SPDX-License-Identifier: MIT
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "pr_merge.py"
SHA = "a" * 40


class MergeHandler(BaseHTTPRequestHandler):
    pr = {}
    commit_status = {}
    merges = []
    merge_code = 200

    def log_message(self, *args):
        pass

    def send_json(self, payload, code=200):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/v1/repos/o/r/pulls/1":
            self.send_json(self.pr)
        elif self.path == f"/api/v1/repos/o/r/commits/{SHA}/status":
            self.send_json(self.commit_status)
        else:
            self.send_json({"message": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/v1/repos/o/r/pulls/1/merge":
            self.merges.append(body)
            if self.merge_code != 200:
                self.send_json({"message": "denied"}, self.merge_code)
                return
            self.send_json({})
        else:
            self.send_json({"message": "not found"}, 404)


class PRMergeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        MergeHandler.merges = []
        MergeHandler.merge_code = 200
        MergeHandler.pr = {
            "number": 1,
            "state": "open",
            "merged": False,
            "draft": False,
            "base": {"ref": "main"},
            "head": {"sha": SHA},
            "labels": [],
        }
        MergeHandler.commit_status = {
            "state": "success",
            "statuses": [
                {"context": "verifier / policy", "status": "success"}
            ],
        }
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), MergeHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.api = f"http://127.0.0.1:{self.server.server_port}/api/v1"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def run_merge(self, *extra, env_extra=None):
        env = os.environ.copy()
        env.update({"GITEA_URL": self.api, "GITEA_TOKEN": "test-token"})
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                "o/r",
                "--pr",
                "1",
                "--head",
                SHA,
                "--api",
                self.api,
                *extra,
            ],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def test_schedules_merge(self):
        result = self.run_merge()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(MergeHandler.merges), 1)
        payload = MergeHandler.merges[0]
        self.assertEqual(payload["do"], "merge")
        self.assertTrue(payload["merge_when_checks_succeed"])
        self.assertEqual(payload["head_commit_id"], SHA)
        self.assertFalse(payload["delete_branch_after_merge"])

    def test_missing_verifier_status_blocks(self):
        MergeHandler.commit_status = {"state": "pending", "statuses": []}
        result = self.run_merge()
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing required status", result.stderr)
        self.assertEqual(MergeHandler.merges, [])

    def test_custom_required_context(self):
        context = "admin/libreharness: auto-merge / verify (pull_request_target)"
        MergeHandler.commit_status = {
            "state": "success",
            "statuses": [{"context": context, "status": "success"}],
        }
        result = self.run_merge("--required-context", context)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(MergeHandler.merges), 1)

    def test_missing_custom_context_blocks(self):
        context = "admin/libreharness: auto-merge / verify (pull_request_target)"
        result = self.run_merge("--required-context", context)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing required status", result.stderr)

    def test_failed_verifier_status_blocks(self):
        MergeHandler.commit_status["statuses"][0]["status"] = "failure"
        result = self.run_merge()
        self.assertEqual(result.returncode, 1)
        self.assertIn("verifier / policy is failure", result.stderr)

    def test_draft_blocks(self):
        MergeHandler.pr["draft"] = True
        result = self.run_merge()
        self.assertEqual(result.returncode, 1)
        self.assertIn("draft", result.stderr)

    def test_wrong_base_blocks(self):
        MergeHandler.pr["base"]["ref"] = "release"
        result = self.run_merge()
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected main", result.stderr)

    def test_head_mismatch_blocks(self):
        MergeHandler.pr["head"]["sha"] = "b" * 40
        result = self.run_merge()
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected", result.stderr)

    def test_blocked_label_blocks(self):
        MergeHandler.pr["labels"] = [{"name": "do-not-merge"}]
        result = self.run_merge()
        self.assertEqual(result.returncode, 1)
        self.assertIn("blocked label", result.stderr)

    def test_already_merged_is_a_noop(self):
        MergeHandler.pr["merged"] = True
        result = self.run_merge()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already merged", result.stdout)
        self.assertEqual(MergeHandler.merges, [])

    def test_merge_error_blocks(self):
        MergeHandler.merge_code = 405
        result = self.run_merge()
        self.assertEqual(result.returncode, 1)
        self.assertIn("HTTP 405", result.stderr)

    def test_dry_run_does_not_post(self):
        result = self.run_merge("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("would merge", result.stdout)
        self.assertEqual(MergeHandler.merges, [])

    def test_token_not_printed(self):
        result = self.run_merge()
        self.assertNotIn("test-token", result.stdout + result.stderr)

    def test_missing_token_blocks(self):
        result = self.run_merge(env_extra={"GITEA_TOKEN": ""})
        self.assertEqual(result.returncode, 2)
        self.assertIn("GITEA_TOKEN is not set", result.stderr)


if __name__ == "__main__":
    unittest.main()
