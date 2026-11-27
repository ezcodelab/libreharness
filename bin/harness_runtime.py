# SPDX-License-Identifier: MIT
"""Cross-platform state paths and queue locking."""

from __future__ import annotations

import contextlib
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Iterator

if os.name == "nt":
    import msvcrt
else:
    import fcntl


def state_root(env: dict[str, str] | None = None) -> Path:
    values = os.environ if env is None else env
    override = values.get("HARNESS_STATE")
    if override:
        return Path(override).expanduser()
    home = Path(values.get("HOME") or Path.home())
    if sys.platform == "win32":
        base = Path(values.get("LOCALAPPDATA") or home / "AppData/Local")
    elif sys.platform == "darwin":
        base = home / "Library/Application Support"
    else:
        base = Path(values.get("XDG_STATE_HOME") or home / ".local/state")
    return base / "libreharness"


def python_argv() -> list[str]:
    override = os.environ.get("LIBREHARNESS_PYTHON")
    if override:
        return [override]
    candidates = (
        [["py", "-3"], ["python"], ["python3"]]
        if sys.platform == "win32"
        else [["python3"], ["python"]]
    )
    for candidate in candidates:
        if shutil.which(candidate[0]):
            return candidate
    raise RuntimeError(
        "LibreHarness requires Python 3.10 or newer; set LIBREHARNESS_PYTHON"
    )


@contextlib.contextmanager
def locked(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        if os.name == "nt":
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            while True:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
