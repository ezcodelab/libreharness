<!-- SPDX-License-Identifier: MIT -->
The repository is `/app`. The `safe_div` function in `/app/calc.py` silently
returns `0` when the denominator is zero. That hides a programming error.

Your task:

1. Add a regression test at `/app/tests/test_regression.py` that fails against
   the current code and expects a `ValueError` for a zero denominator.
2. Fix `/app/calc.py` so the regression test passes.
3. Keep `/app/tests/test_calc.py` unchanged and keep all tests passing.

Run `pytest -q /app/tests` to check your work. Do not delete or rewrite the
existing test.
