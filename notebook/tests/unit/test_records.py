"""records.py on altered copies of a committed record in `tmp_path` (task 4.1). The copies are test inputs
and are never built into a site."""

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from bench.record.canonical import canonical_json
from bench.record.chain import GENESIS, entry_hash

from notebook import records
from notebook.errors import NotebookError

SESSIONS = Path(__file__).resolve().parents[3] / "sessions"
SOURCE = SESSIONS / "wind-tunnel" / "wt-002"


def _copy(tmp_path: Path) -> tuple[Path, Path]:
    sessions = tmp_path / "sessions"
    folder = sessions / "wind-tunnel" / "wt-002"
    shutil.copytree(SOURCE, folder)
    return sessions, folder


def _entries(folder: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (folder / "log.jsonl").read_text(encoding="utf-8").splitlines()]


def _rewrite(folder: Path, entries: list[dict[str, Any]]) -> None:
    """Write the entries back with a valid chain, so only the model's own checks can refuse them."""
    prev = GENESIS
    lines = []
    for entry in entries:
        without = {k: v for k, v in entry.items() if k != "hash"}
        without["prev"] = prev
        without["hash"] = entry_hash(without)
        prev = without["hash"]
        lines.append(canonical_json(without))
    (folder / "log.jsonl").write_bytes(b"\n".join(lines) + b"\n")


def _fails(sessions: Path, *needles: str) -> NotebookError:
    with pytest.raises(NotebookError) as caught:
        records.load(sessions)
    for needle in needles:
        assert needle in str(caught.value)
    return caught.value


def test_unaltered_copy_loads(tmp_path: Path) -> None:
    sessions, _ = _copy(tmp_path)
    (loaded,) = records.load(sessions)
    assert loaded.name == "sessions/wind-tunnel/wt-002"


def test_flipped_byte_in_a_log_line_fails_naming_the_line(tmp_path: Path) -> None:
    sessions, folder = _copy(tmp_path)
    log = folder / "log.jsonl"
    data = bytearray(log.read_bytes())
    second_line = data.index(b"\n") + 1
    index = data.index(b'"seq":2', second_line) + len('"seq":')
    data[index] = ord("3")
    log.write_bytes(bytes(data))
    _fails(sessions, "sessions/wind-tunnel/wt-002/log.jsonl line 2")


def test_flipped_byte_in_a_blob_fails_naming_the_blob(tmp_path: Path) -> None:
    sessions, folder = _copy(tmp_path)
    blob = sorted((folder / "blobs").iterdir())[0]
    data = bytearray(blob.read_bytes())
    data[len(data) // 2] ^= 0x01
    blob.write_bytes(bytes(data))
    _fails(sessions, f"sessions/wind-tunnel/wt-002/blobs/{blob.name}", "does not match its hash")


def test_missing_seal_fails(tmp_path: Path) -> None:
    sessions, folder = _copy(tmp_path)
    entries = _entries(folder)
    assert entries[-1]["kind"] == "seal"
    _rewrite(folder, entries[:-1])
    _fails(sessions, "sessions/wind-tunnel/wt-002", "not sealed")


def test_fake_trial_fails_unless_allowed(tmp_path: Path) -> None:
    sessions, folder = _copy(tmp_path)
    entries = _entries(folder)
    trial = next(e for e in entries if e["kind"] == "trial")
    trial["body"]["fake"] = True
    _rewrite(folder, entries)
    _fails(sessions, f"log.jsonl line {trial['seq']}", "fake")
    (loaded,) = records.load(sessions, allow_fake=True)
    assert loaded.trials[0].fake is True


def test_fake_declaration_fails(tmp_path: Path) -> None:
    sessions, folder = _copy(tmp_path)
    entries = _entries(folder)
    entries[0]["body"]["declaration"]["fake"] = True
    _rewrite(folder, entries)
    _fails(sessions, "log.jsonl line 1", "fake")


def test_extra_key_fails_naming_the_line(tmp_path: Path) -> None:
    sessions, folder = _copy(tmp_path)
    entries = _entries(folder)
    verdict = next(e for e in entries if e["kind"] == "verdict")
    verdict["body"]["extra"] = "x"
    _rewrite(folder, entries)
    _fails(sessions, f"log.jsonl line {verdict['seq']}", "extra keys ['extra']")


def test_unknown_entry_kind_fails(tmp_path: Path) -> None:
    sessions, folder = _copy(tmp_path)
    entries = _entries(folder)
    entries[1]["kind"] = "note"
    _rewrite(folder, entries)
    _fails(sessions, "log.jsonl line 2", "unknown entry kind 'note'")


def test_text_without_an_author_fails(tmp_path: Path) -> None:
    sessions, folder = _copy(tmp_path)
    entries = _entries(folder)
    verdict = next(e for e in entries if e["kind"] == "verdict")
    verdict["body"]["words"] = verdict["body"]["words"]["text"]
    _rewrite(folder, entries)
    _fails(sessions, f"log.jsonl line {verdict['seq']}", "words has no recorded author")


def test_start_entry_must_match_the_folder(tmp_path: Path) -> None:
    sessions, folder = _copy(tmp_path)
    renamed = folder.parent / "wt-009"
    folder.rename(renamed)
    _fails(sessions, "sessions/wind-tunnel/wt-009/log.jsonl line 1", "wind-tunnel/wt-002")


@pytest.mark.parametrize("place", ["sessions", "application", "record"])
def test_stray_file_fails(tmp_path: Path, place: str) -> None:
    sessions, folder = _copy(tmp_path)
    parent = {"sessions": sessions, "application": folder.parent, "record": folder}[place]
    (parent / "notes.txt").write_text("stray\n", encoding="utf-8")
    _fails(sessions, "notes.txt")
