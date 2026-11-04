# SPDX-License-Identifier: MIT
"""Verifier for the test-first bugfix task.

The agent must add a regression test that fails on the baseline and passes on
the fixed code, keep the existing test unchanged, and make the zero-division
behavior raise ValueError.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

APP = Path("/app")
BASELINE = Path("/tests/baseline")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_pytest(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(cwd)
    return subprocess.run(
        ["pytest", "-q", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=environment,
    )


def test_regression_file_exists() -> None:
    assert (APP / "tests" / "test_regression.py").is_file()


def test_existing_test_is_unchanged() -> None:
    assert digest(APP / "tests" / "test_calc.py") == digest(
        BASELINE / "test_calc.py"
    )


def test_all_tests_pass() -> None:
    result = run_pytest(APP, "tests")
    assert result.returncode == 0, result.stdout + result.stderr


def test_regression_fails_on_baseline() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        shutil.copy(BASELINE / "calc.py", root / "calc.py")
        shutil.copy(APP / "tests" / "test_regression.py", root / "test_regression.py")
        result = run_pytest(root, "test_regression.py")
        assert result.returncode != 0, (
            "The regression test passes against the buggy baseline; it does not "
            "reproduce the bug.\n" + result.stdout + result.stderr
        )


def test_zero_denominator_raises_value_error() -> None:
    result = subprocess.run(
        [
            "python",
            "-c",
            "from calc import safe_div; "
            "safe_div(1, 0)",
        ],
        cwd=APP,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "ValueError" in result.stderr
