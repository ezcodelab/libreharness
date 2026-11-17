# SPDX-License-Identifier: MIT
import subprocess
import sys
import tempfile
import unittest
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

    def test_copies_main_and_tags_without_deleting(self):
        mirror_public.mirror(self.source, "origin", "github")
        source_main = git(self.source, "rev-parse", "refs/remotes/origin/main")
        target_main = git(self.target_bare, "rev-parse", "refs/heads/main")
        self.assertEqual(source_main, target_main)
        target_tags = self.refs(self.target_bare, "refs/tags")
        self.assertIn("refs/tags/v1", target_tags)
        self.assertIn("refs/tags/v-extra", target_tags)
        self.assertIn("refs/heads/extra", self.refs(self.target_bare, "refs/heads"))

    def test_refuses_divergent_target_main(self):
        divergent = self.base / "divergent"
        subprocess.run(
            ["git", "init", "-b", "main", str(divergent)],
            check=True,
            capture_output=True,
        )
        git(divergent, "config", "user.email", "test@example.com")
        git(divergent, "config", "user.name", "Test")
        commit(divergent, "different.txt", "different")
        git(divergent, "remote", "add", "origin", str(self.target_bare))
        git(divergent, "push", "origin", "main")
        before = git(self.target_bare, "rev-parse", "refs/heads/main")
        with self.assertRaises(mirror_public.MirrorError):
            mirror_public.mirror(self.source, "origin", "github")
        self.assertEqual(before, git(self.target_bare, "rev-parse", "refs/heads/main"))

    def test_dry_run_does_not_write(self):
        mirror_public.mirror(self.source, "origin", "github", dry_run=True)
        self.assertNotIn("refs/heads/main", self.refs(self.target_bare, "refs/heads"))


if __name__ == "__main__":
    unittest.main()
