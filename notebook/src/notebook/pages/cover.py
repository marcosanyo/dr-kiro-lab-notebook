"""The cover, `index.html` (Requirement 13). Task 8.2.

The cover file (`choices.load_cover`, already checked against the records) names one missed prediction of an
ended session, or "none", and one trial per lab. The cover shows:

- the trial recorded with the missed prediction's outcome as one large pinned instant photo, and beside it the
  recorded track when the trial has one (13.1, 13.7);
- the prediction: its id and measurement in pencil, the hypothesis statement in Dr. Kiro's ink, the
  registered range in pencil, and the measured value in pencil with miss red and the word "miss" (13.1, 6.4);
- every row of the `end` snapshot's table that cites the prediction, with the replacing row of each `rejected`
  one, or that no row cites it; nothing when the session has no `end` snapshot (13.2);
- for "none", the sentence that the session has no missed prediction, in place of the photo (13.3);
- one card per lab with a small moving picture of the named trial and a link to the lab page (13.4);
- "chosen by a person" on the miss and on the cards (12.7, 13.5); everything else in one `<details>` (13.6).

The commentary visible before any detail is opened is at most `MAX_VISIBLE_WORDS` whitespace-separated tokens
(13.6); `page` checks this and fails the build otherwise. Stopped sessions never reach the cover: the cover
file names ended sessions only (14.4, checked in `choices.load_cover`).
"""

from bench.specfiles.discovered import Row, Table

from notebook import addresses, html, numbers, plots, tables
from notebook.choices import Card, Cover
from notebook.errors import NotebookError
from notebook.ink import Authored, Ink, Segment, markup, pencil
from notebook.ink import stamp as stamp_segment
from notebook.layouts import Layout, layout_for
from notebook.pages import parts
from notebook.pages.parts import chosen, link, say_text
from notebook.pages.photo import PictureFile, photo
from notebook.records import Hypothesis, Outcome, Prediction, RecordModel, Snapshot, Trial

MAX_VISIBLE_WORDS = 60


def _source(record: RecordModel, seq: int) -> str:
    return f"{record.name}/log.jsonl line {seq}"


def _record(records: list[RecordModel], application: str, session: str, where: str) -> RecordModel:
    found = [r for r in records if r.application == application and r.session == session]
    if len(found) != 1:
        raise NotebookError(where, f"names {application}/{session}, which is not one record of the build")
    return found[0]


def _trial(record: RecordModel, tid: str, where: str) -> Trial:
    found = [t for t in record.trials if t.id == tid]
    if len(found) != 1:
        raise NotebookError(where, f"trial {tid} is not one trial of {record.name}")
    return found[0]


def _prediction(record: RecordModel, pid: str, where: str) -> tuple[Hypothesis, Prediction]:
    found = [(h, p) for h in record.hypotheses for p in h.predictions if p.id == pid]
    if len(found) != 1:
        raise NotebookError(where, f"prediction {pid} is not one registered prediction of {record.name}")
    return found[0]


# Rows that cite the prediction


def _stamp(snapshot: Snapshot, row: Row) -> list[Segment]:
    """A status word in the bench's stamp style with its label below, as in the table (Requirements 8.2,
    15.2). The cover shows rows of the accepted `end` snapshot only, so the label is "checked by the
    bench"."""
    if snapshot.for_ != "end":
        raise NotebookError(snapshot.design.source, "the cover cites rows of an accepted end snapshot only")
    segment = stamp_segment(row.status, f"{snapshot.design.source} line {row.line}")
    return html.element("span", {"class": "cover-status"}, parts.stamp(segment, "CHECKED"))


def _row(record: RecordModel, snapshot: Snapshot, row: Row) -> list[Segment]:
    """A row by its id, linked to its place in the session page's table, with its rule and status."""
    source = f"{snapshot.design.source} line {row.line}"

    def cell(value: str) -> list[Segment]:
        return html.text(Authored(value, snapshot.design.author, source).segment())

    page = addresses.session(record.application, record.session, source)
    target = addresses.on_page(page, addresses.row(row.id, source))
    return [
        *link(target, cell(row.id)),
        markup(" "),
        *html.element("span", {"class": "cover-rule"}, cell(row.rule)),
        markup(" "),
        *_stamp(snapshot, row),
    ]


