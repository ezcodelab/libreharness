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

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "pr_watch.py"
SHA = "a" * 40


class GiteaHandler(BaseHTTPRequestHandler):
    pr = {}
    status = {}
    merges = []
    merge_error = 200

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
            self.send_json(self.status)
        else:
            self.send_json({"message": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/v1/repos/o/r/pulls/1/merge":
            self.merges.append(body)
            if self.merge_error != 200:
                self.send_json({"message": "denied"}, self.merge_error)
                return
            self.send_json({})
        else:
            self.send_json({"message": "not found"}, 404)


class GiteaPRWatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.verifier = base / "verifier.txt"
        self.verifier.write_text(f"PASS {SHA}\n", encoding="utf-8")
        self.evidence = base / "evidence.txt"
        self.evidence.write_text("python3 -m unittest: OK\n", encoding="utf-8")
        GiteaHandler.merges = []
        GiteaHandler.merge_error = 200
        GiteaHandler.pr = {
            "state": "open",
            "merged": False,
            "mergeable": True,
            "base": {"ref": "main"},
            "head": {"sha": SHA},
        }
        GiteaHandler.status = {
            "state": "success",
            "statuses": [
                {"context": "CI / check (pull_request)", "status": "success"}
            ],
        }
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), GiteaHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.api = f"http://127.0.0.1:{self.server.server_port}/api/v1"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def run_watch(self, *extra, env_extra=None):
        env = os.environ.copy()
        env.update({"GITEA_URL": self.api, "GITEA_TOKEN": "test-token"})
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--forge",
                "gitea",
                "--repo",
                "o/r",
                "--pr",
                "1",
                "--verifier-pass",
                str(self.verifier),
                "--evidence",
                str(self.evidence),
                *extra,
            ],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def test_auto_schedules_when_checks_pending(self):
        GiteaHandler.status["statuses"][0]["status"] = "pending"
        result = self.run_watch("--auto")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("scheduled auto-merge", result.stdout)
        self.assertEqual(len(GiteaHandler.merges), 1)
        payload = GiteaHandler.merges[0]
        self.assertEqual(payload["do"], "squash")
        self.assertTrue(payload["merge_when_checks_succeed"])
        self.assertEqual(payload["head_commit_id"], SHA)

    def test_merge_requires_success(self):
        GiteaHandler.status["statuses"][0]["status"] = "pending"
        result = self.run_watch("--merge")
        self.assertEqual(result.returncode, 2)
        self.assertIn("check CI / check (pull_request): pending", result.stderr)
        self.assertEqual(GiteaHandler.merges, [])

    def test_merge_success(self):
        result = self.run_watch("--merge")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(GiteaHandler.merges), 1)
        self.assertFalse(GiteaHandler.merges[0]["merge_when_checks_succeed"])

    def test_failure_blocks_auto(self):
        GiteaHandler.status["statuses"][0]["status"] = "failure"
        result = self.run_watch("--auto")
        self.assertEqual(result.returncode, 2)
        self.assertIn("check CI / check (pull_request): failure", result.stderr)
        self.assertEqual(GiteaHandler.merges, [])

    def test_skipped_blocks(self):
        GiteaHandler.status["statuses"][0]["status"] = "skipped"
        result = self.run_watch("--auto")
        self.assertEqual(result.returncode, 2)
        self.assertIn("skipped", result.stderr)

    def test_skipped_non_required_context_is_ignored(self):
        GiteaHandler.status["statuses"].append(
            {"context": "CI / test (github) (pull_request)", "status": "skipped"}
        )
        result = self.run_watch(
            "--auto", "--required-check", "CI / check (pull_request)"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(GiteaHandler.merges), 1)

    def test_missing_status_blocks(self):
        GiteaHandler.status = {"state": "pending", "statuses": []}
        result = self.run_watch("--auto")
        self.assertEqual(result.returncode, 2)
        self.assertIn("no status checks", result.stderr)

    def test_required_context_must_match(self):
        result = self.run_watch("--auto", "--required-check", "other")
        self.assertEqual(result.returncode, 2)
        self.assertIn("required check missing: other", result.stderr)

    def test_stale_verifier_sha_blocks(self):
        self.verifier.write_text("PASS " + "b" * 40 + "\n", encoding="utf-8")
        result = self.run_watch("--auto")
        self.assertEqual(result.returncode, 2)
        self.assertIn("does not match PR head", result.stderr)

    def test_auto_required_pending_check_schedules(self):
        GiteaHandler.status["statuses"][0]["status"] = "pending"
        result = self.run_watch(
            "--auto", "--required-check", "CI / check (pull_request)"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(GiteaHandler.merges), 1)
        self.assertTrue(GiteaHandler.merges[0]["merge_when_checks_succeed"])

    def test_missing_gitea_url_blocks(self):
        result = self.run_watch("--auto", env_extra={"GITEA_URL": ""})
        self.assertEqual(result.returncode, 3)
        self.assertIn("GITEA_URL is not set", result.stderr)

    def test_token_not_in_merge_error(self):
        GiteaHandler.merge_error = 403
        result = self.run_watch("--merge")
        self.assertEqual(result.returncode, 3)
        self.assertNotIn("test-token", result.stdout + result.stderr)

    def test_missing_token_blocks(self):
        result = self.run_watch("--auto", env_extra={"GITEA_TOKEN": ""})
        self.assertEqual(result.returncode, 3)
        self.assertIn("GITEA_TOKEN is not set", result.stderr)


if __name__ == "__main__":
    unittest.main()
