"""The watch reader (task 25.1) on fixture records: fake application, `tmp_path`, nothing here is a result."""

import json
from pathlib import Path
from typing import Any

import pytest
from bench.record.canonical import canonical_json
from bench.record.chain import BLOB_DIR, LOG_NAME, entry_hash
from hypothesis import find
from hypothesis import strategies as st

from fixtures.synth import SynthRecord, records
from notebook import text
from notebook.errors import NotebookError
from notebook.watch.reader import Reader


@pytest.fixture(scope="module")
def synth() -> SynthRecord:
    return find(
        records(rounds=st.just(2), endings=("table",)),
        lambda r: len(r.entries) >= 10 and len(r.kinds("snapshot")) >= 1,
    )


def _lines(synth: SynthRecord) -> list[bytes]:
    return [canonical_json(e) + b"\n" for e in synth.entries]


def _folder(tmp_path: Path, synth: SynthRecord, lines: list[bytes] | None = None) -> Path:
    folder = tmp_path / "state" / synth.session
    (folder / BLOB_DIR).mkdir(parents=True)
    for digest, data in synth.blobs.items():
        (folder / BLOB_DIR / digest).write_bytes(data)
    (folder / LOG_NAME).write_bytes(b"".join(_lines(synth) if lines is None else lines))
    return folder


def _rechain(entries: list[dict[str, Any]]) -> list[bytes]:
    """Valid chain over altered entries, so only the check under test can refuse a line."""
    prev, out = "0" * 64, []
    for number, entry in enumerate(entries, start=1):
        entry = {**{k: v for k, v in entry.items() if k != "hash"}, "seq": number, "prev": prev}
        entry["hash"] = entry_hash(entry)
        prev = entry["hash"]
        out.append(canonical_json(entry) + b"\n")
    return out


def test_a_complete_record_is_accepted_entry_by_entry(tmp_path: Path, synth: SynthRecord) -> None:
    reader = Reader(_folder(tmp_path, synth))
    assert reader.poll() == synth.entries
    assert reader.stop is None
    assert reader.poll() == []


def test_a_half_written_last_line_is_not_returned(tmp_path: Path, synth: SynthRecord) -> None:
    lines = _lines(synth)
    folder = _folder(tmp_path, synth, lines[:-1] + [lines[-1][:-1]])
    reader = Reader(folder)
    assert reader.poll() == synth.entries[:-1]
    assert reader.stop is None
    # the same half line with half its bytes, then the full line
    (folder / LOG_NAME).write_bytes(b"".join(lines[:-1]) + lines[-1][:20])
    assert reader.poll() == []
    (folder / LOG_NAME).write_bytes(b"".join(lines))
    assert reader.poll() == synth.entries[-1:]


