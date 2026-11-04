# SPDX-License-Identifier: MIT
"""Small arithmetic helpers for the test-first benchmark task."""


def safe_div(a: float, b: float) -> float:
    """Divide a by b.

    The zero-denominator branch is intentionally wrong in the baseline: it
    returns 0 instead of raising. The task is to add a regression test and fix
    it.
    """
    if b == 0:
        return 0
    return a / b
