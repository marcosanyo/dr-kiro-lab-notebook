"""The session page, `<app>-<session>.html` at the site root (design 9, N28).

Requirements 10, 14.5, 14.6, 17; tasks 7.5 and 12.1.

Task 7.5 writes the first section, the discovered spec table as a notebook page (Requirement 10.1):

- An accepted `end` snapshot, or the last snapshot of a stopped session: the table as the bench's reader
  gives it, each row once in table order with its seven cells (8.1, 8.11); the status as a stamp labelled
  "checked by the bench" or "not checked by the bench" (8.2, 10.7); strike-through only for exactly
  `rejected`; the "replaced by" tab, the note for a cell that names no single other row, the reverse links
  (8.3, 8.4, 8.10); the refused-end note (10.11).
- A table the reader does not accept: the section as written, the reader's message, the commentary (10.14).
- An ended session without an `end` snapshot (body-1): "no table" and every missed prediction (10.9).
- The margin: the sticky note to the chosen missed prediction (10.1, 10.2) and the chosen trials, pinned
  (`pin` hook, see `table_section`).
"""

from collections.abc import Callable

from bench.specfiles.discovered import Row, Table

from notebook import addresses, html, numbers, refusals, tables
from notebook.choices import Choice, Choices
from notebook.errors import NotebookError
from notebook.ink import Authored, Segment, commentary, markup, pencil
from notebook.ink import stamp as stamp_segment
from notebook.pages import parts
from notebook.pages.parts import chosen, drkiro_block, link, row_link, say_text, stamp, sticky, tab
from notebook.pages.photo import PictureFile, Pins
from notebook.records import Outcome, Prediction, RecordModel, Snapshot, Trial
from notebook.views import View

# The pinned picture of one chosen trial: `pages.photo.Pins(record, layout)` returns the trial's instant
# photo (`<figure class="photo">`) and keeps its picture file. Without a pin the margin names each chosen
# trial only.
Pin = Callable[[Trial], list[Segment]]

_COLUMNS = (
    "COLUMN_ID",
    "COLUMN_RULE",
    "COLUMN_SCOPE",
    "COLUMN_EXPERIMENTS",
    "COLUMN_PREDICTIONS",
    "COLUMN_STATUS",
    "COLUMN_REPLACED_BY",
)

# The note of `tables.table_view` -> its commentary in `text.py`.
_REPLACED_NOTES = {
    tables.NOTE_NO_ROW: "REPLACED_NAMES_NO_ROW",
    tables.NOTE_MANY_ROWS: "REPLACED_NAMES_MANY_ROWS",
    tables.NOTE_ITSELF: "REPLACED_NAMES_ITSELF",
}


def _entry_source(record: RecordModel, seq: int) -> str:
    return f"{record.name}/log.jsonl line {seq}"


def _predictions(record: RecordModel) -> dict[str, Prediction]:
    return {p.id: p for h in record.hypotheses for p in h.predictions}


# The table


def _cell(snapshot: Snapshot, row: Row, value: str) -> Segment:
    """One cell as the reader gives it, in the ink of the snapshot file's recorded author."""
    return Authored(value, snapshot.design.author, f"{snapshot.design.source} line {row.line}").segment()


def _id_list(snapshot: Snapshot, row: Row, items: tuple[str, ...]) -> Segment:
    """An experiments or predictions cell: the reader's items, in order, separated by ", "."""
    return _cell(snapshot, row, ", ".join(items))


def _refused_end(note: refusals.RefusedEndNote) -> list[Segment]:
    heading = html.element(
        "span", {"class": "sticky-heading"}, [s for seg in note.heading for s in html.text(seg)]
    )
    body: list[Segment] = [*html.element("p", None, heading)]
    for message in note.messages:
        parts = [s for seg in message.parts for s in html.text(seg)]
        body += html.element("p", None, parts)
        if message.note is not None:
            body += html.element("p", None, html.text(message.note))
    body += html.element("p", None, html.text(note.sealed))
    body += html.element("p", None, html.text(note.no_copy))
    return sticky(body, stamped=True)


