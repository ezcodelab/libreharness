# SPDX-License-Identifier: MIT
from calc import safe_div


def test_positive_division() -> None:
    assert safe_div(10, 2) == 5
