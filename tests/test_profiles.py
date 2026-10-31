# SPDX-License-Identifier: MIT
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "profiles"


class ProfileTests(unittest.TestCase):
    def test_each_profile_has_docs_and_notice(self) -> None:
        for profile in sorted(path for path in PROFILES.iterdir() if path.is_dir()):
            with self.subTest(profile=profile.name):
                self.assertTrue((profile / "README.md").is_file())
                self.assertTrue((profile / "AGENTS.md").is_file())
                self.assertTrue((profile / "NOTICE").is_file())

    def test_profiles_have_no_executables_or_symlinks(self) -> None:
        forbidden = {".sh", ".js", ".cjs", ".mjs", ".ts", ".py"}
        for path in PROFILES.rglob("*"):
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertFalse(path.is_symlink(), f"symlink: {path}")
                if path.is_file():
                    self.assertNotIn(path.suffix, forbidden, f"executable: {path}")

    def test_profile_skills_have_frontmatter(self) -> None:
        for skill in sorted(PROFILES.glob("*/skills/*/SKILL.md")):
            with self.subTest(skill=skill.relative_to(ROOT)):
                text = skill.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"), "missing frontmatter")
                frontmatter = text.split("---", 2)[1]
                self.assertIn("name:", frontmatter)
                self.assertIn("description:", frontmatter)

    def test_superpowers_has_no_excluded_execution_handoffs(self) -> None:
        text = (
            PROFILES / "superpowers/skills/writing-plans/SKILL.md"
        ).read_text(encoding="utf-8")
        for token in (
            "subagent-driven-development",
            "executing-plans",
            "using-git-worktrees",
            "docs/superpowers/plans",
        ):
            self.assertNotIn(token, text)

    def test_superpowers_skills_do_not_use_the_plugin_namespace(self) -> None:
        for skill in sorted((PROFILES / "superpowers/skills").rglob("*.md")):
            with self.subTest(skill=skill.relative_to(ROOT)):
                self.assertNotIn("superpowers:", skill.read_text(encoding="utf-8"))

    def test_attribution_pins_upstream_commits(self) -> None:
        egm = (PROFILES / "egm/NOTICE").read_text(encoding="utf-8")
        superpowers = (PROFILES / "superpowers/NOTICE").read_text(encoding="utf-8")
        self.assertIn("403d888", egm)
        self.assertIn("Apache License", egm)
        self.assertIn("2ce8aa1", superpowers)
        self.assertIn("MIT License", superpowers)
        self.assertTrue((PROFILES / "superpowers/LICENSE").is_file())


if __name__ == "__main__":
    unittest.main()
