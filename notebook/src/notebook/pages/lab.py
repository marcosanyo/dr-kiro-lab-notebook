"""The lab pages, `<app>.html` at the site root (Requirement 14, design 9, N28), and the ink legend,
`legend.html` (Requirements 4.5, 15.2). Task 8.3.

A lab page lists every record of one application, ended and stopped, in one list ordered by session id in
code-point order (14.1, 21.2; `records.load` already sorts them). Every record shows the same fields, in the
same order and the same type size (14.1), the fields of 14.2:

- how the record was sealed (the seal's `end`) and the bench's reason, as recorded;
- the budget used: the start entry's budget minus the seal's recorded remaining budget;
- the numbers of trials, experiments, hits and misses;
- the hypotheses registered and never run (no experiment entry names them);
- the discovered spec table: checked by the bench (accepted `end` snapshot), "no table" (an ended session
  without an `end` snapshot, 10.9), not checked by the bench (the last snapshot of a stopped session), not
  accepted by the bench's table reader (10.14), or no snapshot at all;
- the action at which the session stopped, from the failure entry, when the record has one.

A stopped session also gets the one fixed commentary of `text.STOPPED_NOTE` beside its recorded reason (14.3).
Each record links to its session page.

The legend names the three inks, the miss red and the four status words in commentary ink, never in the
stamp style (15.2). Every page's footer links it (`parts.page`).
"""

from bench.specfiles.discovered import STATUSES, Table

from notebook import addresses, html, tables, text
from notebook.errors import NotebookError
from notebook.ink import Segment, pencil
from notebook.pages import parts
from notebook.pages.parts import link, say_text
from notebook.records import RecordModel

# The field labels of every record, in the order shown (Requirement 14.1: the same fields for every record).
FIELDS = (
    "FIELD_SESSION",
    "FIELD_END",
    "FIELD_REASON",
    "FIELD_BUDGET",
    "FIELD_TRIALS",
    "FIELD_EXPERIMENTS",
    "FIELD_HITS",
    "FIELD_MISSES",
    "FIELD_NEVER_RUN",
    "FIELD_TABLE",
    "FIELD_STOPPED_AT",
)


def _source(record: RecordModel, seq: int) -> str:
    return f"{record.name}/log.jsonl line {seq}"


def _count(value: int, source: str) -> list[Segment]:
    return html.text(pencil(str(value), source))


def _budget(record: RecordModel) -> list[Segment]:
    source = _source(record, record.seal.seq)
    used = record.budget - record.seal.budget_remaining
    if used < 0:
        raise NotebookError(
            source,
            f"the recorded remaining budget {record.seal.budget_remaining} is more than the budget "
            f"{record.budget}",
        )
    return [*_count(used, source), *say_text("BUDGET_OF"), *_count(record.budget, _source(record, 1))]


def _outcomes(record: RecordModel, kind: str) -> list[Segment]:
    found = [o for o in record.outcomes if o.outcome == kind]
    return _count(len(found), _source(record, record.seal.seq))


def _never_run(record: RecordModel) -> list[Segment]:
    run = {e.hypothesis for e in record.experiments}
    never = [h for h in record.hypotheses if h.id not in run]
    if not never:
        return say_text("NEVER_RUN_NONE")
    out: list[Segment] = []
    for i, hypothesis in enumerate(never):
        if i:
            out += say_text("LIST_SEPARATOR")
        source = _source(record, hypothesis.seq)
        out += html.text(pencil(html.check_id("hypothesis", hypothesis.id, source), source))
    return out


def _rows(table: Table, label: str, source: str) -> list[Segment]:
    return [*say_text(label), *_count(len(table.rows), source)]


def _table(record: RecordModel) -> list[Segment]:
    end = tables.end_snapshot(record)
    if end is not None:
        read = tables.read(record, end)
        if not isinstance(read, Table):
            raise NotebookError(end.design.source, "the accepted end table cannot be read")
        return _rows(read, "TABLE_CHECKED_ROWS", end.design.source)
    if record.seal.end == "ended":
        return say_text("NO_TABLE")
    if not record.snapshots:
        return say_text("TABLE_NO_SNAPSHOT")
    last = record.snapshots[-1]
    read = tables.read(record, last)
    if isinstance(read, tables.Unreadable):
        return say_text("UNREADABLE")
    return _rows(read, "TABLE_NOT_CHECKED_ROWS", last.design.source)


def _stopped_at(record: RecordModel) -> list[Segment]:
    if record.failure is None:
        return say_text("STOPPED_AT_NONE")
    return html.text(pencil(record.failure.action, _source(record, record.failure.seq)))


def _reason(record: RecordModel) -> list[Segment]:
    out = html.text(record.seal.reason.segment())
    if record.seal.end == "stopped":
        out += parts.sticky(say_text("STOPPED_NOTE"))
    return out


