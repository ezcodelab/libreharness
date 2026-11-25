#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Resolve pinned repository-check tools without distributing them with the plugin."""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import platform
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path, PurePosixPath

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
TOOLS = {
    "gitleaks": {
        "version": "8.30.1",
        "binary": "gitleaks",
        "base": "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1",
        "assets": {
            "x86_64": (
                "gitleaks_8.30.1_linux_x64.tar.gz",
                "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
            ),
            "aarch64": (
                "gitleaks_8.30.1_linux_arm64.tar.gz",
                "e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080",
            ),
        },
    },
    "lychee": {
        "version": "0.24.2",
        "binary": "lychee",
        "base": "https://github.com/lycheeverse/lychee/releases/download/lychee-v0.24.2",
        "assets": {
            "x86_64": (
                "lychee-x86_64-unknown-linux-musl.tar.gz",
                "73657a111819a30c47c08352896796f23d64e4eb2b3ed39b6d32149241566fc5",
            ),
            "aarch64": (
                "lychee-aarch64-unknown-linux-musl.tar.gz",
                "5d0b0e3aeab240f41920c633a6eaf97599be6eedda034b36e858ede7dba5e535",
            ),
        },
    },
    "actionlint": {
        "version": "1.7.7",
        "binary": "actionlint",
        "base": "https://github.com/rhysd/actionlint/releases/download/v1.7.7",
        "assets": {
            "x86_64": (
                "actionlint_1.7.7_linux_amd64.tar.gz",
                "023070a287cd8cccd71515fedc843f1985bf96c436b7effaecce67290e7e0757",
            ),
            "aarch64": (
                "actionlint_1.7.7_linux_arm64.tar.gz",
                "401942f9c24ed71e4fe71b76c7d638f66d8633575c4016efd2977ce7c28317d0",
            ),
        },
    },
    "shellcheck": {
        "version": "0.11.0",
        "binary": "shellcheck",
        "base": "https://github.com/koalaman/shellcheck/releases/download/v0.11.0",
        "assets": {
            "x86_64": (
                "shellcheck-v0.11.0.linux.x86_64.tar.gz",
                "b7af85e41cc99489dcc21d66c6d5f3685138f06d34651e6d34b42ec6d54fe6f6",
            ),
            "aarch64": (
                "shellcheck-v0.11.0.linux.aarch64.tar.gz",
                "68a8133197a50beb8803f8d42f9908d1af1c5540d4bb05fdfca8c1fa47decefc",
            ),
        },
    },
}


class DevtoolError(RuntimeError):
    pass


def platform_key(machine: str | None = None) -> str:
    if sys.platform != "linux":
        raise DevtoolError("repository checks support Linux only")
    current = (machine or platform.machine()).lower()
    aliases = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "aarch64": "aarch64",
        "arm64": "aarch64",
    }
    key = aliases.get(current)
    if key is None:
        raise DevtoolError(f"no pinned tool binary for architecture {current!r}")
    return key


def cache_root() -> Path:
    override = os.environ.get("LIBREHARNESS_TOOLS")
    if override:
        return Path(override).expanduser()
    base = os.environ.get("XDG_CACHE_HOME")
    if base:
        return Path(base).expanduser() / "libreharness" / "tools"
    return Path.home() / ".cache/libreharness/tools"


def tool_path(name: str, cache: Path) -> Path:
    spec = TOOLS.get(name)
    if spec is None:
        raise DevtoolError(f"unknown tool {name!r}; choose {', '.join(sorted(TOOLS))}")
    return cache / name / spec["version"] / spec["binary"]


def verify_archive(data: bytes, expected: str, name: str) -> None:
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise DevtoolError(
            f"{name}: checksum mismatch; expected {expected}, downloaded {actual}"
        )


def install_archive(data: bytes, binary: str, destination: Path, name: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            matches = [
                member
                for member in archive.getmembers()
                if member.isfile() and PurePosixPath(member.name).name == binary
            ]
            if len(matches) != 1:
                raise DevtoolError(
                    f"{name}: archive must contain exactly one {binary} binary"
                )
            source = archive.extractfile(matches[0])
            if source is None:
                raise DevtoolError(f"{name}: cannot read {binary} from archive")
            handle, temporary = tempfile.mkstemp(
                dir=destination.parent, prefix=f".{destination.name}."
            )
            try:
                with os.fdopen(handle, "wb") as stream:
                    while chunk := source.read(1024 * 1024):
                        stream.write(chunk)
                os.chmod(temporary, 0o755)
                os.replace(temporary, destination)
            except BaseException:
                Path(temporary).unlink(missing_ok=True)
                raise
    except tarfile.TarError as exc:
        raise DevtoolError(f"{name}: malformed archive: {exc}") from exc


def download(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "libreharness-devtool"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(MAX_ARCHIVE_BYTES + 1)
    except OSError as exc:
        raise DevtoolError(f"download failed for {url}: {exc}") from exc
    if len(data) > MAX_ARCHIVE_BYTES:
        raise DevtoolError(f"download exceeds {MAX_ARCHIVE_BYTES} bytes: {url}")
    return data


def ensure(name: str, cache: Path, *, force: bool = False) -> Path:
    spec = TOOLS.get(name)
    if spec is None:
        raise DevtoolError(f"unknown tool {name!r}; choose {', '.join(sorted(TOOLS))}")
    destination = tool_path(name, cache)
    if destination.is_file() and os.access(destination, os.X_OK) and not force:
        return destination
    architecture = platform_key()
    asset, expected = spec["assets"][architecture]
    url = f"{spec['base']}/{asset}"
    data = download(url)
    verify_archive(data, expected, name)
    install_archive(data, spec["binary"], destination, name)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ensure_parser = sub.add_parser("ensure", help="download missing pinned tools")
    ensure_parser.add_argument("tools", nargs="*", choices=sorted(TOOLS))
    ensure_parser.add_argument("--force", action="store_true")
    run_parser = sub.add_parser("run", help="run a pinned tool")
    run_parser.add_argument("tool", choices=sorted(TOOLS))
    run_parser.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    cache = cache_root()
    try:
        if args.command == "ensure":
            names = args.tools or sorted(TOOLS)
            for name in names:
                print(f"{name}: {ensure(name, cache, force=args.force)}")
            return 0
        executable = ensure(args.tool, cache)
        return subprocess.run([str(executable), *args.args], check=False).returncode
    except DevtoolError as exc:
        print(f"devtool: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
