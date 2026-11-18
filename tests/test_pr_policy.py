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
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "pr_policy.py"
SHA = "a" * 40


class PolicyHandler(BaseHTTPRequestHandler):
    pr = {}
    files = []
    diff = ""
    pr_error = False
    last_accept = ""

    def log_message(self, *args):
        pass

    def send_json(self, payload, code=200):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, payload):
        body = payload.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/v1"):
            path = path[len("/api/v1") :]
        if path == "/repos/o/r/pulls/1.diff":
            self.send_text(self.diff)
        elif path == "/repos/o/r/pulls/1":
            PolicyHandler.last_accept = self.headers.get("Accept", "")
            if "diff" in PolicyHandler.last_accept:
                self.send_text(self.diff)
            elif self.pr_error:
                self.send_json({"message": "not found"}, 404)
            else:
                self.send_json(self.pr)
        elif path == "/repos/o/r/pulls/1/files":
            self.send_json(self.files)
        else:
            self.send_json({"message": "not found"}, 404)


class PRPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.verifier = Path(self.tmp.name) / "verifier.txt"
        self.verifier.write_text(f"PASS {SHA}\n", encoding="utf-8")
        PolicyHandler.pr_error = False
        PolicyHandler.last_accept = ""
        PolicyHandler.pr = {
            "number": 1,
            "state": "open",
            "merged": False,
            "draft": False,
            "base": {"ref": "main"},
            "head": {"sha": SHA, "repo": {"full_name": "o/r"}},
            "labels": [],
            "additions": 5,
            "deletions": 2,
        }
        PolicyHandler.files = [
            {"filename": "docs/guide.md", "additions": 5, "deletions": 2}
        ]
        PolicyHandler.diff = (
            "diff --git a/docs/guide.md b/docs/guide.md\n"
            "+new line\n"
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), PolicyHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.root = f"http://127.0.0.1:{self.server.server_port}"
        self.api = f"{self.root}/api/v1"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def run_policy(self, *extra, forge="gitea", env_extra=None):
        child = os.environ.copy()
        if forge == "github":
            child.update(
                {"GITHUB_API_URL": self.root, "GITHUB_TOKEN": "test-token"}
            )
            child.pop("GITEA_URL", None)
            child.pop("GITEA_TOKEN", None)
            api = self.root
            forge_args = ["--forge", "github"]
        else:
            child.update({"GITEA_URL": self.api, "GITEA_TOKEN": "test-token"})
            child.pop("GITHUB_API_URL", None)
            child.pop("GITHUB_TOKEN", None)
            api = self.api
            forge_args = []
        if env_extra:
            child.update(env_extra)
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
                api,
                *forge_args,
                *extra,
            ],
            text=True,
            capture_output=True,
            env=child,
            check=False,
        )

    def test_pass(self):
        result = self.run_policy()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("pr_policy: PASS", result.stdout)

    def test_json_pass(self):
        result = self.run_policy("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"ok": true', result.stdout)

    def test_github_pass(self):
        result = self.run_policy(forge="github")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("pr_policy: PASS", result.stdout)

    def test_github_uses_diff_accept(self):
        result = self.run_policy(forge="github")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("vnd.github.v3.diff", PolicyHandler.last_accept)

    def test_github_blocked_label(self):
        PolicyHandler.pr["labels"] = [{"name": "do-not-merge"}]
        result = self.run_policy(forge="github")
        self.assertEqual(result.returncode, 1)
        self.assertIn("blocked label", result.stdout)

    def test_github_fork_allowed(self):
        PolicyHandler.pr["head"]["repo"]["full_name"] = "contributor/r"
        result = self.run_policy(forge="github")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_closed_blocks(self):
        PolicyHandler.pr["state"] = "closed"
        result = self.run_policy()
        self.assertEqual(result.returncode, 1)
        self.assertIn("not open", result.stdout)

    def test_draft_blocks(self):
        PolicyHandler.pr["draft"] = True
        result = self.run_policy()
        self.assertEqual(result.returncode, 1)
        self.assertIn("draft", result.stdout)

    def test_wrong_base_blocks(self):
        PolicyHandler.pr["base"]["ref"] = "release"
        result = self.run_policy()
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected main", result.stdout)

    def test_head_mismatch_blocks(self):
        PolicyHandler.pr["head"]["sha"] = "b" * 40
        result = self.run_policy()
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected", result.stdout)

    def test_fork_blocks(self):
        PolicyHandler.pr["head"]["repo"]["full_name"] = "other/r"
        result = self.run_policy()
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected o/r", result.stdout)

    def test_blocked_label_blocks(self):
        PolicyHandler.pr["labels"] = [{"name": "do-not-merge"}]
        result = self.run_policy()
        self.assertEqual(result.returncode, 1)
        self.assertIn("blocked label", result.stdout)

    def test_large_diff_blocks(self):
        PolicyHandler.pr["additions"] = 3000
        result = self.run_policy()
        self.assertEqual(result.returncode, 1)
        self.assertIn("changed lines", result.stdout)

    def test_many_files_blocks(self):
        PolicyHandler.files = [
            {"filename": f"docs/{index}.md", "additions": 1, "deletions": 0}
            for index in range(51)
        ]
        result = self.run_policy()
        self.assertEqual(result.returncode, 1)
        self.assertIn("files", result.stdout)

    def test_protected_path_blocks(self):
        PolicyHandler.files = [
            {"filename": ".gitea/workflows/auto-merge.yml", "additions": 1, "deletions": 0}
        ]
        result = self.run_policy()
        self.assertEqual(result.returncode, 1)
        self.assertIn("protected path", result.stdout)

    def test_previous_protected_path_blocks(self):
        PolicyHandler.files = [
            {
                "filename": "docs/new.md",
                "previous_filename": ".gitea/workflows/auto-merge.yml",
                "additions": 1,
                "deletions": 0,
            }
        ]
        result = self.run_policy()
        self.assertEqual(result.returncode, 1)
        self.assertIn("protected path", result.stdout)

    def test_build_file_blocks(self):
        PolicyHandler.files = [
            {"filename": "package.json", "additions": 1, "deletions": 0}
        ]
        result = self.run_policy()
        self.assertEqual(result.returncode, 1)
        self.assertIn("protected path", result.stdout)

    def test_deploy_script_blocks(self):
        PolicyHandler.files = [
            {"filename": "scripts/deploy-gitea", "additions": 1, "deletions": 0}
        ]
        result = self.run_policy()
        self.assertEqual(result.returncode, 1)
        self.assertIn("protected path", result.stdout)

    def test_gate_policy_sources_block(self):
        for filename in (
            "bin/pr_policy.py",
            "bin/verify_pr.sh",
            "bin/pr_watch.py",
            "bin/sync_gitea_gate.py",
            "bin/tasks.py",
            "templates/gitea-auto-merge.yml",
        ):
            PolicyHandler.files = [
                {"filename": filename, "additions": 1, "deletions": 0}
            ]
            result = self.run_policy()
            self.assertEqual(result.returncode, 1, filename)
            self.assertIn("protected path", result.stdout)

    def test_private_marker_blocks(self):
        private = "/home/" + "cachyos" + "/Documents/" + "homelab"
        PolicyHandler.diff = (
            "diff --git a/docs/guide.md b/docs/guide.md\n"
            f"+host={private}\n"
        )
        result = self.run_policy()
        self.assertEqual(result.returncode, 1)
        self.assertIn("private marker", result.stdout)

    def test_private_marker_in_removed_line_allowed(self):
        private = "/home/" + "cachyos" + "/Documents/" + "homelab"
        PolicyHandler.diff = (
            "diff --git a/docs/guide.md b/docs/guide.md\n"
            f"-host={private}\n"
        )
        result = self.run_policy()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_forbidden_file_blocks(self):
        PolicyHandler.files = [
            {"filename": "deploy/id_rsa", "additions": 1, "deletions": 0}
        ]
        result = self.run_policy()
        self.assertEqual(result.returncode, 1)
        self.assertIn("forbidden file", result.stdout)

    def test_env_example_is_allowed(self):
        PolicyHandler.files = [
            {"filename": ".env.example", "additions": 1, "deletions": 0}
        ]
        result = self.run_policy()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_api_error_exits_2(self):
        PolicyHandler.pr_error = True
        result = self.run_policy()
        self.assertEqual(result.returncode, 2)
        self.assertIn("HTTP 404", result.stderr)


if __name__ == "__main__":
    unittest.main()
