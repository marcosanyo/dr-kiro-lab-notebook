# Feature: build-from-spec, Property 10: Run file round trip
"""For any run file content (any setup, relied-on ids made of any characters, the null markers, any number of
turns), reading the written run file gives equal content, and writing it twice gives the same bytes.

**Validates: Requirements 14.2**
"""

import tempfile
from pathlib import Path

from hypothesis import given, settings

from build_from_spec.runfile import read_run_file, run_file_texts
from support import run_file_contents


@settings(max_examples=100)
@given(run_file_contents())
def test_run_file_round_trip(data):
    with tempfile.TemporaryDirectory() as folder:
        first = Path(folder) / "first.run.json"
        second = Path(folder) / "second.run.json"
        text, _ = run_file_texts(data)
        first.write_text(text, encoding="utf-8", newline="")
        assert read_run_file(first) == data

        again, _ = run_file_texts(read_run_file(first))
        second.write_text(again, encoding="utf-8", newline="")
        assert first.read_bytes() == second.read_bytes()