@pytest.mark.parametrize("cut", [1, 7, 40])
def test_reading_in_two_passes_gives_the_same_entries(tmp_path: Path, synth: SynthRecord, cut: int) -> None:
    data = b"".join(_lines(synth))
    folder = _folder(tmp_path, synth, [data[: len(data) // cut + 3]])
    reader = Reader(folder)
    first = reader.poll()
    (folder / LOG_NAME).write_bytes(data)
    assert first + reader.poll() == synth.entries


def test_a_flipped_byte_stops_at_its_line(tmp_path: Path, synth: SynthRecord) -> None:
    lines = _lines(synth)
    bad = lines[4].replace(b'"seq":5', b'"seq":5 ', 1)
    folder = _folder(tmp_path, synth, lines[:4] + [bad] + lines[5:])
    reader = Reader(folder)
    assert reader.poll() == synth.entries[:4]
    assert (reader.stop.line, reader.stop.problem) == (5, text.WATCH_BAD_FORMAT)
    assert reader.poll() == []


def test_not_json_stops_at_its_line(tmp_path: Path, synth: SynthRecord) -> None:
    lines = _lines(synth)
    reader = Reader(_folder(tmp_path, synth, lines[:2] + [b"{oops\n"] + lines[3:]))
    assert len(reader.poll()) == 2
    assert (reader.stop.line, reader.stop.problem) == (3, text.WATCH_NOT_JSON)
    assert "oops" not in str(reader.stop)


def test_a_changed_hash_stops_at_its_line(tmp_path: Path, synth: SynthRecord) -> None:
    entries = [dict(e) for e in synth.entries]
    entries[2] = {**entries[2], "hash": "1" * 64}
    lines = [canonical_json(e) + b"\n" for e in entries]
    reader = Reader(_folder(tmp_path, synth, lines))
    assert len(reader.poll()) == 2
    assert (reader.stop.line, reader.stop.problem) == (3, text.WATCH_HASH_MISMATCH)


def test_a_wrong_seq_stops_at_its_line(tmp_path: Path, synth: SynthRecord) -> None:
    entries = [dict(e) for e in synth.entries]
    entries[3]["seq"] = 9
    entries[3]["hash"] = entry_hash({k: v for k, v in entries[3].items() if k != "hash"})
    lines = [canonical_json(e) + b"\n" for e in entries]
    reader = Reader(_folder(tmp_path, synth, lines))
    assert len(reader.poll()) == 3
    assert (reader.stop.line, reader.stop.problem) == (4, text.WATCH_OUT_OF_SEQUENCE)


def test_a_wrong_prev_stops_at_its_line(tmp_path: Path, synth: SynthRecord) -> None:
    entries = [dict(e) for e in synth.entries]
    entries[5]["prev"] = "2" * 64
    entries[5]["hash"] = entry_hash({k: v for k, v in entries[5].items() if k != "hash"})
    lines = [canonical_json(e) + b"\n" for e in entries]
    reader = Reader(_folder(tmp_path, synth, lines))
    assert len(reader.poll()) == 5
    assert (reader.stop.line, reader.stop.problem) == (6, text.WATCH_PREV_MISMATCH)


def test_a_key_set_that_does_not_fit_the_kind_stops_at_its_line(tmp_path: Path, synth: SynthRecord) -> None:
    entries = [json.loads(json.dumps(e)) for e in synth.entries]
    entries[1]["body"]["extra"] = 1
    reader = Reader(_folder(tmp_path, synth, _rechain(entries)))
    assert len(reader.poll()) == 1
    assert (reader.stop.line, reader.stop.problem) == (2, text.WATCH_BAD_FORMAT)


def test_an_entry_key_set_and_an_unknown_kind_stop(tmp_path: Path, synth: SynthRecord) -> None:
    lines = _lines(synth)
    entry = json.loads(lines[1])
    entry["more"] = 1
    reader = Reader(_folder(tmp_path, synth, lines[:1] + [canonical_json(entry) + b"\n"]))
    reader.poll()
    assert (reader.stop.line, reader.stop.problem) == (2, text.WATCH_BAD_FORMAT)
    entries = [json.loads(json.dumps(e)) for e in synth.entries]
    entries[1]["kind"] = "nonsense"
    reader = Reader(_folder(tmp_path / "b", synth, _rechain(entries)))
    reader.poll()
    assert (reader.stop.line, reader.stop.problem) == (2, text.WATCH_BAD_FORMAT)


def test_a_missing_blob_stops_at_its_line(tmp_path: Path, synth: SynthRecord) -> None:
    folder = _folder(tmp_path, synth)
    first = next(i for i, e in enumerate(synth.entries) if e["kind"] == "snapshot")
    digest = synth.entries[first]["body"]["files"]["design"]["blob"]
    (folder / BLOB_DIR / digest).unlink()
    reader = Reader(folder)
    assert len(reader.poll()) == first
    assert (reader.stop.line, reader.stop.problem) == (first + 1, text.WATCH_BLOB_MISSING)


def test_a_blob_that_does_not_match_its_name_stops(tmp_path: Path, synth: SynthRecord) -> None:
    folder = _folder(tmp_path, synth)
    first = next(i for i, e in enumerate(synth.entries) if e["kind"] == "snapshot")
    digest = synth.entries[first]["body"]["files"]["design"]["blob"]
    (folder / BLOB_DIR / digest).write_bytes(b"changed")
    reader = Reader(folder)
    reader.poll()
    assert (reader.stop.line, reader.stop.problem) == (first + 1, text.WATCH_BLOB_CHANGED)


def test_dot_names_in_blobs_and_other_files_are_ignored_and_nothing_is_written(
    tmp_path: Path, synth: SynthRecord
) -> None:
    folder = _folder(tmp_path, synth)
    (folder / BLOB_DIR / ".tmp-partial").write_bytes(b"x")
    (folder / "builder.log").write_text("not read")
    before = sorted((p.name, p.stat().st_mtime_ns) for p in folder.rglob("*"))
    reader = Reader(folder)
    assert reader.poll() == synth.entries
    assert sorted((p.name, p.stat().st_mtime_ns) for p in folder.rglob("*")) == before
    assert not (folder / ".lock").exists()


def test_a_missing_log_fails(tmp_path: Path) -> None:
    with pytest.raises(NotebookError):
        Reader(tmp_path).poll()
