"""The reduced record copy and its check, on a sealed record of the bench's Store (Requirement 6; design 3.6).

Task 10.1. The record has a start, a register, an experiment, a trial with a picture, a snapshot after the
experiment, a verdict that references the design blob, and an end snapshot that references the three spec
files. Blobs referenced only by the end snapshot are removed in the copy; the design blob stays, because the
verdict references it.
"""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import pytest
from bench.record.chain import BLOB_DIR, LOG_NAME

from build_from_spec.reduced import ReducedError, Removed, check_reduced, plan, reduce
from support import seal_record


def make_source(root: Path) -> tuple[Path, dict[str, str]]:
    """A sealed record under root/sessions/s1, and the blob names by label."""
    names: dict[str, str] = {}
    (root / "sessions").mkdir(parents=True)

    def build(store):
        def put(label: str, data: bytes, author: str, media: str) -> dict[str, str]:
            ref = store.put_blob(data, author, media)
            names[label] = ref["blob"]
            return ref

        frozen = put("frozen", b"### H1: about\n\nWHEN a, THE b SHALL c.\n", "dr-kiro", "text/markdown")
        picture = put("picture", b"\x89PNG fixture picture", "bench", "image/png")
        experiment_file = put("experiment", b"print('experiment')\n", "dr-kiro", "text/x-python")
        requirements = put("requirements", b"# Requirements\n", "dr-kiro", "text/markdown")
        design = put("design", b"# Design\n", "dr-kiro", "text/markdown")
        tasks = put("tasks", b"# Tasks\n", "dr-kiro", "text/markdown")
        return [
            ("start", {"application": "fake", "session": "s1"}),
            ("register", {"hypothesis": "H1", "frozen": frozen}),
            ("experiment", {"experiment": "E1", "hypothesis": "H1", "files": {"e1.py": experiment_file}}),
            ("trial", {"trial": "T1", "experiment": "E1", "picture": picture, "measurements": {"x": 0.5}}),
            ("snapshot", {"for": "experiment", "experiment": "E1", "files": {}}),
            (
                "verdict",
                {"hypothesis": "H1", "text": {"author": "dr-kiro", "text": "it holds"}, "design": design},
            ),
            (
                "snapshot",
                {"for": "end", "files": {"requirements": requirements, "design": design, "tasks": tasks}},
            ),
        ]

    folder = seal_record(root / "sessions" / "s1", build)
    return folder, names


def lines_of(log: Path) -> list[bytes]:
    return log.read_bytes().split(b"\n")[:-1]


def write_lines(log: Path, lines: list[bytes]) -> None:
    log.write_bytes(b"".join(line + b"\n" for line in lines))


def kind_of(line: bytes) -> str:
    return json.loads(line)["kind"]


