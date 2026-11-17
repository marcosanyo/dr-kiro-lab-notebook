"""Property test of ink by author (task 7.7).

The records are fixtures from `tests/fixtures/synth.py`: every text Dr. Kiro writes carries author `dr-kiro`,
the bench's wording (refusal text, not-measured reasons, seal and failure reasons) carries `bench`, and blobs
carry their author in the reference. Each record is written, verified by the bench and loaded with
`allow_fake=True`. No number here is a recorded result.

Four parts:
- the model: every authored value of the record is read with the author it was recorded with, and its segment
  has that author's ink (`dr-kiro` -> Dr. Kiro's ink, `bench` -> pencil);
- the rendered table section: every cell in the ink of the snapshot file's author, every status word in the
  stamp ink (and nothing else), the reader's message spans in their authors' inks, bench values in pencil;
- the whole session page and the exception of Requirement 4.2 (design N29): Dr. Kiro's ink from a log entry
  is an authored value recorded with author `dr-kiro`, or one of Dr. Kiro's fixed words (the verdict word,
  Dr. Kiro's label of a prediction), which the bench records as plain strings; every fixed word is shown in
  Dr. Kiro's ink and is also a builder-level scan segment;
- an entry whose text field has no recorded author (a plain string, or an unknown author) fails the load,
  naming the record and the `log.jsonl` line.
"""

# Feature: lab-notebook, Property 3: Ink follows the recorded author
# **Validates: Requirements 4.1, 4.2**

import copy
import dataclasses
import tempfile
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from bench.record.chain import GENESIS, LOG_NAME, entry_hash
from bench.specfiles.discovered import Table
from hypothesis import event, given, settings
from hypothesis import strategies as st

from fixtures.synth import SynthRecord, design_text, records, table_rows, write_all
from notebook import records as notebook_records
from notebook import scan, tables, views
from notebook.choices import Choice, Choices
from notebook.errors import NotebookError
from notebook.ink import Authored, Ink
from notebook.layouts import Layout
from notebook.pages import session
from notebook.pages.photo import Pins
from notebook.pages.session import table_section
from notebook.records import Blob, RecordModel

INK_OF = {"dr-kiro": Ink.DRKIRO, "bench": Ink.PENCIL}
READER = "(the bench's table reader)"
# The synthetic pictures are one cell each (`fixtures.synth._picture`).
LAYOUT = Layout("fake", frames=1, rows=1, columns=1, gap=0, source="test fixture")


def _load(synth: SynthRecord) -> RecordModel:
    with tempfile.TemporaryDirectory() as tmp:
        (record,) = notebook_records.load(write_all(Path(tmp) / "sessions", [synth]), allow_fake=True)
    return record


# The record as written and as read


def _raw_authored(value: Any) -> Iterator[tuple[str, str]]:
    """Every authored value written in an entry body: `{"author", "text"}` objects as (author, text), blob
    references as (author, digest)."""
    if isinstance(value, dict):
        if set(value) == {"author", "text"}:
            yield value["author"], value["text"]
            return
        if set(value) == {"blob", "author", "media"}:
            yield value["author"], value["blob"]
            return
        for item in value.values():
            yield from _raw_authored(item)
    elif isinstance(value, list):
        for item in value:
            yield from _raw_authored(item)


def _model_authored(value: Any) -> Iterator[Authored | Blob]:
    """Every `Authored` and `Blob` reachable in the typed model (the raw entries are skipped)."""
    if isinstance(value, Authored | Blob):
        yield value
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        for f in dataclasses.fields(value):
            if f.name != "entries":
                yield from _model_authored(getattr(value, f.name))
    elif isinstance(value, tuple | list):
        for item in value:
            yield from _model_authored(item)


def _key(item: Authored | Blob) -> tuple[str, str]:
    return (item.author, item.digest) if isinstance(item, Blob) else (item.author, item.text)


def _assert_model(synth: SynthRecord, record: RecordModel) -> None:
    raw = Counter(a for e in synth.entries for a in _raw_authored(e["body"]))
    found = list(_model_authored(record))
    model = Counter(_key(item) for item in found)
    # Every recorded authored value is read, with the author it was recorded with.
    assert not raw - model
    # What the model has beyond the recorded objects are the declaration's plain strings, the bench's.
    assert {author for author, _ in model - raw} <= {"bench"}
    for item in found:
        if isinstance(item, Blob):
            if item.media.startswith("text/"):
                item = item.text()
            else:
                continue
        assert item.segment().ink is INK_OF[item.author]
        assert item.segment().text == item.text


