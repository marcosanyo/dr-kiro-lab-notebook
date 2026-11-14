"""Property 13: Told set export equals the declaration (wind-tunnel Requirements 1.1, 2.1-2.4).

Feature: wind-tunnel, Property 13.
"""

import re
import tempfile
from pathlib import Path
from unittest import mock

from bench.adapter import (
    DESCRIPTION_MAX,
    Declaration,
    FunctionKnob,
    Measurement,
    NumberKnob,
    check_declaration,
)
from bench.frontend.describe import declaration_text, descriptions
from hypothesis import given, settings
from hypothesis import strategies as st

from wind_tunnel import told_set

# Plain sentences: letters, digits without dots, spaces and light punctuation. No path, version or
# session value can be generated, so any such value in the export would come from the export itself.
_WORDS = st.text(alphabet="abcdefghijklmnopqrstuvwxyz ,;:()-", min_size=1, max_size=60)
_TEXT = _WORDS.map(lambda s: s.strip(" ") or "x").filter(
    lambda s: not re.search(r"\b(?:session|version)\b", s, re.IGNORECASE)
)
_DESCRIPTION = st.one_of(st.just(""), _TEXT).map(lambda s: s[:DESCRIPTION_MAX].strip(" "))
_NAMES = st.lists(
    st.from_regex(r"[a-z][a-z0-9_]{0,8}", fullmatch=True)
    .filter(lambda n: n not in {"t", "abs", "min", "max", "len"})
    .filter(lambda n: n not in {"math", "range"} and not n.isupper()),
    min_size=1,
    max_size=8,
    unique=True,
)
_BOUNDS = st.tuples(st.integers(min_value=-50, max_value=50), st.integers(min_value=1, max_value=50)).map(
    lambda p: (float(p[0]), float(p[0] + p[1]))
)


@st.composite
def declarations(draw) -> Declaration:
    names = draw(_NAMES)
    n_knobs = draw(st.integers(min_value=1, max_value=len(names)))
    knobs = []
    for name in names[:n_knobs]:
        low, high = draw(_BOUNDS)
        description = draw(_DESCRIPTION)
        if draw(st.booleans()):
            knobs.append(NumberKnob(name, low, high, description))
        else:
            seconds = float(draw(st.integers(min_value=1, max_value=9)))
            knobs.append(FunctionKnob(name, low, high, (0.0, seconds), seconds, description))
    measurements = tuple(
        Measurement(
            f"m_{name}",
            draw(st.sampled_from(["1", "m", "s"])),
            draw(st.sampled_from(["scalar", "series"])),
            draw(st.sampled_from([(), ("not_shedding",), ("a", "b")])),
        )
        for name in names[n_knobs:] or ["x"]
    )
    return Declaration(
        knobs=tuple(knobs),
        measurements=measurements,
        picture=draw(st.sampled_from(["image/png", "image/gif", "image/webp"])),
        budget=draw(st.integers(min_value=1, max_value=99)),
        fake=False,
        goal=draw(_TEXT),
        measured_by=draw(_TEXT),
    )


class _Scan:
    def __init__(self, decl: Declaration) -> None:
        self._decl = decl

    def declaration(self) -> Declaration:
        return self._decl


def _export(decl: Declaration) -> tuple[bytes, bytes]:
    """Run the export command twice for `decl`; return the bytes of both files."""
    with (
        tempfile.TemporaryDirectory() as folder,
        mock.patch.object(told_set, "scan_adapter", lambda: _Scan(decl)),
    ):
        a, b = Path(folder) / "first_export.txt", Path(folder) / "second_export.txt"
        told_set.main(["--out", str(a)])
        told_set.main(["--out", str(b)])
        return a.read_bytes(), b.read_bytes()


@given(declarations())
@settings(max_examples=150, deadline=None)
def test_p13_export_equals_declaration_text(decl: Declaration) -> None:
    """**Validates: Requirements 1.1, 2.1, 2.2, 2.3, 2.4**"""
    check_declaration(decl)
    first, second = _export(decl)
    assert first == second
    text = first.decode("utf-8")
    assert text == declaration_text(decl) + "\n"
    assert text.endswith("\n") and not text.endswith("\n\n")
    for tool in ("register_hypothesis", "run_experiment"):
        assert descriptions(decl)[tool].endswith(text[:-1])
    assert "first_export" not in text and "second_export" not in text
    assert not re.search(r"\d+\.\d+\.\d+", text)
    assert not re.search(r"(?:^|\s)(?:/|~/|\.\./)\w", text)
    assert not re.search(r"\b(?:session|version)\b", text, re.IGNORECASE)
    for knob in decl.knobs:
        assert knob.name in text
        if knob.description:
            assert knob.description in text
