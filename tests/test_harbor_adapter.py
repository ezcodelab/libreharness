# SPDX-License-Identifier: MIT
import asyncio
import importlib.util
import inspect
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


@unittest.skipUnless(
    importlib.util.find_spec("harbor"),
    "Harbor is not installed in this Python environment",
)
class HarborAdapterTests(unittest.TestCase):
    @staticmethod
    def make_harness(root: Path) -> None:
        root.mkdir(parents=True)
        (root / "AGENTS.md").write_text("BASE RULES\n", encoding="utf-8")
        for folder in ("agents", "commands", "skills", "bin"):
            (root / folder).mkdir(parents=True)
        (root / "bin/tasks.py").write_text("", encoding="utf-8")
        (root / "skills/base-skill").mkdir()
        (root / "skills/base-skill/SKILL.md").write_text(
            "base skill\n", encoding="utf-8"
        )

    def test_setup_uploads_the_workflow_runtime(self) -> None:
        from harbor.agents.installed.opencode import OpenCode
        from harbor_agent.opencode_agent import OpenCodeLibreHarness

        class FakeEnvironment:
            default_user = "agent"

            def __init__(self) -> None:
                self.calls = []

            async def exec(self, command, **kwargs):
                self.calls.append(("exec", command, kwargs))
                return SimpleNamespace(
                    return_code=0,
                    stdout="/home/agent\n",
                    stderr="",
                )

            async def upload_dir(self, source, target) -> None:
                self.calls.append(("dir", str(source), target))

            async def upload_file(self, source, target) -> None:
                self.calls.append(("file", str(source), target))

        with tempfile.TemporaryDirectory() as temp:
            agent = OpenCodeLibreHarness(
                logs_dir=Path(temp),
                model_name="opencode/example",
            )
            environment = FakeEnvironment()
            with patch.object(OpenCode, "setup", new=AsyncMock()) as base_setup:
                asyncio.run(agent.setup(environment))

        base_setup.assert_awaited_once_with(environment)
        dirs = [call[2] for call in environment.calls if call[0] == "dir"]
        files = [call[2] for call in environment.calls if call[0] == "file"]
        for name in ("agents", "commands", "skills", "bin"):
            self.assertIn(f"/home/agent/.config/opencode/{name}", dirs)
        self.assertIn("/home/agent/.config/opencode/AGENTS.md", files)
        self.assertTrue(
            any(
                "chown -R agent /home/agent/.config/opencode" in call[1]
                for call in environment.calls
                if call[0] == "exec"
            )
        )

    def test_setup_uploads_a_profile_after_the_base(self) -> None:
        from harbor.agents.installed.opencode import OpenCode
        from harbor_agent.opencode_agent import OpenCodeLibreHarness

        class FakeEnvironment:
            default_user = "agent"

            def __init__(self) -> None:
                self.dirs = []
                self.files = []
                self.execs = []

            async def exec(self, command, **kwargs):
                self.execs.append(command)
                return SimpleNamespace(
                    return_code=0,
                    stdout="/home/agent\n",
                    stderr="",
                )

            async def upload_dir(self, source, target) -> None:
                self.dirs.append((str(source), target))

            async def upload_file(self, source, target) -> None:
                self.files.append((Path(source).read_text(encoding="utf-8"), target))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "harness"
            self.make_harness(root)
            profile = root / "profiles/egm"
            (profile / "skills/egm-comprehension").mkdir(parents=True)
            (profile / "skills/egm-comprehension/SKILL.md").write_text(
                "profile skill\n", encoding="utf-8"
            )
            (profile / "AGENTS.md").write_text("PROFILE RULES\n", encoding="utf-8")
            (profile / "NOTICE").write_text("MIT\n", encoding="utf-8")
            agent = OpenCodeLibreHarness(
                logs_dir=Path(temp) / "logs",
                model_name="opencode/example",
                harness_path=root,
                profile="egm",
            )
            environment = FakeEnvironment()
            with patch.object(OpenCode, "setup", new=AsyncMock()) as base_setup:
                asyncio.run(agent.setup(environment))

            base_setup.assert_awaited_once_with(environment)
            base_skills = [
                index
                for index, (source, target) in enumerate(environment.dirs)
                if target == "/home/agent/.config/opencode/skills"
                and "/profiles/" not in source
            ]
            profile_skills = [
                index
                for index, (source, target) in enumerate(environment.dirs)
                if target == "/home/agent/.config/opencode/skills"
                and source.endswith("/profiles/egm/skills")
            ]
            self.assertTrue(base_skills and profile_skills)
            self.assertLess(max(base_skills), max(profile_skills))
            agents_uploads = [
                content
                for content, target in environment.files
                if target == "/home/agent/.config/opencode/AGENTS.md"
            ]
            self.assertTrue(agents_uploads)
            self.assertIn("BASE RULES", agents_uploads[-1])
            self.assertIn("PROFILE RULES", agents_uploads[-1])
            self.assertIn("Optional profile: egm", agents_uploads[-1])
            self.assertTrue(
                any(
                    target == "/home/agent/.config/opencode/LIBREHARNESS-PROFILE-NOTICE"
                    for _content, target in environment.files
                )
            )
            metadata = json.loads(
                (Path(temp) / "logs/profile.json").read_text(encoding="utf-8")
            )
        self.assertEqual(metadata["name"], "egm")
        self.assertEqual(metadata["source"], "profiles/egm")
        self.assertIn("skills/egm-comprehension/SKILL.md", metadata["files"])

    def test_profile_is_a_harbor_option(self) -> None:
        from harbor_agent.opencode_agent import OpenCodeLibreHarness

        self.assertIn("profile", OpenCodeLibreHarness.options_schema()["properties"])

    def test_profile_env_fallback_and_explicit_precedence(self) -> None:
        from harbor_agent.opencode_agent import OpenCodeLibreHarness

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "harness"
            self.make_harness(root)
            for name in ("egm", "other"):
                profile = root / "profiles" / name
                profile.mkdir(parents=True)
                (profile / "AGENTS.md").write_text(name, encoding="utf-8")
            with patch.dict(os.environ, {"LIBREHARNESS_PROFILE": "egm"}):
                from_env = OpenCodeLibreHarness(
                    logs_dir=Path(temp) / "logs",
                    model_name="opencode/example",
                    harness_path=root,
                )
            self.assertEqual(from_env.profile, "egm")
            with patch.dict(os.environ, {"LIBREHARNESS_PROFILE": "other"}):
                explicit = OpenCodeLibreHarness(
                    logs_dir=Path(temp) / "logs",
                    model_name="opencode/example",
                    harness_path=root,
                    profile="egm",
                )
            self.assertEqual(explicit.profile, "egm")

    def test_profile_symlink_is_rejected(self) -> None:
        from harbor_agent.opencode_agent import OpenCodeLibreHarness

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "harness"
            self.make_harness(root)
            profile = root / "profiles/linked"
            profile.mkdir(parents=True)
            (profile / "AGENTS.md").write_text("linked\n", encoding="utf-8")
            (profile / "AGENTS.link").symlink_to(root / "AGENTS.md")
            with self.assertRaises(ValueError):
                OpenCodeLibreHarness(
                    logs_dir=Path(temp) / "logs",
                    model_name="opencode/example",
                    harness_path=root,
                    profile="linked",
                )

    def test_profile_collision_is_rejected(self) -> None:
        from harbor_agent.opencode_agent import OpenCodeLibreHarness

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "harness"
            self.make_harness(root)
            profile = root / "profiles/bad"
            (profile / "skills/base-skill").mkdir(parents=True)
            (profile / "skills/base-skill/SKILL.md").write_text(
                "collision\n", encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                OpenCodeLibreHarness(
                    logs_dir=Path(temp) / "logs",
                    model_name="opencode/example",
                    harness_path=root,
                    profile="bad",
                )

    def test_invalid_or_missing_profile_is_rejected(self) -> None:
        from harbor_agent.opencode_agent import OpenCodeLibreHarness

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "harness"
            self.make_harness(root)
            with self.assertRaises(ValueError):
                OpenCodeLibreHarness(
                    logs_dir=Path(temp) / "logs",
                    model_name="opencode/example",
                    harness_path=root,
                    profile="../escape",
                )
            with self.assertRaises(FileNotFoundError):
                OpenCodeLibreHarness(
                    logs_dir=Path(temp) / "logs",
                    model_name="opencode/example",
                    harness_path=root,
                    profile="missing",
                )

    def test_exec_as_agent_rewrites_only_the_stock_opencode_tail(self) -> None:
        from harbor.agents.installed.opencode import OpenCode
        from harbor_agent.opencode_agent import (
            OpenCodeLibreHarness,
            rewrite_opencode_run_command,
        )

        command = (
            "opencode --model=ollama-cloud/deepseek-v4.1-flash run --format=json "
            "--thinking --dangerously-skip-permissions -- 'do the task' "
            "2>&1 </dev/null | stdbuf -oL tee /logs/agent/opencode.txt"
        )
        rewritten = rewrite_opencode_run_command(command)
        self.assertNotIn("| stdbuf -oL tee", rewritten)
        self.assertIn("> /logs/agent/opencode.txt 2>&1", rewritten)
        self.assertIn('exit "$rc"', rewritten)
        self.assertEqual(
            rewrite_opencode_run_command("mkdir -p ~/.config/opencode"),
            "mkdir -p ~/.config/opencode",
        )

        with tempfile.TemporaryDirectory() as temp:
            agent = OpenCodeLibreHarness(
                logs_dir=Path(temp),
                model_name="opencode/example",
            )
            environment = SimpleNamespace()
            with patch.object(
                OpenCode, "exec_as_agent", new=AsyncMock()
            ) as base_exec:
                asyncio.run(agent.exec_as_agent(environment, command))

        base_exec.assert_awaited_once()
        self.assertEqual(base_exec.await_args.args[0], environment)
        self.assertEqual(base_exec.await_args.args[1], rewritten)

    def test_rewrite_tolerates_epipe_after_a_completed_stop(self) -> None:
        from harbor_agent.opencode_agent import rewrite_opencode_run_command

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log = root / "opencode.txt"
            log.write_text(
                "\n".join(
                    [
                        "error: EPIPE: broken pipe, write",
                        '{"type":"step_finish","part":{"reason":"stop"}}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            script = root / "fake-opencode.sh"
            script.write_text(f"cat {log}\nexit 1\n", encoding="utf-8")
            output = root / "captured.txt"
            command = (
                f"sh {script} 2>&1 </dev/null | stdbuf -oL tee {output}"
            )
            result = subprocess.run(
                rewrite_opencode_run_command(command),
                shell=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, "completed stop + EPIPE was not tolerated")

    def test_rewrite_rejects_a_real_crash(self) -> None:
        from harbor_agent.opencode_agent import rewrite_opencode_run_command

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log = root / "opencode.txt"
            log.write_text(
                '{"type":"step_start","part":{}}\n',
                encoding="utf-8",
            )
            script = root / "fake-opencode.sh"
            script.write_text(f"cat {log}\nexit 1\n", encoding="utf-8")
            output = root / "captured.txt"
            command = (
                f"sh {script} 2>&1 </dev/null | stdbuf -oL tee {output}"
            )
            result = subprocess.run(
                rewrite_opencode_run_command(command),
                shell=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0, "a real crash was swallowed")

    def test_adapter_uses_harbor_hooks_not_a_copied_run_loop(self) -> None:
        from harbor.agents.installed.opencode import OpenCode
        from harbor_agent.opencode_agent import (
            OpenCodeLibreHarness,
            rewrite_opencode_run_command,
        )

        self.assertIn("setup", OpenCodeLibreHarness.__dict__)
        self.assertNotIn("configure", OpenCodeLibreHarness.__dict__)
        self.assertNotIn("run", OpenCodeLibreHarness.__dict__)

        # If Harbor fixes the tee pipeline, delete the rewrite and this test.
        source = inspect.getsource(OpenCode.run)
        normalized = " ".join(source.split())
        self.assertIn("opencode --model=", normalized)
        self.assertIn("run --format=json", normalized)
        self.assertIn("2>&1 </dev/null | stdbuf -oL tee", normalized)
        rendered = (
            "opencode --model=x/y run --format=json -- 'do it' "
            "2>&1 </dev/null | stdbuf -oL tee /logs/agent/opencode.txt"
        )
        self.assertNotEqual(rewrite_opencode_run_command(rendered), rendered)


if __name__ == "__main__":
    unittest.main()
