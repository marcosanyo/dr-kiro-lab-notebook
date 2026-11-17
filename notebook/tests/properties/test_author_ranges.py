# Feature: lab-notebook, Property 2: Author ranges cover each file and the bench accepts them
"""Property 2 (design "Correctness Properties").

For any list of segments, `ink.join` returns ranges that start at 0, are contiguous, end at the length of the
text, never join two different authors, and are accepted by `bench.scan.levels.sidecar_pieces`; every Dr. Kiro
segment's escaped form lies inside one `dr-kiro` range, and every other segment inside a `bench` range.

**Validates: Requirements 20.1, 20.3**
"""

import json
import tempfile
from pathlib import Path

from bench.scan.levels import AUTHOR_LEVEL, SIDECAR_SUFFIX, sidecar_pieces
from hypothesis import given, settings
from hypothesis import strategies as st

from notebook import ink
from notebook.ink import Ink, Segment

# Text a segment may hold: any character except the C0 controls the build refuses (design N6). Markup is
# written as is and gets the same alphabet: `<`, `&`, quotes, tab, line feed, carriage return, non-ASCII.
_ALPHABET = st.characters(blacklist_categories=("Cs",)).filter(
    lambda c: not ("\x00" <= c <= "\x1f") or c in "\t\n\r"
)
_TEXT = st.text(alphabet=_ALPHABET, max_size=12)
_SEGMENT = st.builds(Segment, text=_TEXT, ink=st.sampled_from(list(Ink)), source=st.just("property test"))
# The bench refuses a sidecar with no range, so a file needs at least one non-empty segment.
_SEGMENTS = st.lists(_SEGMENT, max_size=12).filter(lambda segs: any(s.text for s in segs))


def _containing(ranges: list[dict], start: int, end: int) -> dict:
    found = [r for r in ranges if r["start"] <= start and end <= r["end"]]
    assert len(found) == 1, f"[{start}, {end}) lies in {len(found)} ranges"
    return found[0]


@settings(max_examples=200, deadline=None)
@given(_SEGMENTS)
def test_author_ranges_cover_the_file_and_the_bench_accepts_them(segments: list[Segment]) -> None:
    text, ranges = ink.join(segments)

    # Start at 0, contiguous, end at the length of the text, no empty range.
    assert ranges[0]["start"] == 0
    assert ranges[-1]["end"] == len(text)
    for before, after in zip(ranges, ranges[1:], strict=False):
        assert before["end"] == after["start"]
        # Adjacent ranges are merged when they share an author, so neighbours always differ.
        assert before["author"] != after["author"]
    assert all(r["end"] > r["start"] for r in ranges)
    assert {r["author"] for r in ranges} <= {"bench", "dr-kiro"}

    # Each segment's escaped form lies inside one range of its scan author.
    position = 0
    for segment in segments:
        piece = ink.escape(segment)
        if not piece:
            continue
        end = position + len(piece)
        assert text[position:end] == piece
        expected = "dr-kiro" if segment.ink is Ink.DRKIRO else "bench"
        assert _containing(ranges, position, end)["author"] == expected
        position = end
    assert position == len(text)

    # The bench reads the same ranges from a sidecar written as the site writes it (design 12).
    with tempfile.TemporaryDirectory() as folder:
        page = Path(folder) / "page.html"
        page.write_text(text, encoding="utf-8", newline="")
        sidecar = page.with_name(page.name + SIDECAR_SUFFIX)
        body = json.dumps({"ranges": ranges}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        sidecar.write_text(body + "\n", encoding="utf-8")
        pieces = sidecar_pieces(page, text)

    assert [p.text for p in pieces] == [text[r["start"] : r["end"]] for r in ranges]
    assert [p.level for p in pieces] == [AUTHOR_LEVEL[r["author"]] for r in ranges]
    assert "".join(p.text for p in pieces) == text
