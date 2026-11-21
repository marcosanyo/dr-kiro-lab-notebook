"""Property test of the watch reader: the complete, valid prefix (task 25.2).
The records are fixtures from `tests/fixtures/synth.py` (fake application; no number here is a result). The
blobs are on disk before the first write, as the bench writes a blob before the line that names it. The log is
then written in successive pieces, cut anywhere, including inside a line, and `poll()` is called after each.
"""

# Feature: lab-notebook, Property 18: The reader shows exactly the complete, valid prefix
# **Validates: Requirements 23.4, 23.5, 23.12**
import tempfile
from pathlib import Path

from bench.record.canonical import canonical_json
from bench.record.chain import BLOB_DIR, LOG_NAME
from hypothesis import HealthCheck, event, given, settings
from hypothesis import strategies as st

from fixtures.synth import SynthRecord, records
from notebook.watch.reader import Reader

_SETTINGS = settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])


def _folder(root: Path, synth: SynthRecord) -> Path:
    folder = root / synth.session
    (folder / BLOB_DIR).mkdir(parents=True)
    for digest, data in synth.blobs.items():
        (folder / BLOB_DIR / digest).write_bytes(data)
    (folder / LOG_NAME).write_bytes(b"")
    return folder


@st.composite
def _cuts(draw: st.DrawFn, size: int) -> list[int]:
    """Sorted cut points inside the bytes; pieces may be empty."""
    return sorted(draw(st.lists(st.integers(0, size), max_size=30)))


def _feed(reader: Reader, folder: Path, data: bytes, cuts: list[int]) -> list[tuple[int, list[dict]]]:
    """Append the pieces one at a time; after each, the bytes written so far and what `poll()` returned."""
    bounds = [0, *cuts, len(data)]
    seen = []
    with (folder / LOG_NAME).open("ab") as log:
        for start, end in zip(bounds, bounds[1:], strict=False):
            log.write(data[start:end])
            log.flush()
            seen.append((end, reader.poll()))
    return seen


@given(st.data())
@_SETTINGS
def test_the_reader_shows_exactly_the_complete_prefix(data: st.DataObject) -> None:
    synth = data.draw(records())
    lines = [canonical_json(e) + b"\n" for e in synth.entries]
    raw = b"".join(lines)
    cuts = data.draw(_cuts(len(raw)))
    ends = [sum(map(len, lines[: n + 1])) for n in range(len(lines))]
    with tempfile.TemporaryDirectory() as tmp:
        folder = _folder(Path(tmp), synth)
        reader = Reader(folder)
        shown: list[dict] = []
        for written, accepted in _feed(reader, folder, raw, cuts):
            shown += accepted
            complete = sum(1 for end in ends if end <= written)
            # Exactly the complete lines so far, in order; a piece with no line end is never shown.
            assert shown == synth.entries[:complete]
            assert reader.stop is None
    event(f"{len(cuts)} cuts")


@given(st.data())
@_SETTINGS
def test_a_corrupted_complete_line_stops_the_reader_at_that_line(data: st.DataObject) -> None:
    synth = data.draw(records())
    lines = [canonical_json(e) + b"\n" for e in synth.entries]
    index = data.draw(st.integers(0, len(lines) - 1))
    position = data.draw(st.integers(0, len(lines[index]) - 2))  # never the line end
    bad = bytearray(lines[index])
    bad[position] ^= 1  # 0x0a is not reachable: 0x0b is not in a canonical line
    assert bad[position] != 0x0A
    raw = b"".join(lines[:index]) + bytes(bad) + b"".join(lines[index + 1 :])
    cuts = data.draw(_cuts(len(raw)))
    with tempfile.TemporaryDirectory() as tmp:
        folder = _folder(Path(tmp), synth)
        reader = Reader(folder)
        shown: list[dict] = []
        for _, accepted in _feed(reader, folder, raw, cuts):
            shown += accepted
            assert len(shown) <= index
        # Everything before the line, nothing from it on; the stop names exactly this line.
        assert shown == synth.entries[:index]
        assert reader.stop is not None
        assert reader.stop.line == index + 1
        assert reader.poll() == []
    event(f"line {'first' if index == 0 else 'later'}")
