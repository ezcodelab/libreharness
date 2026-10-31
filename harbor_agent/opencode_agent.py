# SPDX-License-Identifier: MIT
"""Harbor agent adapter for LibreHarness.

Run LibreHarness as an OpenCode custom agent in a Harbor task:

    PYTHONPATH=/path/to/libreharness harbor run \\
      -d terminal-bench@2.0 \\
      -a harbor_agent.opencode_agent:OpenCodeLibreHarness \\
      -m <provider>/<model>

The adapter installs OpenCode through Harbor's stock OpenCode integration, then
uploads the LibreHarness workflow files into the sandbox's OpenCode config. It
does not install the local UI plugins, so auto-intake, close reminders, and
goal-watch cannot alter a benchmark task.
"""

from __future__ import annotations

import os
import shlex
from dataclasses import replace
from pathlib import Path

from harbor.agents.agent_auth_resolution import ProviderAccess
from harbor.agents.installed.opencode import OpenCode
from harbor.environments.base import BaseEnvironment


class OpenCodeLibreHarness(OpenCode):
    """OpenCode plus the LibreHarness agents, commands, skills, and queue."""

    # OpenCode's native Ollama provider reads OLLAMA_API_KEY. Harbor's stock
    # OpenCode mapping only looks for OPENAI_API_KEY, which made the first
    # Terminal-Bench trial call ollama.com without a credential.
    MODEL_CONNECTION = replace(
        OpenCode.MODEL_CONNECTION,
        agent_provider_access=ProviderAccess(
            api_key_candidate_names=[
                "OLLAMA_API_KEY",
                "OPENCODE_API_KEY",
                "OPENAI_API_KEY",
            ],
            base_url_candidate_names=[
                "OLLAMA_BASE_URL",
                "OPENCODE_BASE_URL",
                "OPENAI_BASE_URL",
                "OPENAI_API_BASE",
            ],
        ),
        api_key_destination_names={
            "ollama-cloud": "OLLAMA_API_KEY",
            "opencode": "OPENCODE_API_KEY",
            "default": "OPENAI_API_KEY",
        },
    )

    def __init__(
        self,
        *args,
        harness_path: str | Path | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        configured = harness_path or os.environ.get("LIBREHARNESS_HOME")
        self.harness_path = Path(
            configured or Path(__file__).resolve().parents[1]
        ).expanduser().resolve()
        if not self.harness_path.is_dir():
            raise FileNotFoundError(
                f"LibreHarness checkout not found: {self.harness_path}"
            )
        for required in ("AGENTS.md", "agents", "commands", "skills", "bin/tasks.py"):
            if not (self.harness_path / required).exists():
                raise FileNotFoundError(
                    f"LibreHarness runtime missing {required} in {self.harness_path}"
                )

    @staticmethod
    def name() -> str:
        return "opencode-libreharness"

    async def configure(self, environment: BaseEnvironment) -> None:
        await super().configure(environment)
        home = (await self.exec_as_agent(
            environment, command='printf %s "$HOME"'
        )).stdout.strip()
        if not home:
            raise RuntimeError("could not resolve the agent HOME in the sandbox")
        config = f"{home}/.config/opencode"
        state = f"{home}/.local/state/libreharness"
        targets = " ".join(
            shlex.quote(f"{config}/{folder}")
            for folder in ("agents", "commands", "skills", "bin")
        )
        await self.exec_as_agent(
            environment,
            command=f"mkdir -p {shlex.quote(config)} {shlex.quote(state)} {targets}",
        )

        # Upload the workflow surface. Keep local plugins out of the benchmark:
        # auto-intake, goal-watch, and close reminders are not part of the
        # measured engineering loop and add nondeterministic side effects.
        for folder in ("agents", "commands", "skills", "bin"):
            source = self.harness_path / folder
            if not source.is_dir():
                raise FileNotFoundError(f"missing LibreHarness directory: {source}")
            await environment.upload_dir(str(source), f"{config}/{folder}")
        await environment.upload_file(
            str(self.harness_path / "AGENTS.md"),
            f"{config}/AGENTS.md",
        )
