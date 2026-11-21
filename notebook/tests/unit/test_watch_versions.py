"""The watch's versions (task 25.5; Requirements 23.6, 20.1, 20.2, 7.3) on the fake fixture session: a record
is fed to the watch line by line; nothing here is a result."""

import json
import shutil
from pathlib import Path

import pytest
from bench.record.canonical import canonical_json
from bench.record.chain import BLOB_DIR, LOG_NAME, entry_hash

from fixtures.choices import write_app
from fixtures.session import accepted_session
from notebook import choices, layouts, records, scan, text
from notebook.watch.versions import Watch

ROOT = Path(__file__).resolve().parents[3]
CONFIGS = [
    ROOT / "body-lab" / "adapter" / "scan_sources.toml",
    ROOT / "wind-tunnel" / "adapter" / "scan_sources.toml",
]
STOP_LIST = ROOT / ".kiro" / "blind-scan" / "stop-list.txt"
ONE = (
    "[fake]\nframes = 1\nrows = 1\ncolumns = 1\ngap = 0\ninterval = 200\n"
    'source = "test fixture: one 8 x 8 picture"\n'
)
THREE = (
    "[fake]\nframes = 9\nrows = 3\ncolumns = 3\ngap = 0\ninterval = 200\n"
    'source = "test fixture: three by three"\n'
)


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    root = tmp_path_factory.mktemp("versions")
    fixture = accepted_session(root / "lab")
    (full,) = records.load(fixture.sessions, allow_fake=True)
    (app,) = choices.load_apps([write_app(root / "app")], [full]).apps
    scanner = scan.load(CONFIGS, STOP_LIST)
    entries = [json.loads(line) for line in (fixture.sealed / LOG_NAME).read_bytes().splitlines()]
    return fixture, app, scanner, entries


def _rechain(entries):
    prev, out = "0" * 64, []
    for entry in entries:
        entry = {**{k: v for k, v in entry.items() if k != "hash"}, "prev": prev}
        entry["hash"] = entry_hash(entry)
        prev = entry["hash"]
        out.append(entry)
    return out


def _state(made, tmp_path, entries):
    """A record folder at the bench with no line written yet."""
    fixture = made[0]
    folder = tmp_path / "state" / fixture.sealed.name
    folder.mkdir(parents=True)
    shutil.copytree(fixture.sealed / BLOB_DIR, folder / BLOB_DIR)
    (folder / LOG_NAME).write_bytes(b"")
    lines = [canonical_json(e) + b"\n" for e in entries]
    return folder, lines


def _feed(folder, lines, upto):
    (folder / LOG_NAME).write_bytes(b"".join(lines[:upto]))


def _watch(made, folder, table=ONE):
    _, app, scanner, _ = made
    return Watch(folder, app, layouts.parse(table, "test fixture"), scanner, allow_fake=True)


def test_every_pass_that_accepts_entries_makes_the_next_version(made, tmp_path):
    folder, lines = _state(made, tmp_path, made[3])
    watch = _watch(made, folder)
    assert watch.poll().number == 0
    numbers = []
    for upto in range(1, len(lines) + 1):
        _feed(folder, lines, upto)
        version = watch.poll()
        assert version.stop is None
        numbers.append(version.number)
        assert watch.poll().number == version.number  # a pass with nothing new makes no version
    assert numbers == list(range(1, len(lines) + 1))
    assert "at the bench" in version.page.decode()


def test_several_entries_in_one_pass_make_one_version(made, tmp_path):
    folder, lines = _state(made, tmp_path, made[3])
    watch = _watch(made, folder)
    _feed(folder, lines, 4)
    assert watch.poll().number == 1
    _feed(folder, lines, len(lines))
    assert watch.poll().number == 2


def test_a_term_in_bench_text_stops_the_watch_and_is_never_shown(made, tmp_path):
    scanner = made[2]
    term = sorted(t[0] for t in scanner.terms if len(t) == 1 and t[0].isalpha())[0]
    entries = [json.loads(json.dumps(e)) for e in made[3]]
    seq = next(e["seq"] for e in entries if e["kind"] == "verdict")
    entries[seq - 1]["body"]["verdict"] = term
    folder, lines = _state(made, tmp_path, _rechain(entries))
    watch = _watch(made, folder)
    _feed(folder, lines, seq - 1)
    good = watch.poll()
    assert good.stop is None
    _feed(folder, lines, len(lines))
    stopped = watch.poll()
    assert stopped.number == good.number and stopped.page == good.page
    assert stopped.stop is not None
    assert (stopped.stop.line, stopped.stop.problem) == (seq, text.WATCH_FOUND_TERM)
    assert term not in str(stopped.stop) and term.encode() not in stopped.page
    # no new version, and nothing more is read
    assert watch.poll() == stopped
    assert watch.reader.last_seq == len(lines)


def test_a_picture_that_does_not_divide_into_the_layout_stops_the_watch(made, tmp_path):
    folder, lines = _state(made, tmp_path, made[3])
    seq = next(e["seq"] for e in made[3] if e["kind"] == "trial")
    watch = _watch(made, folder, THREE)
    _feed(folder, lines, seq - 1)
    good = watch.poll()
    assert good.stop is None
    _feed(folder, lines, seq)
    stopped = watch.poll()
    assert stopped.number == good.number and stopped.page == good.page
    assert (stopped.stop.line, stopped.stop.problem) == (seq, text.WATCH_FOUND_PICTURE)


def test_a_clean_record_never_stops(made, tmp_path):
    folder, lines = _state(made, tmp_path, made[3])
    watch = _watch(made, folder)
    _feed(folder, lines, len(lines))
    version = watch.poll()
    assert version.stop is None and version.number == 1 and watch.reader.stop is None


def test_a_reader_stop_keeps_the_last_version(made, tmp_path):
    folder, lines = _state(made, tmp_path, made[3])
    watch = _watch(made, folder)
    _feed(folder, lines, 3)
    good = watch.poll()
    (folder / LOG_NAME).write_bytes(b"".join(lines[:3]) + b"not json\n")
    stopped = watch.poll()
    assert stopped.number == good.number and stopped.page == good.page
    assert (stopped.stop.line, stopped.stop.problem) == (4, text.WATCH_NOT_JSON)


def test_a_record_that_does_not_make_a_page_stops_the_watch_at_the_newest_entry(made, tmp_path):
    entries = [json.loads(json.dumps(e)) for e in made[3]]
    seq = next(e["seq"] for e in entries if e["kind"] == "verdict")
    # a second start entry: well formed and chained, but the record cannot replay with it
    entries[seq - 1] = {**entries[seq - 1], "kind": "start", "body": entries[0]["body"]}
    folder, lines = _state(made, tmp_path, _rechain(entries))
    watch = _watch(made, folder)
    _feed(folder, lines, seq - 1)
    good = watch.poll()
    assert good.stop is None
    _feed(folder, lines, seq)
    stopped = watch.poll()
    assert stopped.number == good.number and stopped.page == good.page
    assert (stopped.stop.line, stopped.stop.problem) == (seq, text.WATCH_NO_PAGE)
