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

from bench.specfiles.discovered import STATUSES, Row, Table

from notebook import addresses, html, numbers, plots, readerruns, tables
from notebook.choices import Card, Cover
from notebook.errors import NotebookError
from notebook.ink import Authored, Ink, Segment, markup, pencil
from notebook.ink import stamp as stamp_segment
from notebook.layouts import Layout, layout_for
from notebook.pages import parts
from notebook.pages.parts import chosen, link, say_text
from notebook.pages.photo import PictureFile, photo
from notebook.records import Hypothesis, Outcome, Prediction, RecordModel, Snapshot, Trial

# Was 60 (13.6) before the reader line and the lab tabs were added to the cover (user, polish pass).
MAX_VISIBLE_WORDS = 90


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


def _cell(snapshot: Snapshot, row: Row, value: str) -> list[Segment]:
    return html.text(
        Authored(value, snapshot.design.author, f"{snapshot.design.source} line {row.line}").segment()
    )


def _row_target(record: RecordModel, snapshot: Snapshot, row: Row) -> str:
    source = f"{snapshot.design.source} line {row.line}"
    page = addresses.session(record.application, record.session, source)
    return addresses.on_page(page, addresses.row(row.id, source))


def _card_of_row(
    record: RecordModel, snapshot: Snapshot, view: tables.TableView, rv: tables.RowView
) -> list[Segment]:
    """One rule card: the row's id (linked to its place in the session page's table), its stamp and its rule.
    A `rejected` row has its rule struck, and one line "replaced by <id> <rule of that row>" below it; the
    replacing row is not drawn again as a card (user, polish pass)."""
    row = rv.row
    inner = [
        *html.element(
            "span",
            {"class": "rule-head"},
            [*link(_row_target(record, snapshot, row), _cell(snapshot, row, row.id)), *_stamp(snapshot, row)],
        ),
        *html.element("span", {"class": "cover-rule"}, _cell(snapshot, row, row.rule)),
    ]
    if rv.struck:
        if view.tab_id(rv) is not None:
            replacing = view.rows[rv.target].row
            inner += html.element(
                "span",
                {"class": "cover-replaced"},
                [
                    *say_text("REPLACED_BY"),
                    *link(_row_target(record, snapshot, replacing), _cell(snapshot, replacing, replacing.id)),
                    markup(" "),
                    *html.element(
                        "span", {"class": "rule-small"}, _cell(snapshot, replacing, replacing.rule)
                    ),
                ],
            )
        else:
            # Only possible in a table the bench did not accept at the end; shown as the table shows it.
            inner += say_text(
                {
                    tables.NOTE_NO_ROW: "REPLACED_NAMES_NO_ROW",
                    tables.NOTE_MANY_ROWS: "REPLACED_NAMES_MANY_ROWS",
                    tables.NOTE_ITSELF: "REPLACED_NAMES_ITSELF",
                }[rv.note]
            )
    classes = "rule-card row-rejected" if rv.struck else "rule-card row-cited"
    if row.status in STATUSES:
        classes += f" st-{row.status}"
    return html.element("li", {"class": classes}, inner)


