# SPDX-License-Identifier: MIT
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "check_mirror.py"
SHA_A = "a" * 40
SHA_B = "b" * 40


class MirrorHandler(BaseHTTPRequestHandler):
    github_sha = SHA_A
    gitea_sha = SHA_A
    github_date = ""
    github_error = False
    gitea_error = False
    github_failures_remaining = 0

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
        path = urlparse(self.path).path
        if path == "/repos/gh/repo/commits/main":
            if self.github_failures_remaining > 0:
                MirrorHandler.github_failures_remaining -= 1
                self.send_json({"message": "transient"}, 500)
            elif self.github_error:
                self.send_json({"message": "error"}, 500)
            else:
                self.send_json(
                    {
                        "sha": self.github_sha,
                        "commit": {"committer": {"date": self.github_date}},
                    }
                )
        elif path == "/api/v1/repos/gt/repo/branches/main":
            if self.gitea_error:
                self.send_json({"message": "error"}, 500)
            else:
                self.send_json({"commit": {"id": self.gitea_sha}})
        else:
            self.send_json({"message": "not found"}, 404)


class MirrorCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        MirrorHandler.github_sha = SHA_A
        MirrorHandler.gitea_sha = SHA_A
        MirrorHandler.github_date = datetime.now(timezone.utc).isoformat()
        MirrorHandler.github_error = False
        MirrorHandler.gitea_error = False
        MirrorHandler.github_failures_remaining = 0
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), MirrorHandler)
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.thread.start()
        self.root = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def run_check(self, *extra):
        child = os.environ.copy()
        child.pop("GITHUB_TOKEN", None)
        child.pop("GITEA_TOKEN", None)
        child.pop("GITEA_URL", None)
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--pair",
                "gh/repo=gt/repo",
                "--github-api",
                self.root,
                "--gitea-api",
                f"{self.root}/api/v1",
                "--max-age",
                "1200",
                *extra,
            ],
            text=True,
            capture_output=True,
            env=child,
            check=False,
        )

    def test_in_sync(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("mirror OK", result.stdout)

    def test_behind_recent_is_within_grace(self):
        MirrorHandler.github_sha = SHA_B
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("within 1200s grace", result.stdout)

    def test_behind_old_fails(self):
        MirrorHandler.github_sha = SHA_B
        MirrorHandler.github_date = (
            datetime.now(timezone.utc) - timedelta(seconds=1800)
        ).isoformat()
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("mirror FAIL", result.stdout)
        self.assertIn("limit 1200s", result.stdout)

    def test_github_error_exits_2(self):
        MirrorHandler.github_error = True
        result = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertIn("HTTP 500", result.stderr)

    def test_gitea_error_exits_2(self):
        MirrorHandler.gitea_error = True
        result = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertIn("HTTP 500", result.stderr)

    def test_json_output(self):
        result = self.run_check("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"ok": true', result.stdout)

    def test_retries_transient_github_error(self):
        MirrorHandler.github_failures_remaining = 1
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("mirror OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
