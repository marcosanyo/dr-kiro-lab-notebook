# Feature: build-from-spec, Property 7: Reduced copy keeps everything but the snapshots
"""For any sealed record with random entries of every kind, some sharing blobs, `reduce` writes a copy whose
log holds exactly the non-snapshot lines of the source, byte for byte and in order; whose blobs are exactly
the blobs referenced by kept entries, each byte-identical to the source blob; and whose returned removed list
is the snapshot entries' sequence numbers and hashes in log order. The copy holds no other file.

**Validates: Requirements 6.1, 6.2, 6.4**
"""

import json
import tempfile
from pathlib import Path

from bench.record.chain import BLOB_DIR, LOG_NAME, blob_refs
from hypothesis import given, settings

from build_from_spec.reduced import Removed, reduce
from support import record_specs, write_record


@settings(max_examples=100, deadline=None)
@given(record_specs())
def test_reduced_copy_keeps_everything_but_the_snapshots(spec):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "sessions").mkdir()
        source = write_record(root / "sessions" / "s1", spec)
        target = root / "copy"

        removed = reduce(source, target)

        source_lines = (source / LOG_NAME).read_bytes().split(b"\n")[:-1]
        entries = [json.loads(line) for line in source_lines]
        kept = [(line, e) for line, e in zip(source_lines, entries, strict=True) if e["kind"] != "snapshot"]
        assert (target / LOG_NAME).read_bytes() == b"".join(line + b"\n" for line, _ in kept)

        assert removed == tuple(Removed(e["seq"], e["hash"]) for e in entries if e["kind"] == "snapshot")

        kept_blobs = {ref["blob"] for _, e in kept for ref in blob_refs(e["body"])}
        present = {p.name for p in (target / BLOB_DIR).iterdir()}
        assert present == kept_blobs
        for name in kept_blobs:
            assert (target / BLOB_DIR / name).read_bytes() == (source / BLOB_DIR / name).read_bytes()

        assert sorted(p.name for p in target.iterdir()) == sorted([LOG_NAME, BLOB_DIR])