# The rendered table section


def _none(key: str) -> Choice:
    return Choice(None, "fixture reason", f"fixture choice key {key}")


def _choices(record: RecordModel) -> Choices:
    return Choices(record.name, "fixture choice file", _none("contrast"), _none("best"), _none("missed"))


def _assert_section(record: RecordModel) -> None:
    view = views.full(record)
    no_table = record.seal.end == "ended" and not any(s.for_ == "end" for s in record.snapshots)
    if view.shown is None and not no_table:
        event("no snapshot: no table section")
        return
    segments = table_section(view, _choices(record))
    log = f"{record.name}/{LOG_NAME}"
    recorded: dict[tuple[str, str], set[Ink]] = {}
    for item in _model_authored(record):
        if isinstance(item, Authored):
            recorded.setdefault((item.source, item.text), set()).add(INK_OF[item.author])
    # The opened rows show Dr. Kiro's label of each cited prediction, a fixed word of the exception of
    # Requirement 4.2 (design N29), in Dr. Kiro's ink (task 12.2).
    # The same characters at the same entry may also be a bench string (a condition class equal to the
    # label), which stays in pencil.
    for place in _fixed_words(record):
        recorded.setdefault(place, {Ink.PENCIL}).add(Ink.DRKIRO)
    for seg in segments:
        if seg.ink is Ink.DRKIRO:
            # Dr. Kiro's ink only ever carries text read from the record.
            assert seg.source.startswith(record.name + "/"), seg
        if seg.source.startswith(log) and seg.ink is not Ink.MARKUP:
            # Text from a log entry: an authored value (a refusal part) in its recorded author's ink; anything
            # else is the bench's (ids, outcomes, computed numbers) in pencil.
            assert seg.ink in recorded.get((seg.source, seg.text), {Ink.PENCIL}), seg
    stamps = [seg for seg in segments if seg.ink is Ink.STAMP]
    if no_table:
        event("no table")
        assert not stamps
        return
    snapshot = view.shown
    shown = tables.read(record, snapshot)
    design = snapshot.design
    from_design = [s for s in segments if s.source.startswith(design.source) and s.ink is not Ink.MARKUP]
    if isinstance(shown, Table):
        event("table")
        # Every status word, as written, in the stamp ink, one per row in table order; nothing else stamped.
        assert [s.text for s in stamps] == [row.status for row in shown.rows]
        assert all(s.source.startswith(design.source) for s in stamps)
        for seg in from_design:
            assert seg.ink in (Ink.STAMP, INK_OF[design.author])
        return
    event("unreadable table")
    assert not stamps
    spans = [s for s in from_design if s.source.endswith(READER)]
    assert [s.ink for s in spans] == [INK_OF[span.author] for span in shown.message.spans]
    assert [s.text for s in spans] == [span.text for span in shown.message.spans]
    for seg in from_design:
        if not seg.source.endswith(READER):
            assert seg.ink is INK_OF[design.author]


# The exception of Requirement 4.2: Dr. Kiro's fixed words


def _fixed_words(record: RecordModel) -> Counter[tuple[str, str]]:
    """The exception of Requirement 4.2 (design N29), as (source, text): the verdict word of each verdict
    entry and Dr. Kiro's label of each prediction of a hypothesis entry. Dr. Kiro passed them to the bench,
    which recorded them as plain strings with no author."""
    log = f"{record.name}/{LOG_NAME}"
    words: Counter[tuple[str, str]] = Counter()
    for hypothesis in record.hypotheses:
        for prediction in hypothesis.predictions:
            words[(f"{log} line {hypothesis.seq}", prediction.label)] += 1
    for verdict in record.verdicts:
        words[(f"{log} line {verdict.seq}", verdict.verdict)] += 1
    return words