def _values(record: RecordModel) -> dict[str, list[Segment]]:
    start = _source(record, 1)
    seal = _source(record, record.seal.seq)
    page = addresses.session(record.application, record.session, start)
    return {
        "FIELD_SESSION": link(page, html.text(pencil(record.session, start))),
        "FIELD_END": html.text(pencil(record.seal.end, seal)),
        "FIELD_REASON": _reason(record),
        "FIELD_BUDGET": _budget(record),
        "FIELD_TRIALS": _count(len(record.trials), seal),
        "FIELD_EXPERIMENTS": _count(len(record.experiments), seal),
        "FIELD_HITS": _outcomes(record, "hit"),
        "FIELD_MISSES": _outcomes(record, "miss"),
        "FIELD_NEVER_RUN": _never_run(record),
        "FIELD_TABLE": _table(record),
        "FIELD_STOPPED_AT": _stopped_at(record),
    }


def _record(record: RecordModel) -> list[Segment]:
    values = _values(record)
    if tuple(values) != FIELDS:
        raise NotebookError(record.name, "the lab page fields are not the fixed field list")
    items: list[Segment] = []
    for name in FIELDS:
        items += html.element("dt", None, say_text(name))
        items += html.element("dd", None, values[name])
    return html.element("li", {"class": "lab-record"}, html.element("dl", None, items))


def page(application: str, records: list[RecordModel]) -> list[Segment]:
    """The lab page of `application`: every record of it, in code-point order of the session id."""
    mine = sorted((r for r in records if r.application == application), key=lambda r: r.session)
    if not mine:
        raise NotebookError(application, "a lab page needs at least one record of its application")
    source = _source(mine[0], 1)
    addresses.site_id("application", application, source)
    body = [
        *html.element("p", None, link(addresses.COVER, say_text("BACK_TO_COVER"))),
        *html.element("h1", None, [*say_text("LAB_HEADING"), *html.text(pencil(application, source))]),
        *html.element("p", None, say_text("LAB_INTRO")),
        *html.element("ul", {"class": "lab-list"}, [s for r in mine for s in _record(r)]),
    ]
    return parts.page("LAB_TITLE", body)


def pages(records: list[RecordModel]) -> dict[str, list[Segment]]:
    """Every lab page by its address, one per application of the records, in code-point order."""
    applications = sorted({r.application for r in records})
    return {
        addresses.lab(a, _source(next(r for r in records if r.application == a), 1)): page(a, records)
        for a in applications
    }


# The ink legend

_INKS = (
    ("INK_DRKIRO_NAME", "INK_DRKIRO_ABOUT", "k"),
    ("INK_PENCIL_NAME", "INK_PENCIL_ABOUT", "p"),
    ("INK_COMMENTARY_NAME", "INK_COMMENTARY_ABOUT", "c"),
    # The miss red has no swatch: it is used only on missed predictions (Requirement 6.4).
    ("MISS_RED_NAME", "MISS_RED_ABOUT", None),
)

_STATUS_WORDS = (
    ("STATUS_VALIDATED_WORD", "STATUS_VALIDATED"),
    ("STATUS_PARTLY_WORD", "STATUS_PARTLY"),
    ("STATUS_OBSERVED_WORD", "STATUS_OBSERVED"),
    ("STATUS_REJECTED_WORD", "STATUS_REJECTED"),
)


def legend() -> list[Segment]:
    """`legend.html`: the three inks and the miss red, each with a colour swatch that holds no text, and the
    four status words, defined in commentary ink (Requirements 4.5, 15.2)."""
    words = {getattr(text, word) for word, _ in _STATUS_WORDS}
    if words != set(STATUSES):
        raise NotebookError(
            text.SOURCE_FILE, f"the legend's status words {sorted(words)} are not the bench's"
        )
    inks: list[Segment] = []
    for name, about, swatch in _INKS:
        mark: list[Segment] = []
        if swatch is not None:
            mark = html.element("span", {"class": f"swatch swatch-{swatch}", "aria-hidden": "true"}, [])
        inks += html.element("dt", None, [*mark, *say_text(name)])
        inks += html.element("dd", None, say_text(about))
    statuses: list[Segment] = []
    for word, about in _STATUS_WORDS:
        statuses += html.element("dt", None, say_text(word))
        statuses += html.element("dd", None, say_text(about))
    body = [
        *html.element("p", None, link(addresses.COVER, say_text("BACK_TO_COVER"))),
        *html.element("h1", None, say_text("LEGEND_TITLE")),
        *html.element("p", None, say_text("LEGEND_INTRO")),
        *html.element("h2", None, say_text("LEGEND_INKS")),
        *html.element("dl", {"class": "legend"}, inks),
        *html.element("h2", None, say_text("LEGEND_STATUS")),
        *html.element("p", None, say_text("LEGEND_STATUS_INTRO")),
        *html.element("dl", {"class": "legend"}, statuses),
    ]
    return parts.page("LEGEND_TITLE", body)
