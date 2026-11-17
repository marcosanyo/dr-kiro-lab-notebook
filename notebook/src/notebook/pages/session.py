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
from dataclasses import dataclass

from bench.conditions import NOT_RUN
from bench.specfiles.discovered import Row, Table

from notebook import addresses, html, numbers, refusals, tables, views
from notebook.choices import Choice, Choices
from notebook.errors import NotebookError
from notebook.ink import Authored, Ink, Segment, commentary, markup, pencil
from notebook.ink import stamp as stamp_segment
from notebook.pages import bands as run_bands
from notebook.pages import chart as prediction_chart
from notebook.pages import lab, parts
from notebook.pages.parts import chosen, drkiro_block, link, row_link, say_text, stamp, sticky, tab
from notebook.pages.photo import PictureFile, Pins
from notebook.records import (
    Experiment,
    Hypothesis,
    NotMeasuredValue,
    Outcome,
    Prediction,
    RecordModel,
    Refusal,
    Snapshot,
    Trial,
)
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
_STATUS_COLUMN = _COLUMNS.index("COLUMN_STATUS")

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
    label = _label(view)
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
            [*html.text(_cell(snapshot, row, row.scope)), *run_bands.draw(view, row)],
            html.text(_id_list(snapshot, row, row.experiments)),
            html.text(_id_list(snapshot, row, row.predictions)),
            stamp(_status(snapshot, row), label),
            replaced,
        ]
        attrs = {"id": row_anchor}
        if rv.struck:
            attrs["class"] = "row-rejected"
        # The status cell is marked so the strike-through of a rejected row leaves its label alone
        # (visual steering, strike-through).
        body += html.element(
            "tr",
            attrs,
            [
                s
                for i, c in enumerate(cells)
                for s in html.element("td", {"class": "status"} if i == _STATUS_COLUMN else None, c)
            ],
        )
        note = notes.get(rv.index)
        if note is not None:
            body += html.element(
                "tr", {"class": "row-note"}, html.element("td", {"colspan": "7"}, _refused_end(note))
            )
        # The opened row (Requirement 8.8): a `<details>` in its own table row, one cell across all columns,
        # so the HTML stays valid and the row itself is still drawn once (8.11).
        body += html.element(
            "tr",
            {"class": "row-evidence"},
            html.element("td", {"colspan": "7"}, _evidence(view, snapshot, row)),
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


# The opened row (Requirements 8.5-8.8)

# The condition classes of a hit that a `validated` row needs at least one of (Requirement 8.7).
UNTRIED_CLASSES = ("new-combination", "outside")


def _evidence_experiment(view: View, snapshot: Snapshot, row: Row, cited: str) -> list[Segment]:
    """One cited experiment: its id linked to its entry, and its title as written. An id that names no
    experiment of the view is shown as the row wrote it, with commentary, and is not linked."""
    found = [e for e in view.experiments if e.id == cited]
    if not found:
        return html.element(
            "li", None, [*html.text(_cell(snapshot, row, cited)), *say_text("EVIDENCE_NO_EXPERIMENT")]
        )
    (experiment,) = found
    source = _entry_source(view.record, experiment.seq)
    eid = addresses.experiment(experiment.id, source)
    return html.element(
        "li",
        None,
        [
            *link(addresses.here(eid), html.text(pencil(eid, source))),
            markup(" "),
            *html.text(experiment.title.segment()),
        ],
    )


def _evidence_value(view: View, outcome: Outcome) -> list[Segment]:
    """The trial and the measured value of one outcome; a miss in miss red with the word "miss" (6.4)."""
    source = _entry_source(view.record, outcome.seq)
    pid = html.check_id("prediction", outcome.prediction, source)
    where = f"{source}: prediction {pid}"
    miss = outcome.outcome == "miss"
    line: list[Segment] = []
    if outcome.trial is not None:
        tid = html.check_id("trial", outcome.trial, source)
        line += [
            *say_text("OUTCOME_TRIAL"),
            *link(
                addresses.here(addresses.trial(outcome.experiment, tid, source)),
                html.text(pencil(tid, source)),
            ),
        ]
    if outcome.value is not None:
        value = pencil(numbers.short(outcome.value, where), source)
        line += say_text("OUTCOME_MEASURED")
        line += html.element("span", {"class": "ink-p miss-value"}, [value]) if miss else html.text(value)
    elif outcome.not_measured is not None:
        line += [*say_text("OUTCOME_NOT_MEASURED"), *html.text(pencil(outcome.not_measured, source))]
    line += say_text("OUTCOME_IS")
    word = pencil(outcome.outcome, source)
    line += html.element("span", {"class": "ink-p miss"}, [word]) if miss else html.text(word)
    return line


def _evidence_prediction(
    view: View, snapshot: Snapshot, row: Row, cited: str, owners: dict[str, Hypothesis]
) -> list[Segment]:
    """One cited prediction: its hypothesis, conditions, registered range, condition class, Dr. Kiro's
    label, outcome and measured value, each linked to its place in its experiment entry (Requirement 8.8).
    An id that names no prediction registered in the view is shown as the row wrote it, with commentary."""
    hypothesis = owners.get(cited)
    if hypothesis is None:
        return html.element(
            "li", None, [*html.text(_cell(snapshot, row, cited)), *say_text("EVIDENCE_NO_PREDICTION")]
        )
    (prediction,) = [p for p in hypothesis.predictions if p.id == cited]
    source = _entry_source(view.record, hypothesis.seq)
    pid = html.check_id("prediction", prediction.id, source)
    hid = html.check_id("hypothesis", hypothesis.id, source)
    where = f"{source}: prediction {pid}"
    outcomes = [o for o in view.outcomes if o.prediction == pid]
    kind = view.state.outcomes[pid].kind
    # The prediction's place: its outcome in the experiment entry, or its own address when it never ran.
    prediction_id = html.text(pencil(pid, source))
    if outcomes:
        osource = _entry_source(view.record, outcomes[0].seq)
        prediction_id = link(
            addresses.here(addresses.outcome(outcomes[0].experiment, pid, osource)), prediction_id
        )
    elif kind == NOT_RUN.kind:
        prediction_id = link(addresses.here(addresses.never_run(pid, source)), prediction_id)
    entries = [e for e in view.experiments if e.hypothesis == hypothesis.id]
    hypothesis_id = html.text(pencil(hid, source))
    if entries:
        esource = _entry_source(view.record, entries[0].seq)
        hypothesis_id = link(addresses.here(addresses.experiment(entries[0].id, esource)), hypothesis_id)
    line: list[Segment] = [
        *prediction_id,
        *say_text("EVIDENCE_OF_HYPOTHESIS"),
        *hypothesis_id,
        markup(" "),
        *html.text(hypothesis.title.segment()),
        *say_text("EVIDENCE_PREDICTED"),
        *html.text(pencil(prediction.measurement, source)),
        *say_text("PREDICTION_RANGE"),
        *html.text(
            pencil(
                f"[{numbers.short(prediction.low, where)}, {numbers.short(prediction.high, where)}]", source
            )
        ),
    ]
    if prediction.when:
        line += [*say_text("PREDICTION_WHEN"), *_conditions(prediction, source)]
    line += [
        *say_text("PREDICTION_CLASS"),
        *html.text(pencil(prediction.condition_class, source)),
        *say_text("PREDICTION_LABEL"),
        *html.text(_drkiro_word(prediction.label, source)),
    ]
    if outcomes:
        for outcome in outcomes:
            line += _evidence_value(view, outcome)
    else:
        line += [*say_text("PREDICTION_STATE"), *html.text(pencil(kind, source))]
    return html.element("li", None, line)


def _untried_hits(view: View, row: Row, owners: dict[str, Hypothesis]) -> list[Segment]:
    """For a `validated` row: each cited hit whose condition class is `new-combination` or `outside`, with
    its condition class (Requirement 8.7)."""
    items: list[Segment] = []
    for cited in row.predictions:
        hypothesis = owners.get(cited)
        if hypothesis is None:
            continue
        (prediction,) = [p for p in hypothesis.predictions if p.id == cited]
        if prediction.condition_class not in UNTRIED_CLASSES:
            continue
        for outcome in (o for o in view.outcomes if o.prediction == cited and o.outcome == "hit"):
            source = _entry_source(view.record, outcome.seq)
            pid = html.check_id("prediction", outcome.prediction, source)
            rsource = _entry_source(view.record, hypothesis.seq)
            items += html.element(
                "li",
                None,
                [
                    *link(
                        addresses.here(addresses.outcome(outcome.experiment, pid, source)),
                        html.text(pencil(pid, source)),
                    ),
                    *say_text("EVIDENCE_CLASS"),
                    *html.text(pencil(prediction.condition_class, rsource)),
                    *_evidence_value(view, outcome),
                ],
            )
    if not items:
        return html.element("p", None, say_text("EVIDENCE_UNTRIED_NONE"))
    return [
        *html.element("p", None, say_text("EVIDENCE_UNTRIED")),
        *html.element("ul", {"class": "evidence-list untried-hits"}, items),
    ]


def _evidence(view: View, snapshot: Snapshot, row: Row) -> list[Segment]:
    """The opened row: a `<details>` with the row's cited experiments and cited predictions (8.8); for an
    `observed` row the fixed explanation (8.6); for a `validated` row its untried hits (8.7). A cited miss
    is in miss red with the word "miss" in every row, so in a `partly` row too (8.5). The status word itself
    is shown only in the row's stamp (15.2)."""
    owners = {p.id: h for h in view.record.hypotheses if h.seq <= view.upto for p in h.predictions}
    experiments = [s for cited in row.experiments for s in _evidence_experiment(view, snapshot, row, cited)]
    predictions = [
        s for cited in row.predictions for s in _evidence_prediction(view, snapshot, row, cited, owners)
    ]
    content: list[Segment] = [*html.element("p", None, say_text("EVIDENCE_EXPERIMENTS"))]
    content += (
        html.element("ul", {"class": "evidence-list"}, experiments)
        if experiments
        else html.element("p", None, say_text("EVIDENCE_EXPERIMENTS_NONE"))
    )
    content += html.element("p", None, say_text("EVIDENCE_PREDICTIONS"))
    content += (
        html.element("ul", {"class": "evidence-list cited-predictions"}, predictions)
        if predictions
        else html.element("p", None, say_text("EVIDENCE_PREDICTIONS_NONE"))
    )
    if row.status == "observed":
        content += html.element(
            "p",
            {"class": "evidence-observed"},
            [*say_text("EVIDENCE_OBSERVED"), *say_text("STATUS_OBSERVED")],
        )
    elif row.status == "validated":
        content += _untried_hits(view, row, owners)
    summary = html.element(
        "summary", None, [*say_text("EVIDENCE_SUMMARY"), *html.text(_cell(snapshot, row, row.id))]
    )
    return html.element(
        "details",
        {"class": "evidence"},
        [*summary, *html.element("section", {"class": "evidence-body"}, content)],
    )


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
        out += html.element("p", None, html.element("span", {"class": "stamp-label"}, say_text(_label(view))))
    return out


def _label(view: View) -> str:
    """The label of a table's status words: "checked by the bench" for the accepted `end` snapshot; "not yet
    checked by the bench" at a replay step (Requirement 16.3); "not checked by the bench" for the last
    snapshot of a stopped session (Requirement 10.7)."""
    if view.checked:
        return "CHECKED"
    if view.replay:
        return "NOT_YET_CHECKED"
    return "NOT_CHECKED"


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
    # "<id> registered range [<low>, <high>], measured <name>: <value> miss", the measurement's name in its
    # own element (visual steering, sticky note; user, checkpoint 11).
    return [
        *link,
        *say_text("REGISTERED_RANGE"),
        *html.text(
            pencil(
                f"[{numbers.short(prediction.low, where)}, {numbers.short(prediction.high, where)}]",
                source,
            )
        ),
        *say_text("MEASURED"),
        *html.element("span", {"class": "ink-p measure-name"}, [pencil(prediction.measurement, source)]),
        *say_text("MEASURED_NAME_END"),
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
        # Only a replay step before the miss can lack it (Requirement 16.2): the note says so.
        return sticky([*say_text("REPLAY_NOT_RUN"), *chosen()])
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
            # Only a replay step before the trial can lack it (Requirement 16.2): the step says so.
            out += html.element("p", None, say_text("REPLAY_NOT_RUN"))
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


# Measured values (Requirements 5.3, 5.4)


def _short_values(record: RecordModel, trial: Trial) -> list[Segment]:
    """Every recorded measurement of `trial` in record order, rounded to 4 significant digits; a series by
    its number of samples; a not-measured value by its outcome name and the bench's reason, never a
    number."""
    source = _entry_source(record, trial.seq)
    items: list[Segment] = []
    for name, value in trial.measurements:
        where = f"{source}: {trial.id} {name}"
        line: list[Segment] = [*html.text(pencil(name, source)), *say_text("VALUE_SEPARATOR")]
        if isinstance(value, NotMeasuredValue):
            line += [
                *html.text(pencil(value.outcome, source)),
                *say_text("NOT_MEASURED_REASON"),
                *html.text(value.reason.segment()),
            ]
        elif isinstance(value, tuple):
            line += [
                *say_text("SERIES_OF"),
                *html.text(pencil(str(len(value)), source)),
                *say_text("SERIES_SAMPLES"),
            ]
        else:
            line += html.text(pencil(numbers.short(value, where), source))
        items += html.element("li", None, line)
    return [
        *html.element("p", None, say_text("VALUES_ROUNDED")),
        *html.element("ul", {"class": "values"}, items),
    ]


def _full_values(record: RecordModel, trial: Trial) -> list[Segment]:
    """The opened trial: every parameter value and every recorded measurement in full (Requirement 5.3)."""
    source = _entry_source(record, trial.seq)
    params: list[Segment] = []
    for param in trial.params:
        where = f"{source}: {trial.id} {param.name.text}"
        params += html.element(
            "li",
            None,
            [
                *html.text(param.name.segment()),
                *say_text("VALUE_SEPARATOR"),
                *html.text(pencil(numbers.full(param.value, where), source)),
            ],
        )
    measured: list[Segment] = []
    for name, value in trial.measurements:
        where = f"{source}: {trial.id} {name}"
        line: list[Segment] = [*html.text(pencil(name, source)), *say_text("VALUE_SEPARATOR")]
        if isinstance(value, NotMeasuredValue):
            line += [
                *html.text(pencil(value.outcome, source)),
                *say_text("NOT_MEASURED_REASON"),
                *html.text(value.reason.segment()),
            ]
        elif isinstance(value, tuple):
            line += html.text(pencil(", ".join(numbers.full(v, where) for v in value), source))
        else:
            line += html.text(pencil(numbers.full(value, where), source))
        measured += html.element("li", None, line)
    return html.element(
        "details",
        {"class": "full-values"},
        [
            *html.element("summary", None, say_text("VALUES_FULL")),
            *html.element("p", None, say_text("PARAMS_FULL")),
            *html.element("ul", {"class": "values"}, params),
            *html.element("p", None, say_text("MEASURED_FULL")),
            *html.element("ul", {"class": "values"}, measured),
        ],
    )


# The highlight (Requirements 10.3, 10.4)


def _highlight_trial(view: View, trial: Trial, pins: Pins) -> list[Segment]:
    return html.element(
        "section",
        {"class": "highlight-trial"},
        [*pins.figure(trial), *_short_values(view.record, trial)],
    )


def _highlight_choice(view: View, choice: Choice, name: str, pins: Pins) -> list[Segment]:
    heading = html.element("h3", None, say_text(name))
    if choice.value is None:
        return [
            *heading,
            *html.element("p", None, [*say_text("HIGHLIGHT_NONE"), *_reason(choice)]),
            *chosen(),
        ]
    by_id = {t.id: t for t in view.trials}
    shown: list[Segment] = []
    for tid in choice.value:
        trial = by_id.get(tid)
        if trial is None:
            # Only a replay step before the trial can lack it (Requirement 16.2): the step says so.
            shown += html.element("p", None, say_text("REPLAY_NOT_RUN"))
            continue
        shown += _highlight_trial(view, trial, pins)
    return [*heading, *html.element("section", {"class": "side-by-side"}, shown), *chosen()]


def _highlight(view: View, choices: Choices, pins: Pins) -> list[Segment]:
    return html.element(
        "section",
        {"class": "highlight", "id": "highlight"},
        [
            *html.element("h2", None, say_text("HIGHLIGHT_HEADING")),
            *_highlight_choice(view, choices.contrast, "HIGHLIGHT_CONTRAST", pins),
            *_highlight_choice(view, choices.best, "HIGHLIGHT_BEST", pins),
        ],
    )


# The progress (Requirement 10.5)

# The order in which outcome counts are shown: the bench's outcome words, then the bench's word for a
# registered prediction without an outcome.
OUTCOME_ORDER = ("hit", "miss", "not-checkable", NOT_RUN.kind)


def _outcome_counts(view: View) -> list[tuple[str, int]]:
    """The bench state's outcome of every registered prediction, counted by kind (`bench.core.state`)."""
    kinds = [o.kind for o in view.state.outcomes.values()]
    unknown = sorted(set(kinds) - set(OUTCOME_ORDER))
    if unknown:
        raise NotebookError(view.record.name, f"the bench state holds unknown outcome kinds {unknown}")
    return [(kind, kinds.count(kind)) for kind in OUTCOME_ORDER]


def _progress(view: View) -> list[Segment]:
    record = view.record
    source = f"{record.name}/log.jsonl, entries 1 to {view.upto}"
    used = view.state.budget - view.state.remaining
    budget = [
        *say_text("PROGRESS_BUDGET"),
        *html.text(pencil(str(used), source)),
        *say_text("BUDGET_OF"),
        *html.text(pencil(str(view.state.budget), source)),
    ]
    phases: dict[str, list[Experiment]] = {}
    for experiment in view.experiments:
        phases.setdefault(experiment.phase, []).append(experiment)
    phase_items: list[Segment] = []
    for phase, experiments in phases.items():
        line: list[Segment] = [
            *html.text(pencil(phase, source)),
            *say_text("VALUE_SEPARATOR"),
            *html.text(pencil(str(len(experiments)), source)),
            markup(" ("),
        ]
        for i, experiment in enumerate(experiments):
            if i:
                line += say_text("LIST_SEPARATOR")
            esource = _entry_source(record, experiment.seq)
            eid = addresses.experiment(experiment.id, esource)
            line += link(addresses.here(eid), html.text(pencil(eid, esource)))
        line.append(markup(")"))
        phase_items += html.element("li", None, line)
    outcome_items: list[Segment] = []
    for kind, count in _outcome_counts(view):
        outcome_items += html.element(
            "li",
            None,
            [
                *html.text(pencil(kind, source)),
                *say_text("VALUE_SEPARATOR"),
                *html.text(pencil(str(count), source)),
            ],
        )
    return html.element(
        "section",
        {"class": "progress", "id": "progress"},
        [
            *html.element("h2", None, say_text("PROGRESS_HEADING")),
            *html.element("p", None, budget),
            *html.element("p", None, say_text("PROGRESS_PHASES")),
            *html.element("ul", {"class": "phases"}, phase_items),
            *html.element("p", None, say_text("PROGRESS_OUTCOMES")),
            *html.element("ul", {"class": "outcome-counts"}, outcome_items),
            *prediction_chart.figure(view),
        ],
    )


# Dr. Kiro's plan (Requirement 10.6, design N18)


def _plan(view: View) -> list[Segment]:
    if not view.snapshots:
        raise NotebookError(view.record.name, "the record has no snapshot, so its page has no plan")
    last = view.snapshots[-1]
    requirements = html.element(
        "details",
        {"class": "plan-requirements"},
        [
            *html.element("summary", None, say_text("PLAN_REQUIREMENTS")),
            *drkiro_block(last.requirements.text().segment()),
        ],
    )
    return html.element(
        "section",
        {"class": "plan", "id": "plan"},
        [
            *html.element("h2", None, say_text("PLAN_HEADING")),
            *html.element("p", None, say_text("PLAN_NOTE")),
            *drkiro_block(last.tasks.text().segment()),
            *requirements,
        ],
    )


# The experiment entries (Requirements 10.8, 11, 15.1, 15.3)


def _code(segment: Segment) -> list[Segment]:
    """A block of code as written, with the label "written by Dr. Kiro" when it is Dr. Kiro's
    (`.code-k` in the visual steering)."""
    k = segment.ink.value
    label = (
        html.element("span", {"class": "block-label"}, say_text("WRITTEN_BY_DRKIRO"))
        if segment.ink is Ink.DRKIRO
        else []
    )
    return [*label, *html.element("p", {"class": f"ink-{k} code-{k}"}, [segment])]


def _drkiro_word(word: str, source: str) -> Segment:
    """A word Dr. Kiro gave the bench, which the bench recorded as a plain string after checking it: the
    verdict word and Dr. Kiro's label of a prediction. Shown in Dr. Kiro's ink (Requirements 15.1, 17.4; the
    exception of 4.2), and also scanned at the builder level (`scan.drkiro_word_segments`, design N29)."""
    return Segment(word, Ink.DRKIRO, source)


def _conditions(prediction: Prediction, source: str) -> list[Segment]:
    out: list[Segment] = []
    for i, param in enumerate(prediction.when):
        if i:
            out += say_text("LIST_SEPARATOR")
        where = f"{source}: {prediction.id} {param.name.text}"
        out += [
            *html.text(param.name.segment()),
            *html.text(pencil(f" = {numbers.short(param.value, where)}", source)),
        ]
    return out


class _Anchors:
    """The ids of one page, each given once. A second element with the same id fails the build."""

    def __init__(self, record: RecordModel) -> None:
        self.record = record
        self.given: set[str] = set()

    def take(self, fragment: str, source: str) -> str:
        if fragment in self.given:
            raise NotebookError(
                source, f"the session page of {self.record.name} would hold #{fragment} twice"
            )
        self.given.add(fragment)
        return fragment


def _prediction_item(view: View, prediction: Prediction, source: str, anchors: _Anchors) -> list[Segment]:
    """One registered prediction: id, measurement, range, conditions, condition class (labelled "classified
    at registration"), Dr. Kiro's label, and its outcome in the bench state. A prediction never run gets its
    own address `#H<n>.P<n>` (design 9)."""
    pid = html.check_id("prediction", prediction.id, source)
    where = f"{source}: prediction {pid}"
    kind = view.state.outcomes[pid].kind
    line: list[Segment] = [
        *html.text(pencil(pid, source)),
        markup(" "),
        *html.text(pencil(prediction.measurement, source)),
        *say_text("PREDICTION_RANGE"),
        *html.text(
            pencil(
                f"[{numbers.short(prediction.low, where)}, {numbers.short(prediction.high, where)}]", source
            )
        ),
    ]
    if prediction.when:
        line += [*say_text("PREDICTION_WHEN"), *_conditions(prediction, source)]
    line += [
        *say_text("PREDICTION_CLASS"),
        *html.text(pencil(prediction.condition_class, source)),
        *say_text("PREDICTION_LABEL"),
        *html.text(_drkiro_word(prediction.label, source)),
        *say_text("PREDICTION_STATE"),
        *html.text(pencil(kind, source)),
    ]
    attrs = None
    if kind == NOT_RUN.kind and addresses.never_run(pid, source) not in anchors.given:
        attrs = {"id": anchors.take(addresses.never_run(pid, source), source)}
    return html.element("li", attrs, line)


def _hypothesis(view: View, hypothesis: Hypothesis, anchors: _Anchors) -> list[Segment]:
    """The hypothesis's frozen part as written and its predictions."""
    source = _entry_source(view.record, hypothesis.seq)
    hid = html.check_id("hypothesis", hypothesis.id, source)
    items = [s for p in hypothesis.predictions for s in _prediction_item(view, p, source, anchors)]
    return [
        *html.element(
            "p",
            None,
            [*say_text("ENTRY_HYPOTHESIS"), *html.text(pencil(hid, source)), *say_text("ENTRY_FROZEN")],
        ),
        *drkiro_block(hypothesis.frozen.text().segment()),
        *html.element("p", None, say_text("ENTRY_PREDICTIONS")),
        *html.element("ul", {"class": "predictions"}, items),
    ]


def _experiment_file(experiment: Experiment, source: str, anchors: _Anchors) -> list[Segment]:
    eid = experiment.id
    names: list[Segment] = []
    for i, name in enumerate(experiment.params):
        if i:
            names += say_text("LIST_SEPARATOR")
        names += html.text(name.segment())
    declared: list[Segment] = [*say_text("ENTRY_PARAMS"), *names]
    if experiment.sweep:
        declared += say_text("ENTRY_SWEEP")
        for i, name in enumerate(experiment.sweep):
            if i:
                declared += say_text("LIST_SEPARATOR")
            declared += html.text(name.segment())
    return html.element(
        "section",
        {"class": "experiment-file", "id": anchors.take(addresses.experiment_file(eid, source), source)},
        [
            *html.element(
                "p",
                None,
                [*say_text("ENTRY_FILE"), *html.text(experiment.file.segment()), *say_text("ENTRY_FILE_END")],
            ),
            *_code(experiment.source.text().segment()),
            *html.element("p", None, declared),
        ],
    )


def _trial(view: View, experiment: Experiment, trial: Trial, pins: Pins, anchors: _Anchors) -> list[Segment]:
    record = view.record
    source = _entry_source(record, trial.seq)
    tid = html.check_id("trial", trial.id, source)
    params: list[Segment] = [*say_text("TRIAL_PARAMS")]
    for i, param in enumerate(trial.params):
        if i:
            params += say_text("LIST_SEPARATOR")
        where = f"{source}: {tid} {param.name.text}"
        params += [
            *html.text(param.name.segment()),
            *html.text(pencil(f" = {numbers.short(param.value, where)}", source)),
        ]
    heading = [
        *say_text("PHOTO_TRIAL"),
        *html.text(pencil(tid, source)),
        *say_text("TRIAL_SEED"),
        *html.text(pencil(str(trial.seed), source)),
    ]
    return html.element(
        "section",
        {"class": "trial", "id": anchors.take(addresses.trial(experiment.id, tid, source), source)},
        [
            *html.element("h4", None, heading),
            *pins.figure(trial),
            *html.element("p", None, params),
            *_short_values(record, trial),
            *_full_values(record, trial),
        ],
    )


def _outcome(view: View, outcome: Outcome, anchors: _Anchors) -> list[Segment]:
    """One prediction outcome; a miss in miss red with the word "miss" (Requirement 6.4)."""
    record = view.record
    source = _entry_source(record, outcome.seq)
    pid = html.check_id("prediction", outcome.prediction, source)
    where = f"{source}: prediction {pid}"
    line: list[Segment] = [*html.text(pencil(pid, source))]
    if outcome.trial is not None:
        tid = html.check_id("trial", outcome.trial, source)
        line += [
            *say_text("OUTCOME_TRIAL"),
            *link(
                addresses.here(addresses.trial(outcome.experiment, tid, source)),
                html.text(pencil(tid, source)),
            ),
        ]
    miss = outcome.outcome == "miss"
    if outcome.value is not None:
        value = pencil(numbers.short(outcome.value, where), source)
        line += say_text("OUTCOME_MEASURED")
        line += html.element("span", {"class": "ink-p miss-value"}, [value]) if miss else html.text(value)
    elif outcome.not_measured is not None:
        line += [*say_text("OUTCOME_NOT_MEASURED"), *html.text(pencil(outcome.not_measured, source))]
    line += say_text("OUTCOME_IS")
    word = pencil(outcome.outcome, source)
    line += html.element("span", {"class": "ink-p miss"}, [word]) if miss else html.text(word)
    fragment = anchors.take(addresses.outcome(outcome.experiment, pid, source), source)
    return html.element("li", {"id": fragment}, line)


def _verdict(view: View, experiment: Experiment) -> list[Segment]:
    """ "verdict on H<n>:" with the word and Dr. Kiro's words in Dr. Kiro's ink (Requirement 15.1), and the
    bench's flag with its recorded counts beside it (15.3)."""
    record = view.record
    verdicts = [v for v in view.verdicts if v.experiment == experiment.id]
    if not verdicts:
        return html.element("p", None, say_text("VERDICT_NONE"))
    out: list[Segment] = []
    for verdict in verdicts:
        source = _entry_source(record, verdict.seq)
        hid = html.check_id("hypothesis", verdict.hypothesis, source)
        out += html.element(
            "p",
            {"class": "verdict"},
            [
                *say_text("VERDICT_ON"),
                *html.text(pencil(hid, source)),
                *say_text("VERDICT_COLON"),
                *html.text(_drkiro_word(verdict.verdict, source)),
            ],
        )
        out += drkiro_block(verdict.words.segment())
    for flag in (f for f in view.flags if f.experiment == experiment.id):
        source = _entry_source(record, flag.seq)
        counts: list[Segment] = []
        for i, (kind, count) in enumerate(flag.counts):
            if i:
                counts += say_text("LIST_SEPARATOR")
            counts += [
                *html.text(pencil(kind, source)),
                *say_text("FLAG_COUNT"),
                *html.text(pencil(str(count), source)),
            ]
        out += html.element(
            "aside",
            {"class": "bench-note"},
            html.element("p", None, [*say_text("FLAG_NOTE"), *counts]),
        )
    return out


def _entry(view: View, experiment: Experiment, pins: Pins, anchors: _Anchors) -> list[Segment]:
    record = view.record
    source = _entry_source(record, experiment.seq)
    eid = anchors.take(addresses.experiment(experiment.id, source), source)
    hypotheses = [h for h in record.hypotheses if h.id == experiment.hypothesis and h.seq <= view.upto]
    if len(hypotheses) != 1:
        raise NotebookError(
            source, f"{eid} names {experiment.hypothesis}, which is not one registered hypothesis"
        )
    summary = [
        *html.text(pencil(eid, source)),
        markup(" "),
        *html.text(experiment.title.segment()),
        *say_text("ENTRY_PHASE"),
        *html.text(pencil(experiment.phase, source)),
        *say_text("ENTRY_MODE"),
        *html.text(pencil(experiment.mode, source)),
    ]
    trials = [t for t in view.trials if t.experiment == experiment.id]
    unlisted = [t.id for t in trials if t.id not in experiment.trials]
    if unlisted:
        raise NotebookError(source, f"trials {unlisted} are recorded for {eid}, which does not list them")
    trial_parts = [s for t in trials for s in _trial(view, experiment, t, pins, anchors)]
    outcomes = [o for o in view.outcomes if o.experiment == experiment.id]
    outcome_items = [s for o in outcomes for s in _outcome(view, o, anchors)]
    outcome_part = (
        html.element("ul", {"class": "outcomes"}, outcome_items)
        if outcome_items
        else html.element("p", None, say_text("OUTCOMES_NONE"))
    )
    return html.element(
        "details",
        {"class": "entry", "id": eid},
        [
            *html.element("summary", None, summary),
            *_hypothesis(view, hypotheses[0], anchors),
            *_experiment_file(experiment, source, anchors),
            *html.element("h3", None, say_text("ENTRY_TRIALS")),
            *trial_parts,
            *html.element("h3", None, say_text("ENTRY_OUTCOMES")),
            *outcome_part,
            *_verdict(view, experiment),
        ],
    )


def _entries(view: View, pins: Pins, anchors: _Anchors) -> list[Segment]:
    entries = [s for e in view.experiments for s in _entry(view, e, pins, anchors)]
    if not entries:
        entries = html.element("p", None, say_text("ENTRIES_NONE"))
    return html.element(
        "section",
        {"class": "entries", "id": "experiments"},
        [*html.element("h2", None, say_text("ENTRIES_HEADING")), *entries],
    )


def _never_run(view: View, anchors: _Anchors) -> list[Segment]:
    """Hypotheses registered in the view that no experiment of the view names, with their predictions, each
    at its own address `#H<n>.P<n>` (Requirement 11.3)."""
    run = {e.hypothesis for e in view.experiments}
    never = [h for h in view.record.hypotheses if h.seq <= view.upto and h.id not in run]
    content: list[Segment] = []
    for hypothesis in never:
        content += html.element("section", {"class": "never-run"}, _hypothesis(view, hypothesis, anchors))
    if not content:
        content = html.element("p", None, say_text("NEVER_RUN_NONE_SESSION"))
    return html.element(
        "section",
        {"class": "never-run-list", "id": "never-run"},
        [*html.element("h2", None, say_text("NEVER_RUN_HEADING")), *content],
    )


def _refusal(view: View, refusal: Refusal) -> list[Segment]:
    """One refusal: the action, what Dr. Kiro gave, and the message with each part in its recorded author's
    ink and the commentary note on quotes (Requirements 10.12, 10.13)."""
    source = _entry_source(view.record, refusal.seq)
    head: list[Segment] = [*say_text("REFUSAL_ACTION"), *html.text(pencil(refusal.action, source))]
    for key, value in refusal.given:
        head += [
            *say_text("REFUSAL_GIVEN"),
            *html.text(pencil(key, source)),
            *say_text("VALUE_SEPARATOR"),
            *html.text(value.segment()),
        ]
    shown = refusals.message(refusal)
    body = [
        *html.element("p", None, head),
        *html.element(
            "p", None, [*say_text("REFUSAL_MESSAGE"), *(s for part in shown.parts for s in html.text(part))]
        ),
    ]
    if shown.note is not None:
        body += html.element("p", {"class": "quote-note"}, html.text(shown.note))
    return html.element("li", {"class": "refusal"}, body)


def _refusals(view: View) -> list[Segment]:
    items = [s for r in view.refusals for s in _refusal(view, r)]
    content = (
        [
            *html.element("p", None, say_text("REFUSALS_INTRO")),
            *html.element("ul", {"class": "refusals"}, items),
        ]
        if items
        else html.element("p", None, say_text("REFUSALS_NONE"))
    )
    return html.element(
        "section",
        {"class": "refusal-list", "id": "refusals"},
        [*html.element("h2", None, say_text("REFUSALS_HEADING")), *content],
    )


@dataclass(frozen=True)
class Nav:
    """The controls of one replay step (Requirement 16.8). `forward` is None on the last step, where play
    stops; `back` is the step before, or the session page on the first step."""

    number: int
    total: int
    end: bool
    back: str
    forward: str | None
    session: str


def _replay_steps(record: RecordModel) -> list[Segment]:
    """Requirement 16.1 and 10.1: the steps of the record as links, the play link from the first step, or the
    sentence of Requirement 16.9 when the record has no step."""
    steps = views.steps(record)
    if not steps:
        return html.element("p", {"class": "no-replay"}, say_text("NO_STEP"))
    start = _entry_source(record, 1)
    items: list[Segment] = []
    for step in steps:
        href = addresses.replay(record.application, record.session, step.number, start)
        label = [
            *say_text("REPLAY_STEP"),
            *html.text(pencil(str(step.number), start)),
            *say_text("REPLAY_STEP_OF"),
            *html.text(pencil(str(len(steps)), start)),
            *say_text("REPLAY_AT_END" if step.end else "REPLAY_AFTER_VERDICT"),
        ]
        items += html.element("li", None, link(href, label))
    first = addresses.replay(record.application, record.session, 1, start)
    return [
        *html.element("p", None, say_text("REPLAY_INTRO")),
        *html.element("p", None, link(first + "?play=1", say_text("REPLAY_PLAY"))),
        *html.element("ol", {"class": "steps"}, items),
    ]


def _replay_list(record: RecordModel) -> list[Segment]:
    """The replay section of the session page (Requirement 16)."""
    return html.element(
        "section",
        {"class": "replay", "id": "replay"},
        [*html.element("h2", None, say_text("REPLAY_HEADING")), *_replay_steps(record)],
    )


def _replay_head(record: RecordModel, nav: Nav) -> list[Segment]:
    """The heading of a replay step: the label "replay of a sealed record" (Requirement 16.7), the step's
    number, the controls back, forward and play (Requirement 16.8), and the link back to the session page."""
    start = _entry_source(record, 1)
    position = [
        *say_text("REPLAY_STEP"),
        *html.text(pencil(str(nav.number), start)),
        *say_text("REPLAY_STEP_OF"),
        *html.text(pencil(str(nav.total), start)),
        *say_text("REPLAY_AT_END" if nav.end else "REPLAY_AFTER_VERDICT"),
    ]
    controls: list[Segment] = [
        *html.element("a", {"href": nav.back, "data-replay": "back"}, say_text("REPLAY_BACK")),
    ]
    if nav.forward is not None:
        # Play follows the forward link every 3 seconds (script); play stops on the last step, which has no
        # forward link.
        controls += [
            markup(" "),
            *html.element("a", {"href": nav.forward, "data-replay": "forward"}, say_text("REPLAY_FORWARD")),
            markup(" "),
            *html.element(
                "a", {"href": nav.forward + "?play=1", "data-replay": "play"}, say_text("REPLAY_PLAY")
            ),
        ]
    return [
        *html.element("p", {"class": "replay-label"}, say_text("REPLAY_LABEL")),
        *html.element("p", None, link(nav.session, say_text("REPLAY_TO_SESSION"))),
        *html.element("h1", None, [*say_text("SESSION_HEADING"), *html.text(pencil(record.session, start))]),
        *html.element("p", {"class": "replay-position"}, position),
        *html.element("nav", {"class": "replay-controls", "aria-label": "replay"}, controls),
    ]


# The page


def _top(record: RecordModel) -> list[Segment]:
    """The link back to the lab page and the page heading."""
    start = _entry_source(record, 1)
    lab_page = addresses.lab(record.application, start)
    addresses.session(record.application, record.session, start)
    heading = [
        *say_text("SESSION_HEADING"),
        *html.text(pencil(record.session, start)),
        *say_text("SESSION_OF_LAB"),
        *html.text(pencil(record.application, start)),
    ]
    return [
        *html.element("p", None, link(lab_page, say_text("BACK_TO_LAB"))),
        *html.element("h1", None, heading),
    ]


def _no_snapshot_page(record: RecordModel) -> list[Segment]:
    """The page of a session whose record has no snapshot (wt-003): only the content of Requirement 14.2, as
    the lab page lists it, and the sentence of 16.9 in place of the replay (14.6).

    A snapshot is taken after every run, so such a record holds no experiment and no trial. If one did, this
    page would leave it out, so the build fails instead (Requirement 2.8)."""
    if record.experiments or record.trials:
        raise NotebookError(
            record.name,
            f"the record has {len(record.experiments)} experiments and {len(record.trials)} trials but no "
            "snapshot, so its page would leave them out",
        )
    body = [
        *_top(record),
        *html.element(
            "section",
            {"class": "record-holds", "id": "record"},
            [*html.element("h2", None, say_text("NO_SNAPSHOT_HEADING")), *lab.content(record)],
        ),
        *html.element(
            "section",
            {"class": "replay", "id": "replay"},
            [
                *html.element("h2", None, say_text("REPLAY_HEADING")),
                *html.element("p", {"class": "no-replay"}, say_text("NO_REPLAY")),
            ],
        ),
    ]
    return parts.page("SESSION_TITLE", body)


def page(
    view: View, choices: Choices, pins: Pins, nav: Nav | None = None
) -> tuple[list[Segment], tuple[PictureFile, ...]]:
    """The session page as of `view` and the pictures it shows, in the section order of Requirement 10.1:
    the table with its margin, the highlight, the progress, Dr. Kiro's plan, every experiment entry; then the
    hypotheses never run, the refusals and the replay section (Requirements 14.5 and 17 follow in later
    tasks).

    `nav` is given for a replay step (Requirement 16): the page then starts with the replay heading and its
    controls, and has no replay section of its own. A record without a snapshot (wt-003) gets the page of
    Requirement 14.6 instead, with no picture."""
    record = view.record
    if choices.record != record.name:
        raise NotebookError(choices.file, f"the choice file is for {choices.record}, not {record.name}")
    if not record.snapshots:
        return _no_snapshot_page(record), ()
    if nav is not None and not view.replay:
        raise NotebookError(record.name, "a replay page needs the view of a replay step")
    if nav is None and view.replay:
        raise NotebookError(record.name, "the view of a replay step needs its replay controls")
    head = _top(record) if nav is None else _replay_head(record, nav)
    body = [
        *head,
        *table_section(view, choices, pins),
        *_highlight(view, choices, pins),
        *_progress(view),
        *_plan(view),
    ]
    anchors = _Anchors(record)
    body += [*_entries(view, pins, anchors), *_never_run(view, anchors), *_refusals(view)]
    if nav is None:
        body += _replay_list(record)
    unique: dict[str, PictureFile] = {}
    for picture in pins.files:
        unique.setdefault(picture.path, picture)
    title = "SESSION_TITLE" if nav is None else "REPLAY_LABEL"
    return parts.page(title, body), tuple(unique.values())