def _rows(record: RecordModel, snapshot: Snapshot, table: Table, pid: str) -> list[Segment]:
    """Every row that cites `pid`, in table order, each `rejected` one with its replacing row (13.2)."""
    view = tables.table_view(table)
    items: list[Segment] = []
    for rv in view.rows:
        if pid not in rv.row.predictions:
            continue
        line = _row(record, snapshot, rv.row)
        if rv.struck:
            target = view.tab_id(rv)
            if target is not None:
                replacing = view.rows[rv.target].row
                line += html.element(
                    "span",
                    {"class": "cover-replaced"},
                    [*say_text("REPLACED_BY"), *_row(record, snapshot, replacing)],
                )
            else:
                # Only possible in a table the bench did not accept at the end; shown as the table shows it.
                line += say_text(
                    {
                        tables.NOTE_NO_ROW: "REPLACED_NAMES_NO_ROW",
                        tables.NOTE_MANY_ROWS: "REPLACED_NAMES_MANY_ROWS",
                        tables.NOTE_ITSELF: "REPLACED_NAMES_ITSELF",
                    }[rv.note]
                )
        items += html.element("li", {"class": "row-rejected" if rv.struck else "row-cited"}, line)
    if not items:
        return html.element("p", None, say_text("COVER_NO_ROW"))
    return html.element("ul", {"class": "cover-rows"}, items)


# The miss


def _value(record: RecordModel, outcome: Outcome, where: str) -> list[Segment]:
    source = _source(record, outcome.seq)
    if outcome.value is not None:
        shown = pencil(numbers.short(outcome.value, where), source)
    elif outcome.not_measured is not None:
        shown = pencil(outcome.not_measured, source)
    else:
        raise NotebookError(
            source, f"the miss of {outcome.prediction} has neither a value nor a not-measured outcome"
        )
    return [
        *html.element("span", {"class": "ink-p miss-value"}, [shown]),
        markup(" "),
        *html.element("span", {"class": "ink-p miss"}, [pencil(outcome.outcome, source)]),
    ]


def _details(
    record: RecordModel,
    hypothesis: Hypothesis,
    prediction: Prediction,
    outcome: Outcome,
    has_table: bool,
    where: str,
) -> list[Segment]:
    source = _source(record, hypothesis.seq)
    out_source = _source(record, outcome.seq)
    page = addresses.session(record.application, record.session, where)
    conditions: list[Segment] = []
    for i, param in enumerate(prediction.when):
        if i:
            conditions += say_text("LIST_SEPARATOR")
        conditions += [
            *html.text(param.name.segment()),
            *html.text(pencil(f" = {numbers.short(param.value, where)}", source)),
        ]
    if outcome.value is not None:
        full = pencil(numbers.full(outcome.value, where), out_source)
    else:
        full = pencil(f"{outcome.not_measured}", out_source)
    content = [
        *html.element("summary", None, say_text("COVER_DETAILS")),
        *html.element("p", None, say_text("COVER_ABOUT")),
        *html.element(
            "p",
            None,
            [
                *say_text("COVER_HYPOTHESIS"),
                *html.text(pencil(hypothesis.id, source)),
                markup(" "),
                *html.text(hypothesis.title.segment()),
            ],
        ),
        *html.element("p", None, [*say_text("COVER_CONDITIONS"), *conditions]),
        *html.element(
            "p", None, [*say_text("COVER_CLASS"), *html.text(pencil(prediction.condition_class, source))]
        ),
        *html.element("p", None, [*say_text("COVER_FULL_VALUE"), *html.text(full)]),
        *html.element("p", None, say_text("TRACK_CAPTION")),
    ]
    if has_table:
        content += html.element("p", None, say_text("COVER_ROWS"))
    outcome_link = addresses.on_page(page, addresses.outcome(outcome.experiment, prediction.id, out_source))
    content += html.element("p", None, link(outcome_link, say_text("COVER_OUTCOME_LINK")))
    if has_table:
        content += html.element(
            "p", None, link(addresses.on_page(page, "table"), say_text("COVER_TABLE_LINK"))
        )
    content += html.element("p", None, say_text("COVER_CARDS"))
    return html.element("details", {"class": "cover-details"}, content)