def _rows(record: RecordModel, snapshot: Snapshot, table: Table, pid: str) -> list[Segment]:
    """Every row that cites `pid`, in table order, each as one rule card (13.2)."""
    view = tables.table_view(table)
    items: list[Segment] = []
    for rv in view.rows:
        if pid in rv.row.predictions:
            items += _card_of_row(record, snapshot, view, rv)
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
    figure, pictures = photo(
        record, trial, layout_for(layouts, record.application, record.name), "large", trial_word=False
    )
    # The photo and the track are siblings in one row container (visual steering, "Cover layout").
    evidence = html.element(
        "section", {"class": "cover-evidence"}, [*figure, *plots.track(record, trial, "TRACK_CAPTION_COVER")]
    )
    source = _source(record, hypothesis.seq)
    pid = html.check_id("prediction", prediction.id, source)
    claim: list[Segment] = [
        *chosen(),
        *html.element(
            "p",
            {"class": "claim-statement"},
            [
                *html.text(pencil(pid, source)),
                markup(" "),
                *html.text(hypothesis.statement.segment()),
            ],
        ),
        *html.element(
            "p",
            {"class": "claim-measure"},
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
    return section, pictures


# The reader line


def _reader_line(runs: list[readerruns.Run]) -> list[Segment]:
    """One line under the missed prediction: how many runs of each setup passed. Nothing when the build has no
    reader run. The line does not name the request: its id holds a word the blind scan refuses in builder
    text, and the line is only right for one request, so a second request fails the build. Every number comes
    from the run files."""
    if not runs:
        return []
    requests = sorted({r.request_id for r in runs})
    if len(requests) != 1:
        raise NotebookError(
            readerruns.FOLDER, f"the cover's reader line is for one request; the runs hold {len(requests)}"
        )
    source = f"{readerruns.FOLDER}: the runs of one request"
    chips: list[Segment] = []
    for setup, passes, total, other in readerruns.tally(runs, requests[0]):
        chips += html.element(
            "span",
            {"class": f"reader-chip reader-{setup}"},
            html.text(pencil(f"{setup} {passes}/{total}", source)),
        )
        for word, count in sorted(other.items()):
            chips += say_text("COVER_READER_OTHER") + html.text(pencil(f"{count} {word}", source))
    return html.element(
        "section",
        {"class": "cover-reader"},
        html.element("p", {"class": "cover-reader-line"}, [*say_text("COVER_READER"), *chips]),
    )


# The lab tabs and their sessions

MAX_TABS = 4  # the stylesheet knows this many radio-driven tabs


def _status_counts(record: RecordModel) -> list[Segment]:
    """The rows of the accepted end table by status word, or the reason the record has none."""
    end = tables.end_snapshot(record)
    source = _source(record, record.seal.seq)
    if end is None:
        return html.element("span", {"class": "session-rows"}, say_text("COVER_SESSION_NO_TABLE"))
    table = tables.read(record, end)
    if not isinstance(table, Table):
        raise NotebookError(end.design.source, "the accepted end table cannot be read")
    chips: list[Segment] = []
    for status in STATUSES:
        count = sum(1 for r in table.rows if r.status == status)
        if not count:
            continue
        chips += html.element(
            "span",
            {"class": f"status-count count-{status}"},
            html.text(pencil(f"{status} {count}", source)),
        )
    return html.element("span", {"class": "session-rows"}, [*say_text("COVER_SESSION_ROWS"), *chips])


def _session_line(record: RecordModel) -> list[Segment]:
    start = _source(record, 1)
    seal = _source(record, record.seal.seq)
    page = addresses.session(record.application, record.session, start)
    return html.element(
        "li",
        {"class": "session-line"},
        [
            *html.element(
                "span",
                {"class": "session-id"},
                [*link(page, html.text(pencil(record.session, start)))],
            ),
            *html.element("span", {"class": "session-end"}, html.text(pencil(record.seal.end, seal))),
            *html.element(
                "span",
                {"class": "session-trials"},
                [*say_text("COVER_SESSION_TRIALS"), *html.text(pencil(str(len(record.trials)), seal))],
            ),
            *_status_counts(record),
        ],
    )


def _panel(
    records: list[RecordModel], card: Card, layouts: dict[str, Layout]
) -> tuple[list[Segment], PictureFile]:
    """One lab's panel: one chosen trial as an instant photo, and the ended sessions of the lab."""
    record = _record(records, card.application, card.session, card.source)
    trial = _trial(record, card.trial, f"{card.source} trial")
    # A lab card is exempt from the magnified picture (Requirement 7.9).
    figure, (picture,) = photo(
        record,
        trial,
        layout_for(layouts, record.application, record.name),
        "small",
        trial_word=False,
        magnified=False,
    )
    # Only ended sessions: a stopped session never reaches the cover (14.4); its lab page lists it.
    mine = sorted(
        (r for r in records if r.application == card.application and r.seal.end == "ended"),
        key=lambda r: r.session,
    )
    source = _source(record, 1)
    sessions = html.element(
        "section",
        {"class": "panel-sessions"},
        [
            *html.element("ul", {"class": "session-list"}, [s for r in mine for s in _session_line(r)]),
            *html.element(
                "p",
                {"class": "panel-link"},
                link(addresses.lab(record.application, source), say_text("COVER_ALL_SESSIONS")),
            ),
        ],
    )
    return (
        html.element(
            "section",
            {
                "class": "tab-panel",
                "id": f"panel-{addresses.site_id('application', card.application, source)}",
            },
            [*html.element("section", {"class": "panel-photo"}, [*chosen(), *figure]), *sessions],
        ),
        picture,
    )


def _tabs(
    records: list[RecordModel], cover: Cover, layouts: dict[str, Layout]
) -> tuple[list[Segment], list[PictureFile]]:
    """The lab tabs: one radio and one label per lab, one panel per lab. Only the checked tab's panel shows,
    through the stylesheet alone (no script)."""
    if not 1 <= len(cover.cards) <= MAX_TABS:
        raise NotebookError(
            "choices/cover.toml", f"the cover has {len(cover.cards)} labs; it shows 1 to {MAX_TABS} tabs"
        )
    radios: list[Segment] = []
    labels: list[Segment] = []
    panels: list[Segment] = []
    pictures: list[PictureFile] = []
    for i, card in enumerate(cover.cards):
        source = f"{card.source} application"
        app = addresses.site_id("application", card.application, source)
        attrs = {"type": "radio", "name": "lab-tab", "id": f"tab-{app}", "class": "tab-radio"}
        if i == 0:
            attrs["checked"] = "checked"
        radios += html.void("input", attrs)
        labels += html.element(
            "label", {"for": f"tab-{app}", "class": "tab-label"}, html.text(pencil(card.application, source))
        )
        panel, picture = _panel(records, card, layouts)
        panels += panel
        pictures.append(picture)
    section = html.element(
        "section",
        {"class": "cover-labs"},
        [
            *html.element("p", {"class": "tabs-caption"}, say_text("COVER_TABS_LABEL")),
            *html.element(
                "section",
                {"class": "tabs"},
                [*radios, *html.element("p", {"class": "tab-bar"}, labels), *panels],
            ),
        ],
    )
    return section, pictures


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
    records: list[RecordModel],
    cover: Cover,
    layouts: dict[str, Layout],
    runs: list[readerruns.Run],
) -> tuple[list[Segment], tuple[PictureFile, ...]]:
    """The cover page and the pictures it shows (each once, in the order first shown). Order: the title, the
    missed prediction with its rows, the reader line, the lab tabs with their sessions (user, polish pass)."""
    miss, pictures = _miss(records, cover, layouts)
    tabs, tab_pictures = _tabs(records, cover, layouts)
    pictures += tab_pictures
    head = html.element(
        "header",
        {"class": "cover-head"},
        [
            *html.element("h1", None, say_text("SITE_TITLE")),
            *html.element("p", {"class": "cover-tagline"}, say_text("TAGLINE")),
        ],
    )
    body = [*head, *miss, *_reader_line(runs), *tabs]
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