def _table(view: View, snapshot: Snapshot, table: Table) -> list[Segment]:
    tv = tables.table_view(table)
    notes = refusals.refused_end_notes(table, view.refusals)
    label = "CHECKED" if view.checked else "NOT_CHECKED"
    head = html.element(
        "tr", None, [s for name in _COLUMNS for s in html.element("th", None, say_text(name))]
    )
    body: list[Segment] = []
    for rv in tv.rows:
        row = rv.row
        source = f"{snapshot.design.source} line {row.line}"
        row_anchor = addresses.row(row.id, source)
        id_cell = html.text(_cell(snapshot, row, row.id))
        reverse = tv.reverse_ids(rv)
        if reverse:
            links: list[Segment] = [*say_text("REPLACES")]
            for i, other in enumerate(reverse):
                if i:
                    links += say_text("LIST_SEPARATOR")
                links += row_link(other, source, html.text(_cell(snapshot, row, other)))
            id_cell += html.element("span", {"class": "replaces"}, links)
        replaced = html.text(_cell(snapshot, row, row.replaced_by))
        target = tv.tab_id(rv)
        if target is not None:
            target_row = tv.rows[rv.target].row
            replaced += _tab(snapshot, target_row, source)
        elif rv.note is not None:
            replaced += html.element("span", {"class": "replaces"}, say_text(_REPLACED_NOTES[rv.note]))
        cells = [
            id_cell,
            html.text(_cell(snapshot, row, row.rule)),
            html.text(_cell(snapshot, row, row.scope)),
            html.text(_id_list(snapshot, row, row.experiments)),
            html.text(_id_list(snapshot, row, row.predictions)),
            stamp(_status(snapshot, row), label),
            replaced,
        ]
        attrs = {"id": row_anchor}
        if rv.struck:
            attrs["class"] = "row-rejected"
        body += html.element("tr", attrs, [s for c in cells for s in html.element("td", None, c)])
        note = notes.get(rv.index)
        if note is not None:
            body += html.element(
                "tr", {"class": "row-note"}, html.element("td", {"colspan": "7"}, _refused_end(note))
            )
    grid = html.element(
        "table",
        {"class": "spec-table"},
        [*html.element("thead", None, head), *html.element("tbody", None, body)],
    )
    return html.element("section", {"class": "table-box"}, grid)


def _status(snapshot: Snapshot, row: Row) -> Segment:
    """The status cell as written, in the stamp ink (Requirements 4.1, 15.2)."""
    return stamp_segment(row.status, f"{snapshot.design.source} line {row.line}")


def _tab(snapshot: Snapshot, target: Row, source: str) -> list[Segment]:
    return tab(_cell(snapshot, target, target.id), _cell(snapshot, target, target.rule), source)


def _unreadable(view: View, snapshot: Snapshot, unreadable: tables.Unreadable) -> list[Segment]:
    """Requirement 10.14: the section as written, the reader's message as returned, the commentary."""
    out: list[Segment] = []
    if unreadable.section is None:
        out += html.element("p", None, say_text("UNREADABLE_NO_SECTION"))
    else:
        out += drkiro_block(
            Authored(unreadable.section, snapshot.design.author, snapshot.design.source).segment()
        )
    # Each span of the reader's message in the ink of its author: the bench's wording in pencil, a quote
    # from Dr. Kiro's file in Dr. Kiro's ink. The message is not parsed.
    where = f"{snapshot.design.source} (the bench's table reader)"
    message = [Authored(span.text, span.author, where).segment() for span in unreadable.message.spans]
    out += html.element(
        "p", None, [*say_text("UNREADABLE_MESSAGE"), *(s for m in message for s in html.text(m))]
    )
    out += html.element("p", None, say_text("UNREADABLE"))
    if not view.checked:
        out += html.element(
            "p", None, html.element("span", {"class": "stamp-label"}, say_text("NOT_CHECKED"))
        )
    return out


# Misses


def _miss(view: View, outcome: Outcome, predictions: dict[str, Prediction]) -> list[Segment]:
    """One missed prediction: its id linked to its place in its experiment entry, the measurement, the
    registered range, and the measured value in miss red with the word "miss" (Requirements 6.4, 10.9)."""
    record = view.record
    source = _entry_source(record, outcome.seq)
    prediction = predictions.get(outcome.prediction)
    if prediction is None:
        raise NotebookError(source, f"the outcome names {outcome.prediction}, which no hypothesis registered")
    pid = html.check_id("prediction", outcome.prediction, source)
    target = addresses.here(addresses.outcome(outcome.experiment, pid, source))
    link = parts.link(target, html.text(pencil(pid, source)))
    where = f"{source}: prediction {pid}"
    if outcome.value is not None:
        value = html.element(
            "span", {"class": "ink-p miss-value"}, [pencil(numbers.short(outcome.value, where), source)]
        )
    elif outcome.not_measured is not None:
        value = html.text(pencil(outcome.not_measured, source))
    else:
        raise NotebookError(source, f"the miss of {pid} has neither a value nor a not-measured outcome")
    return [
        *link,
        *html.text(pencil(" " + prediction.measurement, source)),
        *say_text("REGISTERED_RANGE"),
        *html.text(
            pencil(
                f"[{numbers.short(prediction.low, where)}, {numbers.short(prediction.high, where)}]",
                source,
            )
        ),
        *say_text("MEASURED"),
        *value,
        markup(" "),
        *html.element("span", {"class": "ink-p miss"}, [pencil(outcome.outcome, source)]),
    ]


def _no_table(view: View) -> list[Segment]:
    """Requirement 10.9: "no table", the commentary, and every missed prediction of the session."""
    predictions = _predictions(view.record)
    items = [
        s
        for o in view.outcomes
        if o.outcome == "miss"
        for s in html.element("li", None, _miss(view, o, predictions))
    ]
    return [
        *html.element("p", {"class": "no-table"}, say_text("NO_TABLE")),
        *html.element("p", None, say_text("NO_TABLE_NOTE")),
        *html.element("p", None, say_text("MISSED_LIST")),
        *html.element("ul", {"class": "missed"}, items),
    ]


