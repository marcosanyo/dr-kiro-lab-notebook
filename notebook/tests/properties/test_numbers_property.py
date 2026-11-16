"""Property 13 of the lab-notebook design (Requirement 5.3).

Fixture values only: the doubles here are generated inputs, never presented as results (rules.md 4).
"""

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from notebook.numbers import full, short

finite_doubles = st.floats(allow_nan=False, allow_infinity=False, allow_subnormal=True, width=64)


def _significant_digits(text: str) -> int:
    """Number of significant digits of a decimal string, trailing zeros not counted."""
    return len(Decimal(text).normalize().as_tuple().digits)


# Feature: lab-notebook, Property 13: Numbers are rounded to 4 significant digits and shown in full when opened  # noqa: E501
@settings(max_examples=500)
@given(finite_doubles)
def test_short_rounds_to_four_significant_digits_and_full_reads_back(value: float) -> None:
    """**Validates: Requirements 5.3**"""
    shown = short(value, "property 13")
    assert float(shown) == float(format(value, ".3e"))
    assert _significant_digits(shown) <= 4

    opened = full(value, "property 13")
    assert float(opened) == value
    assert str(float(opened)) == str(value)  # keeps the sign of zero
