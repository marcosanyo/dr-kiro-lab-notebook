# Feature: build-from-spec, Property 8: Copy check accepts the copy and finds every change
"""For any sealed record, `check_reduced(reduce(source), source)` reports nothing. For any one change to the
copy (a kept line changed, a non-snapshot line removed, a snapshot line inserted, a blob added, a kept blob
deleted, a kept blob's bytes changed), the check reports a problem that names the changed line or blob.
A change that the record has nothing to act on for falls back to an added blob.

**Validates: Requirements 6.3**
"""

import hashlib
import json
import tempfile
from pathlib import Path

from bench.record.chain import BLOB_DIR, LOG_NAME
from hypothesis import given, settings
from hypothesis import strategies as st

from build_from_spec.reduced import check_reduced, reduce
from support import record_specs, write_record

CHANGES = ("change-line", "remove-line", "insert-snapshot", "extra-blob", "missing-blob", "change-blob")


@st.composite
def changes(draw):
    return (
        draw(st.sampled_from(CHANGES)),
        draw(st.integers(min_value=0, max_value=1000)),
        draw(st.binary(min_size=1, max_size=8)),
    )


def lines_of(path: Path) -> list[bytes]:
    return path.read_bytes().split(b"\n")[:-1]


def write_lines(path: Path, lines: list[bytes]) -> None:
    path.write_bytes(b"".join(line + b"\n" for line in lines))


def apply_change(change, copy: Path, source: Path) -> None:
    """Change the copy in place, in the way named by `change`."""
    kind, position, data = change
    lines = lines_of(copy / LOG_NAME)
    snapshots = [line for line in lines_of(source / LOG_NAME) if json.loads(line)["kind"] == "snapshot"]
    blobs = sorted(p.name for p in (copy / BLOB_DIR).iterdir())
    if kind == "change-line" and lines:
        index = position % len(lines)
        lines[index] = lines[index] + b" "
        write_lines(copy / LOG_NAME, lines)
    elif kind == "remove-line" and lines:
        del lines[position % len(lines)]
        write_lines(copy / LOG_NAME, lines)
    elif kind == "insert-snapshot" and snapshots:
        lines.insert(position % (len(lines) + 1), snapshots[position % len(snapshots)])
        write_lines(copy / LOG_NAME, lines)
    elif kind == "missing-blob" and blobs:
        (copy / BLOB_DIR / blobs[position % len(blobs)]).unlink()
    elif kind == "change-blob" and blobs:
        path = copy / BLOB_DIR / blobs[position % len(blobs)]
        path.write_bytes(path.read_bytes() + data)
    else:  # extra-blob, or nothing to act on in this record
        extra = b"extra-blob:" + data
        (copy / BLOB_DIR / hashlib.sha256(extra).hexdigest()).write_bytes(extra)


@settings(max_examples=100, deadline=None)
@given(record_specs(), changes())
def test_copy_check_accepts_the_copy_and_finds_every_change(spec, change):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "sessions").mkdir()
        source = write_record(root / "sessions" / "s1", spec)
        copy = root / "copy"
        reduce(source, copy)
        assert check_reduced(copy, source) == []

        apply_change(change, copy, source)

        problems = check_reduced(copy, source)
        assert problems, f"the {change[0]} change was not found"
        assert all(problem.startswith((f"{LOG_NAME} line ", f"{BLOB_DIR}/")) for problem in problems), (
            problems
        )
