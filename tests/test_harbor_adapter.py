# SPDX-License-Identifier: MIT
import asyncio
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


@unittest.skipUnless(
    importlib.util.find_spec("harbor"),
    "Harbor is not installed in this Python environment",
)
class HarborAdapterTests(unittest.TestCase):
    def test_configure_uploads_the_workflow_runtime(self) -> None:
        from harbor_agent.opencode_agent import OpenCodeLibreHarness

        class FakeEnvironment:
            def __init__(self) -> None:
                self.calls = []

            async def exec(self, command, **_kwargs):
                self.calls.append(("exec", command))
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
            asyncio.run(agent.configure(environment))

        dirs = [call[2] for call in environment.calls if call[0] == "dir"]
        files = [call[2] for call in environment.calls if call[0] == "file"]
        for name in ("agents", "commands", "skills", "bin"):
            self.assertIn(f"/home/agent/.config/opencode/{name}", dirs)
        self.assertIn("/home/agent/.config/opencode/AGENTS.md", files)
        self.assertTrue(
            any("mkdir -p /home/agent/.config/opencode" in call[1] for call in environment.calls if call[0] == "exec")
        )


if __name__ == "__main__":
    unittest.main()
