# SPDX-License-Identifier: MIT
"""Harbor agent adapter for LibreHarness.

Run LibreHarness as an OpenCode custom agent in a Harbor task:

    PYTHONPATH=/path/to/libreharness harbor run \\
      -d terminal-bench@2.0 \\
      -a harbor_agent.opencode_agent:OpenCodeLibreHarness \\
      -m <provider>/<model>

The adapter is deliberately thin. It inherits Harbor's stock OpenCode install
and run loop, uploads the LibreHarness workflow surface from ``setup()``, and
rewrites only the final OpenCode command through ``exec_as_agent``. The rewrite
removes the stock ``tee`` pipeline, which can turn a completed run with a benign
EPIPE on a secondary stream into an agent error, and tolerates only that narrow
case. A source-contract test fails when Harbor changes the command shape the
rewrite depends on.

The adapter does not install the local UI plugins, so auto-intake, close
reminders, and goal-watch cannot alter a benchmark task.
"""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import replace
from pathlib import Path
from typing import override

from harbor.agents.agent_auth_resolution import ProviderAccess
from harbor.agents.installed.opencode import OpenCode
from harbor.environments.base import BaseEnvironment

_STOCK_RUN_TAIL = re.compile(
    r"(?P<head>.*?)\s+2>&1\s+</dev/null\s+\|\s+stdbuf\s+-oL\s+tee\s+"
    r"(?P<output>(?:'[^']*'|\"[^\"]*\"|\S+))\s*$",
    re.DOTALL,
)
_STOP_EVENT = (
    r'"type"[[:space:]]*:[[:space:]]*"step_finish"'
    r'.*"reason"[[:space:]]*:[[:space:]]*"stop"'
)
_EPIPE = "EPIPE"


def rewrite_opencode_run_command(command: str) -> str:
    """Replace stock Harbor's OpenCode tee pipeline with a direct log write.

    Harbor 0.25.0 pipes the OpenCode JSON stream through ``stdbuf -oL tee``.
    OpenCode 1.19.5 can emit a benign EPIPE on a secondary stream and still
    exit non-zero after a completed run, so the pipeline makes Harbor record a
    passing task as an agent error. Write the stream straight to the same log
    and tolerate only the narrow case: non-zero exit, a completed stop event,
    and EPIPE somewhere in the stream.
    """
    match = _STOCK_RUN_TAIL.search(command)
    if match is None:
        return command
    head = match.group("head")
    output = match.group("output")
    stop_pattern = shlex.quote(_STOP_EVENT)
    return (
        f"{head} > {output} 2>&1 </dev/null; "
        "rc=$?; "
        'if [ "$rc" -ne 0 ]; then '
        f"if grep -Eq {stop_pattern} {output} 2>/dev/null && "
        f"grep -q {shlex.quote(_EPIPE)} {output} 2>/dev/null; then "
        "exit 0; fi; "
        'exit "$rc"; '
        "fi"
    )


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

    @override
    async def setup(self, environment: BaseEnvironment) -> None:
        # Harbor calls setup(), not configure(). The previous configure() hook
        # was dead code, so the pilot never uploaded the harness surface.
        await super().setup(environment)
        await self._upload_overlay(environment)

    @override
    async def exec_as_agent(
        self,
        environment: BaseEnvironment,
        command: str,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        timeout_sec: int | None = None,
    ):
        # Keep stock OpenCode.run() and its future flags. Only the final
        # command shape is ours to change.
        return await super().exec_as_agent(
            environment,
            rewrite_opencode_run_command(command),
            env=env,
            cwd=cwd,
            timeout_sec=timeout_sec,
        )

    async def _upload_overlay(self, environment: BaseEnvironment) -> None:
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

        # Docker uploads land as root; the agent user must be able to read and
        # execute the queue and the skill files.
        default_user = getattr(environment, "default_user", None)
        if default_user is not None:
            owner = shlex.quote(str(default_user))
            await self.exec_as_root(
                environment,
                command=f"chown -R {owner} {shlex.quote(config)} {shlex.quote(state)}",
            )
