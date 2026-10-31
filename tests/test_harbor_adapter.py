# SPDX-License-Identifier: MIT
import asyncio
import importlib.util
import inspect
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