# The margin


def _reason(choice: Choice) -> list[Segment]:
    """A "none" choice's reason, the user's builder-level text (Requirement 12.8)."""
    return html.text(commentary(choice.reason, choice.source))


def _miss_note(view: View, choices: Choices) -> list[Segment]:
    """The sticky note to the chosen missed prediction, or the reason for "none" (Requirements 10.1, 10.2)."""
    choice = choices.missed
    if choice.value is None:
        return sticky([*html.element("p", None, [*say_text("MISS_NONE"), *_reason(choice)]), *chosen()])
    (pid,) = choice.value
    found = [o for o in view.outcomes if o.prediction == pid and o.outcome == "miss"]
    if not found:
        # Only a replay step before the miss can lack it; task 18.1 shows that step's commentary.
        return []
    predictions = _predictions(view.record)
    lines = [
        s
        for o in found
        for s in html.element("p", None, [*say_text("MISS_POINTER"), *_miss(view, o, predictions)])
    ]
    return sticky([*lines, *chosen()])


def _pinned(view: View, choice: Choice, name: str, pin: Pin | None) -> list[Segment]:
    heading = html.element("p", None, say_text(name))
    if choice.value is None:
        return [*heading, *html.element("p", None, [*say_text("PINNED_NONE"), *_reason(choice)]), *chosen()]
    by_id = {t.id: t for t in view.trials}
    out = [*heading]
    for tid in choice.value:
        trial = by_id.get(tid)
        if trial is None:
            # Only a replay step before the trial can lack it; task 18.1 shows that step's commentary.
            continue
        source = _entry_source(view.record, trial.seq)
        checked = html.check_id("trial", tid, source)
        content = pin(trial) if pin is not None else html.text(pencil(checked, source))
        out += html.element("figure", {"class": "pinned", "data-trial": checked}, content)
    return [*out, *chosen()]


def _margin(view: View, choices: Choices, pin: Pin | None) -> list[Segment]:
    return html.element(
        "aside",
        {"class": "margin"},
        [
            *_miss_note(view, choices),
            *_pinned(view, choices.contrast, "PINNED_CONTRAST", pin),
            *_pinned(view, choices.best, "PINNED_BEST", pin),
        ],
    )


# The section


def _has_end(record: RecordModel) -> bool:
    return any(s.for_ == "end" for s in record.snapshots)


def table_section(view: View, choices: Choices, pin: Pin | None = None) -> list[Segment]:
    """The discovered spec table as a notebook page, with its margin (Requirement 10.1).

    `view` is the session page's view (`views.full`). `choices` is the record's choice file. `pin` returns the
    pinned picture of a chosen trial (`pages.photo.Pins`); without it the margin names each chosen trial."""
    record = view.record
    if choices.record != record.name:
        raise NotebookError(choices.file, f"the choice file is for {choices.record}, not {record.name}")
    full = view.upto == len(record.entries)
    if full and record.seal.end == "ended" and not _has_end(record):
        content = _no_table(view)
    elif view.shown is None:
        raise NotebookError(record.name, "the record has no snapshot, so its page has no table section")
    else:
        snapshot = view.shown
        read = tables.read(record, snapshot)
        if isinstance(read, tables.Unreadable):
            content = _unreadable(view, snapshot, read)
        else:
            content = _table(view, snapshot, read)
    page = html.element(
        "section", {"class": "table-page"}, [*html.element("h2", None, say_text("TABLE_HEADING")), *content]
    )
    return html.element(
        "section", {"class": "with-margin", "id": "table"}, [*page, *_margin(view, choices, pin)]
    )


# The page


def has_page(record: RecordModel) -> bool:
    """Whether the session page of this record is written yet. A record without a snapshot (wt-003) gets its
    own page in task 13.1 (Requirements 14.6, 16.9); until then the build writes no page for it."""
    return bool(record.snapshots)


def page(view: View, choices: Choices, pins: Pins) -> tuple[list[Segment], tuple[PictureFile, ...]]:
    """The session page as of `view` and the pictures it shows. Today it holds the table section with its
    margin (Requirement 10.1); task 12.1 adds the other sections after it."""
    record = view.record
    start = _entry_source(record, 1)
    lab_page = addresses.lab(record.application, start)
    addresses.session(record.application, record.session, start)
    heading = [
        *say_text("SESSION_HEADING"),
        *html.text(pencil(record.session, start)),
        *say_text("SESSION_OF_LAB"),
        *html.text(pencil(record.application, start)),
    ]
    body = [
        *html.element("p", None, link(lab_page, say_text("BACK_TO_LAB"))),
        *html.element("h1", None, heading),
        *table_section(view, choices, pins),
    ]
    unique: dict[str, PictureFile] = {}
    for picture in pins.files:
        unique.setdefault(picture.path, picture)
    return parts.page("SESSION_TITLE", body), tuple(unique.values())
