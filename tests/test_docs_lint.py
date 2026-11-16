# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))
import docs_lint  # noqa: E402


class SkillBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.skills = Path(self.tmp.name) / "skills"
        self.skills.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write_skill(self, name: str, lines: int = 3):
        path = self.skills / name
        path.mkdir()
        body = "---\nname: test\ndescription: test\n---\n"
        path.joinpath("SKILL.md").write_text(
            body + ("line\n" * max(lines - 4, 0)), encoding="utf-8"
        )

    def test_nine_skills_pass_with_no_cap(self):
        for index in range(9):
            self.write_skill(f"skill-{index}")
        self.assertEqual(docs_lint.check_skills(self.skills, None, 120), [])

    def test_explicit_cap_still_fails(self):
        for index in range(9):
            self.write_skill(f"skill-{index}")
        problems = docs_lint.check_skills(self.skills, 8, 120)
        self.assertTrue(any("explicit cap" in item["reason"] for item in problems))

    def test_line_limit_still_fails(self):
        self.write_skill("long", lines=121)
        problems = docs_lint.check_skills(self.skills, None, 120)
        self.assertTrue(any("121 lines exceeds 120" in item["reason"] for item in problems))


if __name__ == "__main__":
    unittest.main()
