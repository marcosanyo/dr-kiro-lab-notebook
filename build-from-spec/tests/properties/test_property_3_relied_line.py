# Feature: build-from-spec, Property 3: Relied-on line round trip
"""For any distinct relied-on ids (or `none` alone), the printed line parses back to the same ids, also with
any number of spaces after each comma. For any line that adds a leading or trailing space, an empty id, a
doubled comma, or `none` next to another id, the parser returns None.

**Validates: Requirements 10.1**
"""

from collections.abc import Callable

from hypothesis import given, settings
from hypothesis import strategies as st

from build_from_spec.relied import PREFIX, format_ids, parse_ids
from support import relied_id_tuples, relied_ids


def spaced_line(ids: tuple[str, ...], gaps: list[int]) -> str:
    """The relied-on line for ids, with gaps[i] spaces after the comma that precedes ids[i + 1]."""
    line = PREFIX + ids[0]
    for identifier, spaces in zip(ids[1:], gaps, strict=True):
        line += "," + " " * spaces + identifier
    return line


# Each mutation takes the valid ids and one other id, and returns a line the parser must refuse.
MUTATIONS: list[Callable[[tuple[str, ...], str], str]] = [
    lambda ids, other: " " + format_ids(ids),
    lambda ids, other: format_ids(ids) + " ",
    lambda ids, other: format_ids(ids) + ",",
    lambda ids, other: PREFIX + ", " + other,
    lambda ids, other: PREFIX + ids[0] + ",," + other,
    lambda ids, other: PREFIX + "none, " + other,
    lambda ids, other: PREFIX + other + ", none",
]


@settings(max_examples=100, deadline=None)
@given(data=st.data())
def test_relied_line_round_trip(data):
    ids = data.draw(relied_id_tuples())
    assert parse_ids(format_ids(ids)) == ids
    gaps = data.draw(
        st.lists(st.integers(min_value=0, max_value=3), min_size=len(ids) - 1, max_size=len(ids) - 1)
    )
    assert parse_ids(spaced_line(ids, gaps)) == ids


@settings(max_examples=100, deadline=None)
@given(data=st.data())
def test_malformed_relied_line_is_refused(data):
    ids = data.draw(relied_id_tuples())
    other = data.draw(relied_ids)
    mutation = data.draw(st.sampled_from(MUTATIONS))
    line = mutation(ids, other)
    assert parse_ids(line) is None, line
