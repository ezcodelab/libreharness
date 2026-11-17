# SPDX-License-Identifier: MIT
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))
import mirror_public  # noqa: E402


def git(cwd, *args):
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def init_repo(path):
    subprocess.run(["git", "init", "--bare", str(path)], check=True, capture_output=True)
    work = path.parent / f"{path.name}-work"
    subprocess.run(["git", "init", "-b", "main", str(work)], check=True, capture_output=True)
    git(work, "config", "user.email", "test@example.com")
    git(work, "config", "user.name", "Test")
    git(work, "config", "tag.gpgSign", "false")
    return work


def commit(work, name="file.txt", text="one"):
    (work / name).write_text(text + "\n", encoding="utf-8")
    git(work, "add", name)
    git(work, "commit", "-m", f"add {name}")


class MirrorPublicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.source_bare = self.base / "source.git"
        self.source = init_repo(self.source_bare)
        commit(self.source)
        git(self.source, "tag", "v1")
        git(self.source, "remote", "add", "origin", str(self.source_bare))
        git(self.source, "push", "origin", "main", "--tags")

        self.target_bare = self.base / "target.git"
        subprocess.run(
            ["git", "init", "--bare", str(self.target_bare)],
            check=True,
            capture_output=True,
        )
        self.target_extra = self.base / "target-extra"
        subprocess.run(
            ["git", "init", "-b", "extra", str(self.target_extra)],
            check=True,
            capture_output=True,
        )
        git(self.target_extra, "config", "user.email", "test@example.com")
        git(self.target_extra, "config", "user.name", "Test")
        git(self.target_extra, "config", "tag.gpgSign", "false")
        commit(self.target_extra, "extra.txt", "extra")
        git(self.target_extra, "tag", "v-extra")
        git(self.target_extra, "remote", "add", "origin", str(self.target_bare))
        git(self.target_extra, "push", "origin", "extra")
        git(self.target_extra, "push", "origin", "v-extra")

        git(self.source, "remote", "add", "github", str(self.target_bare))

    def tearDown(self):
        self.tmp.cleanup()

    def refs(self, bare, pattern):
        output = git(bare, "for-each-ref", "--format=%(refname)", pattern)
        return set(output.splitlines())

    def test_status_and_freshness_check(self):
        status_file = self.base / "status.json"
        status = mirror_public.run_once(
            [self.source], "origin", "github", status_file, False, {}
        )
        self.assertTrue(status["ok"])
        ok, detail = mirror_public.check_status(status_file, 1200)
        self.assertTrue(ok, detail)
        data = json.loads(status_file.read_text(encoding="utf-8"))
        data["last_success"] = (
            datetime.now(timezone.utc) - timedelta(seconds=1300)
        ).isoformat(timespec="seconds")
        status_file.write_text(json.dumps(data), encoding="utf-8")
        ok, detail = mirror_public.check_status(status_file, 1200)
        self.assertFalse(ok)
        self.assertIn("limit 1200", detail)

    def test_lock_rejects_second_run(self):
        lock_path = self.base / "mirror.lock"
        lock = mirror_public.acquire_lock(lock_path)
        try:
            with self.assertRaises(mirror_public.LockBusy):
                mirror_public.acquire_lock(lock_path)
        finally:
            lock.close()

    def test_check_missing_status_fails(self):
        ok, detail = mirror_public.check_status(self.base / "missing.json", 1200)
        self.assertFalse(ok)
        self.assertIn("no mirror status", detail)

    def test_copies_main_and_tags_without_deleting(self):
        mirror_public.mirror(self.source, "origin", "github")
        source_main = git(self.source, "rev-parse", "refs/remotes/origin/main")
        target_main = git(self.target_bare, "rev-parse", "refs/heads/main")
        self.assertEqual(source_main, target_main)
        target_tags = self.refs(self.target_bare, "refs/tags")
        self.assertIn("refs/tags/v1", target_tags)
        self.assertIn("refs/tags/v-extra", target_tags)
        self.assertIn("refs/heads/extra", self.refs(self.target_bare, "refs/heads"))

    def make_divergent_target_main(self):
        divergent = self.base / "divergent"
        subprocess.run(
            ["git", "init", "-b", "main", str(divergent)],
            check=True,
            capture_output=True,
        )
        git(divergent, "config", "user.email", "test@example.com")
        git(divergent, "config", "user.name", "Test")
        git(divergent, "config", "tag.gpgSign", "false")
        commit(divergent, "different.txt", "different")
        git(divergent, "remote", "add", "origin", str(self.target_bare))
        git(divergent, "push", "origin", "main")

    def test_refuses_divergent_target_main(self):
        self.make_divergent_target_main()
        before = git(self.target_bare, "rev-parse", "refs/heads/main")
        with self.assertRaises(mirror_public.MirrorError):
            mirror_public.mirror(self.source, "origin", "github")
        self.assertEqual(before, git(self.target_bare, "rev-parse", "refs/heads/main"))

    def test_run_once_failure_preserves_last_success(self):
        self.make_divergent_target_main()
        status_file = self.base / "status.json"
        previous = {"last_success": "2026-11-17T00:00:00+00:00", "repos": {}}
        status = mirror_public.run_once(
            [self.source], "origin", "github", status_file, False, previous
        )
        self.assertFalse(status["ok"])
        self.assertEqual(status["last_success"], previous["last_success"])
        result = next(iter(status["repos"].values()))
        self.assertFalse(result["ok"])
        ok, detail = mirror_public.check_status(status_file, 1200)
        self.assertFalse(ok)
        self.assertIn("last mirror run failed", detail)

    def test_run_once_dry_run_writes_no_status(self):
        status_file = self.base / "status.json"
        status = mirror_public.run_once(
            [self.source], "origin", "github", status_file, True, {}
        )
        self.assertTrue(status["ok"])
        self.assertFalse(status_file.exists())

    def test_main_skips_when_lock_held(self):
        lock_path = self.base / "held.lock"
        status_file = self.base / "status.json"
        lock = mirror_public.acquire_lock(lock_path)
        argv = sys.argv
        try:
            sys.argv = [
                "mirror_public.py",
                "--repo",
                str(self.source),
                "--source",
                "origin",
                "--target",
                "github",
                "--lock-file",
                str(lock_path),
                "--status-file",
                str(status_file),
            ]
            try:
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    rc = mirror_public.main()
            finally:
                sys.argv = argv
        finally:
            lock.close()
        self.assertEqual(rc, 0)
        self.assertIn("skipped", stderr.getvalue())
        self.assertFalse(status_file.exists())

    def test_check_rejects_malformed_status(self):
        status_file = self.base / "bad.json"
        payloads = [
            "[]",
            '"hello"',
            '{"ok": true, "last_success": 123, "repos": {}}',
            '{"ok": true, "last_success": "not-a-date", "repos": {}}',
            '{"ok": true, "last_success": "2999-01-01T00:00:00+00:00", "repos": {}}',
            '{"ok": true, "last_success": "2026-11-17T00:00:00+00:00"}',
            '{"ok": true, "repos": {}}',
        ]
        for payload in payloads:
            status_file.write_text(payload, encoding="utf-8")
            ok, _detail = mirror_public.check_status(status_file, 1200)
            self.assertFalse(ok, payload)

    def test_check_accepts_naive_timestamp_as_utc(self):
        status_file = self.base / "status.json"
        last = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(
            timespec="seconds"
        )
        status_file.write_text(
            json.dumps({"ok": True, "last_success": last, "repos": {}}),
            encoding="utf-8",
        )
        ok, detail = mirror_public.check_status(status_file, 1200)
        self.assertTrue(ok, detail)

    def test_check_reports_failed_status(self):
        status_file = self.base / "status.json"
        last = datetime.now(timezone.utc).isoformat(timespec="seconds")
        status_file.write_text(
            json.dumps(
                {
                    "ok": False,
                    "last_success": last,
                    "repos": {"repo": {"error": "boom"}},
                }
            ),
            encoding="utf-8",
        )
        ok, detail = mirror_public.check_status(status_file, 1200)
        self.assertFalse(ok)
        self.assertIn("boom", detail)

    def test_dry_run_does_not_write(self):
        mirror_public.mirror(self.source, "origin", "github", dry_run=True)
        self.assertNotIn("refs/heads/main", self.refs(self.target_bare, "refs/heads"))


if __name__ == "__main__":
    unittest.main()