def _assert_page(record: RecordModel) -> None:
    """On the whole session page, Dr. Kiro's ink from a log entry is either an authored value recorded with
    author `dr-kiro` at that entry, or one of the fixed words of the exception, and every fixed word is shown
    in Dr. Kiro's ink. The scan reads each fixed word at the builder level as well."""
    fixed = _fixed_words(record)
    builder = scan.drkiro_word_segments([record])
    assert Counter((s.source, s.text) for s in builder) == fixed
    assert {scan.level(s) for s in builder} <= {"builder"}
    log = f"{record.name}/{LOG_NAME}"
    if not record.snapshots:
        # The page of Requirement 14.6 shows only what the record holds, as the lab page lists it: no
        # hypothesis text and no fixed word, and nothing in Dr. Kiro's ink from a log entry but values
        # recorded with author `dr-kiro`.
        event("no snapshot: the page of Requirement 14.6")
        segments, _ = session.page(views.full(record), _choices(record), Pins(record, LAYOUT))
        drkiro_values = {
            (item.source, item.text)
            for item in _model_authored(record)
            if isinstance(item, Authored) and item.author == "dr-kiro"
        }
        for seg in segments:
            if seg.ink is Ink.DRKIRO and seg.source.startswith(log):
                assert (seg.source, seg.text) in drkiro_values, seg
        return
    drkiro = {
        (item.source, item.text)
        for item in _model_authored(record)
        if isinstance(item, Authored) and item.author == "dr-kiro"
    }
    segments, _ = session.page(views.full(record), _choices(record), Pins(record, LAYOUT))
    shown_fixed: Counter[tuple[str, str]] = Counter()
    for seg in segments:
        if seg.ink is not Ink.DRKIRO or not seg.source.startswith(log):
            continue
        place = (seg.source, seg.text)
        if place in drkiro:
            continue
        # Not recorded with an author: allowed only as a fixed word of the exception.
        assert place in fixed, seg
        shown_fixed[place] += 1
    if fixed:
        event("fixed words shown")
    # Every fixed word is shown; a label may be shown more than once, in its experiment entry and in each
    # opened row that cites its prediction (task 12.2).
    assert set(shown_fixed) == set(fixed)


@settings(max_examples=100, deadline=None)
@given(records(rounds=st.integers(0, 4), designs=table_rows().map(design_text)))
def test_ink_follows_the_recorded_author(synth: SynthRecord) -> None:
    record = _load(synth)
    _assert_model(synth, record)
    _assert_section(record)
    _assert_page(record)


@settings(max_examples=100, deadline=None)
@given(records(rounds=st.integers(1, 4)))
def test_ink_follows_the_recorded_author_with_middle_tables(synth: SynthRecord) -> None:
    record = _load(synth)
    _assert_model(synth, record)
    _assert_section(record)
    _assert_page(record)


# A text without an author


def _paths(value: Any, path: tuple[Any, ...] = ()) -> Iterator[tuple[Any, ...]]:
    """The paths of every `{"author", "text"}` object in an entry body."""
    if isinstance(value, dict):
        if set(value) == {"author", "text"}:
            yield path
            return
        for k in value:
            yield from _paths(value[k], (*path, k))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from _paths(item, (*path, i))


def _rechain(entries: list[dict[str, Any]]) -> None:
    prev = GENESIS
    for entry in entries:
        entry["prev"] = prev
        without = {k: v for k, v in entry.items() if k != "hash"}
        entry["hash"] = entry_hash(without)
        prev = entry["hash"]


@settings(max_examples=100, deadline=None)
@given(records(rounds=st.integers(0, 4)), st.data())
def test_text_without_an_author_fails_naming_record_and_line(synth: SynthRecord, data: st.DataObject) -> None:
    places = [(i, p) for i, e in enumerate(synth.entries) for p in _paths(e["body"])]
    index, path = data.draw(st.sampled_from(places))
    broken = copy.deepcopy(synth)
    body = broken.entries[index]["body"]
    for step in path[:-1]:
        body = body[step]
    original = body[path[-1]]
    replacement = data.draw(
        st.sampled_from(
            (
                original["text"],  # a plain string: no author at all
                {"author": "someone", "text": original["text"]},  # an author the record does not know
            )
        )
    )
    body[path[-1]] = replacement
    _rechain(broken.entries)
    seq = broken.entries[index]["seq"]
    event(f"entry kind {broken.entries[index]['kind']}")
    with tempfile.TemporaryDirectory() as tmp:
        sessions = write_all(Path(tmp) / "sessions", [broken])
        with pytest.raises(NotebookError) as caught:
            notebook_records.load(sessions, allow_fake=True)
    record = f"sessions/{broken.application}/{broken.session}"
    assert caught.value.where == f"{record}/{LOG_NAME} line {seq}"
    assert "author" in caught.value.problem
