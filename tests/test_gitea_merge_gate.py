# SPDX-License-Identifier: MIT
import base64
import json
import os
import subprocess
import sys
import textwrap
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "gitea-auto-merge.yml"
HEAD = "a" * 40
OTHER = "b" * 40


def gate_script() -> str:
    text = TEMPLATE.read_text()
    marker = "python3 - <<'PY'\n"
    start = text.index(marker) + len(marker)
    end = text.index("\n          PY", start)
    return textwrap.dedent(text[start:end])


POLICY = {
    "protected_paths": ["Makefile", "deploy/"],
    "forbidden_files": [],
    "blocking_labels": ["blocked"],
    "merge_method": "merge",
}


class FakeGitea(BaseHTTPRequestHandler):
    pr = {}
    files = [{"filename": "docs/readme.md"}]
    files_page2 = []
    move_head_after_files = None
    policy = POLICY
    policy_status = 200
    merge_status = 200
    merge_calls = []
    polls = 0
    poll_then_mergeable = False

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
        if path == "/api/v1/repos/admin/demo/pulls/1":
            data = dict(self.pr)
            if self.poll_then_mergeable:
                self.__class__.polls += 1
                if self.polls == 1:
                    data["mergeable"] = None
                else:
                    data["mergeable"] = True
            self.send_json(data)
        elif path == "/api/v1/repos/admin/demo/pulls/1/files":
            page = int(
                parse_qs(urlparse(self.path).query).get("page", ["1"])[0]
            )
            self.send_json(self.files if page == 1 else self.files_page2)
            if self.move_head_after_files:
                self.__class__.pr["head"]["sha"] = self.move_head_after_files
                self.__class__.move_head_after_files = None
        elif path == "/api/v1/repos/admin/demo/contents/.github/merge-policy.json":
            if self.policy_status != 200:
                self.send_json({"message": "not found"}, self.policy_status)
                return
            raw = base64.b64encode(json.dumps(self.policy).encode()).decode()
            self.send_json({"content": raw})
        else:
            self.send_json({"message": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        if path == "/api/v1/repos/admin/demo/pulls/1/merge":
            self.__class__.merge_calls.append(body)
            if self.merge_status != 200:
                self.send_json({"message": "no"}, self.merge_status)
                return
            self.send_json({})
        else:
            self.send_json({"message": "not found"}, 404)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeGitea)
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.thread.start()
        self.root = f"http://127.0.0.1:{self.server.server_port}/api/v1"
        FakeGitea.pr = {
            "merged": False,
            "state": "open",
            "draft": False,
            "base": {"ref": "main"},
            "head": {"sha": HEAD, "repo": {"full_name": "admin/demo"}},
            "mergeable": True,
            "labels": [],
        }
        FakeGitea.files = [{"filename": "docs/readme.md"}]
        FakeGitea.files_page2 = []
        FakeGitea.move_head_after_files = None
        FakeGitea.policy = POLICY
        FakeGitea.policy_status = 200
        FakeGitea.merge_status = 200
        FakeGitea.merge_calls = []
        FakeGitea.polls = 0
        FakeGitea.poll_then_mergeable = False

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def run_gate(self):
        env = os.environ.copy()
        env.update(
            {
                "MERGE_TOKEN": "test-token",
                "API_URL": self.root,
                "REPO": "admin/demo",
                "PR": "1",
                "HEAD": HEAD,
            }
        )
        return subprocess.run(
            [sys.executable, "-c", gate_script()],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def test_schedules_merge_at_the_exact_head(self):
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(FakeGitea.merge_calls), 1)
        call = FakeGitea.merge_calls[0]
        self.assertEqual(call["head_commit_id"], HEAD)
        self.assertEqual(call["do"], "merge")
        self.assertTrue(call["merge_when_checks_succeed"])
        self.assertTrue(call["delete_branch_after_merge"])

    def test_already_merged_is_a_no_op(self):
        FakeGitea.pr["merged"] = True
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(FakeGitea.merge_calls, [])

    def test_refuses_draft(self):
        FakeGitea.pr["draft"] = True
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("open ready", result.stderr)
        self.assertEqual(FakeGitea.merge_calls, [])

    def test_refuses_moved_head(self):
        FakeGitea.pr["head"]["sha"] = OTHER
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("head moved", result.stderr)

    def test_refuses_fork(self):
        FakeGitea.pr["head"]["repo"]["full_name"] = "someone/demo"
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("fork PR", result.stderr)

    def test_refuses_blocking_label(self):
        FakeGitea.pr["labels"] = [{"name": "wip"}]
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("blocking label", result.stderr)

    def test_refuses_protected_path(self):
        FakeGitea.files = [{"filename": ".github/workflows/auto-merge.yml"}]
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("protected path", result.stderr)

    def test_refuses_gitea_workflow_path(self):
        FakeGitea.files = [{"filename": ".gitea/workflows/auto-merge.yml"}]
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("protected path", result.stderr)

    def test_refuses_policy_listed_path(self):
        FakeGitea.policy = {**POLICY, "protected_paths": ["Makefile"]}
        FakeGitea.files = [{"filename": "Makefile"}]
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("protected path", result.stderr)

    def test_refuses_head_move_during_verification(self):
        FakeGitea.move_head_after_files = OTHER
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("head moved during verification", result.stderr)
        self.assertEqual(FakeGitea.merge_calls, [])

    def test_pagination_scans_later_pages(self):
        FakeGitea.files = [
            {"filename": f"docs/{index}.md"} for index in range(50)
        ]
        FakeGitea.files_page2 = [
            {"filename": ".gitea/workflows/auto-merge.yml"}
        ]
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("protected path", result.stderr)
        self.assertEqual(FakeGitea.merge_calls, [])

    def test_refuses_renamed_protected_path(self):
        FakeGitea.files = [
            {
                "filename": "docs/auto-merge.yml",
                "previous_filename": ".github/workflows/auto-merge.yml",
            }
        ]
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("protected path", result.stderr)

    def test_refuses_forbidden_file(self):
        FakeGitea.files = [{"filename": ".env"}]
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("forbidden file", result.stderr)

    def test_refuses_missing_policy(self):
        FakeGitea.policy_status = 404
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("merge policy is missing", result.stderr)

    def test_refuses_invalid_policy(self):
        FakeGitea.policy = ["not", "an", "object"]
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("not a JSON object", result.stderr)

    def test_refuses_bad_policy_list(self):
        FakeGitea.policy = {"protected_paths": "Makefile"}
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("protected_paths", result.stderr)

    def test_refuses_merge_api_error(self):
        FakeGitea.merge_status = 405
        result = self.run_gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn("merge request failed", result.stderr)

    def test_waits_for_mergeability(self):
        FakeGitea.poll_then_mergeable = True
        result = self.run_gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(FakeGitea.merge_calls), 1)


if __name__ == "__main__":
    unittest.main()