@pytest.fixture
def source(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    return make_source(tmp_path)


@pytest.fixture
def copy(tmp_path: Path, source) -> Path:
    record, _ = source
    target = tmp_path / "copy"
    reduce(record, target)
    return target


def test_every_line_that_is_not_a_snapshot_is_kept_byte_for_byte_and_in_order(tmp_path, source):
    record, _ = source
    source_lines = lines_of(record / LOG_NAME)
    expected = [line for line in source_lines if kind_of(line) != "snapshot"]
    target = tmp_path / "copy"
    reduce(record, target)
    assert lines_of(target / LOG_NAME) == expected
    assert (target / LOG_NAME).read_bytes() == b"".join(line + b"\n" for line in expected)


def test_only_blobs_referenced_by_kept_entries_are_kept(tmp_path, source):
    record, names = source
    target = tmp_path / "copy"
    reduce(record, target)
    kept = {p.name for p in (target / BLOB_DIR).iterdir()}
    assert kept == {names["frozen"], names["picture"], names["experiment"], names["design"]}
    for name in kept:
        assert (target / BLOB_DIR / name).read_bytes() == (record / BLOB_DIR / name).read_bytes()
    assert names["requirements"] not in kept
    assert names["tasks"] not in kept


def test_the_copy_has_the_source_layout(tmp_path, source):
    record, _ = source
    target = tmp_path / "copy"
    reduce(record, target)
    assert sorted(p.name for p in target.iterdir()) == sorted([LOG_NAME, BLOB_DIR])


def test_removed_entries_are_the_snapshots_in_log_order(tmp_path, source):
    record, _ = source
    entries = [json.loads(line) for line in lines_of(record / LOG_NAME)]
    expected = tuple(Removed(e["seq"], e["hash"]) for e in entries if e["kind"] == "snapshot")
    assert [r.seq for r in expected] == [5, 7]
    assert reduce(record, tmp_path / "copy") == expected


def test_reduce_refuses_an_existing_target(tmp_path, source):
    record, _ = source
    target = tmp_path / "copy"
    target.mkdir()
    with pytest.raises(ReducedError, match="already exists"):
        reduce(record, target)


def test_plan_refuses_a_source_that_does_not_verify(source):
    record, _ = source
    log = record / LOG_NAME
    log.write_bytes(log.read_bytes().replace(b'"seq":3', b'"seq":4', 1))
    with pytest.raises(ReducedError, match="log.jsonl line 3: seq is 4, expected 3"):
        plan(record)


def test_the_check_accepts_the_copy(source, copy):
    record, _ = source
    assert check_reduced(copy, record) == []


# Each mutation changes the copy in one way. Arguments: the copy, the source record, the blob names.


def _changed_kept_line(copy: Path, record: Path, names: dict[str, str]) -> None:
    lines = lines_of(copy / LOG_NAME)
    lines[1] = lines[1] + b" "
    write_lines(copy / LOG_NAME, lines)


def _removed_non_snapshot_line(copy: Path, record: Path, names: dict[str, str]) -> None:
    lines = lines_of(copy / LOG_NAME)
    del lines[1]
    write_lines(copy / LOG_NAME, lines)


def _kept_snapshot_entry(copy: Path, record: Path, names: dict[str, str]) -> None:
    lines = lines_of(copy / LOG_NAME)
    snapshot = next(line for line in lines_of(record / LOG_NAME) if kind_of(line) == "snapshot")
    lines.insert(4, snapshot)
    write_lines(copy / LOG_NAME, lines)


def _extra_blob(copy: Path, record: Path, names: dict[str, str]) -> None:
    (copy / BLOB_DIR / hashlib.sha256(b"extra").hexdigest()).write_bytes(b"extra")


def _missing_blob(copy: Path, record: Path, names: dict[str, str]) -> None:
    (copy / BLOB_DIR / names["picture"]).unlink()


def _changed_blob(copy: Path, record: Path, names: dict[str, str]) -> None:
    (copy / BLOB_DIR / names["picture"]).write_bytes(b"other bytes")


def _extra_file(copy: Path, record: Path, names: dict[str, str]) -> None:
    (copy / "notes.md").write_text("notes\n", encoding="utf-8")


FAILURES: list[tuple[str, Callable[..., None], str]] = [
    ("changed kept line", _changed_kept_line, "log.jsonl line 2: differs from source entry seq 2"),
    ("removed non-snapshot line", _removed_non_snapshot_line, "log.jsonl line 2"),
    ("kept snapshot entry", _kept_snapshot_entry, "log.jsonl line 5: snapshot entry seq 5 is kept"),
    ("extra blob", _extra_blob, f"blobs/{hashlib.sha256(b'extra').hexdigest()}: not referenced"),
    ("missing blob", _missing_blob, "blobs/"),
    ("changed blob", _changed_blob, "blobs/"),
    ("extra file", _extra_file, "notes.md: not part of a reduced copy"),
]


@pytest.mark.parametrize(("label", "mutate", "named"), FAILURES, ids=[f[0] for f in FAILURES])
def test_each_change_to_the_copy_is_found_and_named(source, copy, label, mutate, named):
    record, names = source
    mutate(copy, record, names)
    problems = check_reduced(copy, record)
    assert problems, f"{label}: the change was not found"
    assert any(named in problem for problem in problems), problems


def test_a_missing_blob_is_named_by_its_name(source, copy):
    record, names = source
    _missing_blob(copy, record, names)
    assert check_reduced(copy, record) == [f"blobs/{names['picture']}: missing"]


def test_a_copy_without_its_log_is_named(source, copy):
    record, _ = source
    (copy / LOG_NAME).unlink()
    assert check_reduced(copy, record) == ["log.jsonl: missing"]


def test_a_copy_that_is_not_a_folder_is_named(tmp_path, source):
    record, _ = source
    missing = tmp_path / "nowhere"
    assert check_reduced(missing, record) == [f"{missing}: not a folder"]


def test_a_copy_whose_log_has_no_final_newline_is_named(source, copy):
    record, _ = source
    log = copy / LOG_NAME
    log.write_bytes(log.read_bytes().rstrip(b"\n"))
    assert check_reduced(copy, record) == ["log.jsonl: the last line has no newline"]
