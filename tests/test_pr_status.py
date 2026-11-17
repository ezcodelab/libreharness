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
SCRIPT = ROOT / "bin" / "pr_status.py"
SHA = "a" * 40


class StatusHandler(BaseHTTPRequestHandler):
    posts = []
    code = 201

    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path == f"/api/v1/repos/o/r/statuses/{SHA}":
            self.posts.append(body)
            self.send_response(self.code)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()


class PRStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        StatusHandler.posts = []
        StatusHandler.code = 201
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), StatusHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.api = f"http://127.0.0.1:{self.server.server_port}/api/v1"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def run_status(self, *extra, env_extra=None):
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
                "--head",
                SHA,
                "--state",
                "success",
                "--context",
                "verifier / policy",
                "--description",
                "checks passed",
                "--target-url",
                "https://example.invalid/run/1",
                "--api",
                self.api,
                *extra,
            ],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def test_publishes_status(self):
        result = self.run_status()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(StatusHandler.posts), 1)
        payload = StatusHandler.posts[0]
        self.assertEqual(payload["state"], "success")
        self.assertEqual(payload["context"], "verifier / policy")
        self.assertEqual(payload["description"], "checks passed")
        self.assertEqual(payload["target_url"], "https://example.invalid/run/1")

    def test_token_not_printed(self):
        result = self.run_status()
        self.assertNotIn("test-token", result.stdout + result.stderr)

    def test_missing_token_blocks(self):
        result = self.run_status(env_extra={"GITEA_TOKEN": ""})
        self.assertEqual(result.returncode, 2)
        self.assertIn("GITEA_TOKEN is not set", result.stderr)

    def test_http_error_blocks(self):
        StatusHandler.code = 403
        result = self.run_status()
        self.assertEqual(result.returncode, 2)
        self.assertIn("HTTP 403", result.stderr)


if __name__ == "__main__":
    unittest.main()
