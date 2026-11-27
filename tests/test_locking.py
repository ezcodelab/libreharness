# SPDX-License-Identifier: MIT
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import harness_runtime

WORKER = """
import sys
import time
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import harness_runtime

lock = Path(sys.argv[2])
events = Path(sys.argv[3])
for _ in range(3):
    with harness_runtime.locked(lock):
        with events.open("a") as stream:
            stream.write("start\\n")
            stream.flush()
        time.sleep(0.03)
        with events.open("a") as stream:
            stream.write("end\\n")
            stream.flush()
"""


class LockingTests(unittest.TestCase):
    def test_competing_processes_do_not_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worker = root / "worker.py"
            events = root / "events.txt"
            worker.write_text(WORKER)
            processes = [
                subprocess.Popen(
                    [
                        *harness_runtime.python_argv(),
                        str(worker),
                        str(Path(__file__).resolve().parent.parent / "bin"),
                        str(root / "work.lock"),
                        str(events),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for _ in range(4)
            ]
            for process in processes:
                stdout, stderr = process.communicate(timeout=30)
                self.assertEqual(process.returncode, 0, stdout + stderr)
            active = 0
            for line in events.read_text().splitlines():
                if line == "start":
                    active += 1
                    self.assertEqual(active, 1, "two processes held the lock together")
                else:
                    active -= 1
                    self.assertEqual(active, 0, "a process released without holding")
            self.assertEqual(active, 0)

    def test_state_root_uses_platform_conventions(self) -> None:
        home = "/home/operator"
        with mock.patch.object(harness_runtime.sys, "platform", "linux"):
            self.assertEqual(
                harness_runtime.state_root({"HOME": home}),
                Path(home) / ".local/state/libreharness",
            )
            self.assertEqual(
                harness_runtime.state_root(
                    {"HOME": home, "XDG_STATE_HOME": "/var/state"}
                ),
                Path("/var/state/libreharness"),
            )
        with mock.patch.object(harness_runtime.sys, "platform", "darwin"):
            self.assertEqual(
                harness_runtime.state_root({"HOME": home}),
                Path(home) / "Library/Application Support/libreharness",
            )
        with mock.patch.object(harness_runtime.sys, "platform", "win32"):
            self.assertEqual(
                harness_runtime.state_root(
                    {"HOME": home, "LOCALAPPDATA": "C:/Users/operator/AppData/Local"}
                ),
                Path("C:/Users/operator/AppData/Local/libreharness"),
            )
        with mock.patch.object(harness_runtime.sys, "platform", "linux"):
            self.assertEqual(
                harness_runtime.state_root(
                    {"HOME": home, "HARNESS_STATE": "/explicit/state"}
                ),
                Path("/explicit/state"),
            )


if __name__ == "__main__":
    unittest.main()
