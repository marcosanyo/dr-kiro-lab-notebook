import re
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from wind_tunnel_model.casegen import render_case
from wind_tunnel_model.settings import Settings

BASE = Settings.load()

knob_values = st.fixed_dictionaries(
    {
        "aspect": st.floats(min_value=0.5, max_value=3.0),
        "corner": st.floats(min_value=0.0, max_value=1.0),
        "splitter": st.floats(min_value=0.0, max_value=3.0),
        "angle": st.floats(min_value=0.0, max_value=30.0),
    }
)
reynolds_numbers = st.floats(min_value=10.0, max_value=1000.0)


def _files(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


# Feature: wind-tunnel, Property 11: Case generation is deterministic and complete
# **Validates: Requirements 6.6, 6.7, 10.1, 10.2**
@settings(max_examples=100, deadline=None)
@given(knobs=knob_values, reynolds=reynolds_numbers)
def test_case_generation_is_deterministic_and_complete(knobs, reynolds):
    s = BASE.with_reynolds(reynolds)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = render_case(knobs, s, root / "a")
        second = render_case(knobs, s, root / "b")
        a, b = _files(root / "a"), _files(root / "b")
        assert a == b
        assert [p.relative_to(root / "a") for p in first] == [p.relative_to(root / "b") for p in second]
        for name, data in a.items():
            assert b"@" not in data, name
        text = (root / "a/constant/transportProperties").read_text()
        match = re.search(r"nu\s+\[0 2 -1 0 0 0 0\]\s+(\S+);", text)
        assert match is not None
        assert float(match.group(1)) == s.flow.speed * s.flow.height / reynolds