def _miss(
    records: list[RecordModel], cover: Cover, layouts: dict[str, Layout]
) -> tuple[list[Segment], list[PictureFile]]:
    miss = cover.miss
    record = _record(records, miss.application, miss.session, miss.source)
    if miss.prediction is None:
        return html.element(
            "section",
            {"class": "cover-miss", "id": "miss"},
            [
                *html.element("p", None, say_text("COVER_MISS_NONE")),
                *chosen(),
            ],
        ), []
    where = f"{miss.source} prediction"
    outcome = miss.outcome
    if outcome is None or outcome.outcome != "miss" or outcome.prediction != miss.prediction:
        raise NotebookError(where, f"the cover file's prediction {miss.prediction} has no recorded miss")
    if outcome.trial is None:
        raise NotebookError(_source(record, outcome.seq), f"the miss of {miss.prediction} names no trial")
    hypothesis, prediction = _prediction(record, miss.prediction, where)
    trial = _trial(record, outcome.trial, where)
    figure, picture = photo(
        record, trial, layout_for(layouts, record.application, record.name), "large", trial_word=False
    )
    # The photo and the track are siblings in one row container (visual steering, "Cover layout").
    evidence = html.element(
        "section", {"class": "cover-evidence"}, [*figure, *plots.track(record, trial, "TRACK_CAPTION_COVER")]
    )
    source = _source(record, hypothesis.seq)
    pid = html.check_id("prediction", prediction.id, source)
    claim: list[Segment] = [
        *html.element(
            "p",
            None,
            [
                *html.text(pencil(pid, source)),
                markup(" "),
                *html.text(hypothesis.statement.segment()),
            ],
        ),
        *html.element(
            "p",
            None,
            [
                *html.text(pencil(prediction.measurement, source)),
                *say_text("COVER_RANGE"),
                *html.text(
                    pencil(
                        f"[{numbers.short(prediction.low, where)}, {numbers.short(prediction.high, where)}]",
                        source,
                    )
                ),
                *say_text("COVER_MEASURED"),
                *_value(record, outcome, where),
            ],
        ),
        *chosen(),
    ]
    end = tables.end_snapshot(record)
    if end is not None:
        table = tables.read(record, end)
        if not isinstance(table, Table):
            raise NotebookError(end.design.source, "the accepted end table cannot be read")
        claim += _rows(record, end, table, pid)
    claim += _details(record, hypothesis, prediction, outcome, end is not None, where)
    section = html.element(
        "section",
        {"class": "cover-miss", "id": "miss"},
        [*evidence, *html.element("section", {"class": "cover-claim"}, claim)],
    )
    return section, [picture]


# The lab cards


def _card(
    records: list[RecordModel], card: Card, layouts: dict[str, Layout]
) -> tuple[list[Segment], PictureFile]:
    record = _record(records, card.application, card.session, card.source)
    trial = _trial(record, card.trial, f"{card.source} trial")
    figure, picture = photo(
        record, trial, layout_for(layouts, record.application, record.name), "small", trial_word=False
    )
    source = _source(record, 1)
    heading = html.element(
        "p",
        {"class": "card-heading"},
        [
            *link(addresses.lab(record.application, source), html.text(pencil(record.application, source))),
            markup(" "),
            *html.text(pencil(record.session, source)),
        ],
    )
    return html.element("section", {"class": "card"}, [*heading, *figure]), picture


# The page


def visible_words(segments: list[Segment]) -> list[str]:
    """The commentary tokens in the page body that a visitor sees before opening any `<details>`: outside
    every `<details>`, plus each `<summary>`. Dr. Kiro's text, recorded values and markup are not counted."""
    words: list[str] = []
    in_body = False
    depth = 0
    summary = False
    for segment in segments:
        if segment.ink is Ink.MARKUP:
            tag = segment.text
            if tag.startswith("<body"):
                in_body = True
            elif tag.startswith("<details"):
                depth += 1
            elif tag == "</details>":
                depth -= 1
            elif tag.startswith("<summary"):
                summary = True
            elif tag == "</summary>":
                summary = False
            continue
        if segment.ink is Ink.COMMENTARY and in_body and (depth == 0 or (depth == 1 and summary)):
            words += segment.text.split()
    return words


def page(
    records: list[RecordModel], cover: Cover, layouts: dict[str, Layout]
) -> tuple[list[Segment], tuple[PictureFile, ...]]:
    """The cover page and the pictures it shows (each once, in the order first shown)."""
    miss, pictures = _miss(records, cover, layouts)
    cards: list[Segment] = []
    for card in cover.cards:
        segments, picture = _card(records, card, layouts)
        cards += segments
        pictures.append(picture)
    head = html.element(
        "header",
        {"class": "cover-head"},
        [
            *html.element("h1", None, say_text("SITE_TITLE")),
            *html.element("p", {"class": "cover-tagline"}, say_text("TAGLINE")),
        ],
    )
    body = [
        *head,
        *miss,
        # The label sits directly above the cards it labels (visual steering, "Cover layout").
        *html.element(
            "section",
            {"class": "cover-cards"},
            [*chosen(), *html.element("section", {"class": "card-row"}, cards)],
        ),
    ]
    segments = parts.page("SITE_TITLE", body)
    words = visible_words(segments)
    if len(words) > MAX_VISIBLE_WORDS:
        raise NotebookError(
            addresses.COVER,
            f"the cover shows {len(words)} words of commentary before any detail is opened; "
            f"at most {MAX_VISIBLE_WORDS} are allowed",
        )
    unique: dict[str, PictureFile] = {}
    for picture in pictures:
        unique.setdefault(picture.path, picture)
    return segments, tuple(unique.values())
