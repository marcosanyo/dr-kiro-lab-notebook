"""The cover, `index.html` (Requirement 13; reshaped in the polish pass, user 2026-11-19).

The cover file (`choices.load_cover`, already checked against the records) names one missed prediction of an
ended session, or "none", and one trial per lab with the person's words for the lab's tab. The cover
shows, in this order:

- the head: a one-line kicker, the title, the tagline and one line of the three inks, linked to the legend;
- the missed prediction: the recorded sheet of the trial magnified around the body as a taped instant photo,
  the moving picture and the track beside it, and the claim card: the prediction in Dr. Kiro's ink, a
  vertical list predicted / measured / outcome with the unit of the measurement and a "missed" stamp, a
  sticky note with the measured value, and every row of the `end` snapshot's table that cites the prediction
  as a rule card (a `rejected` card has one line "replaced by <id> <rule>"; the replacing row is not drawn
  again) (13.1, 13.2, 13.7); for "none", the sentence that the session has no missed prediction (13.3);
- the reader: what the reader's runs were, the request in words, and how many runs passed per setup;
- one tab per lab, in the order of the cover file, with the lab's chosen trial and its ended sessions (13.4;
  a stopped session never reaches the cover, 14.4);
- "chosen by a person" on the miss and on every lab's trial (12.7, 13.5); everything else in one
  `<details>`.

The commentary visible before any detail is opened is at most `MAX_VISIBLE_WORDS` whitespace-separated tokens
(13.6); `page` checks this and fails the build otherwise.
"""

from bench.specfiles.discovered import STATUSES, Row, Table

from notebook import addresses, html, numbers, plots, readerrequest, readerruns, tables
from notebook.choices import Card, Cover
from notebook.errors import NotebookError
from notebook.ink import Authored, Ink, Segment, commentary, markup, pencil
from notebook.ink import stamp as stamp_segment
from notebook.layouts import Layout, layout_for
from notebook.pages import parts
from notebook.pages.parts import chosen, link, say_text
from notebook.pages.photo import PictureFile, photo
from notebook.records import Hypothesis, Outcome, Prediction, RecordModel, Snapshot, Trial

# Was 60 (13.6). The cover now holds the reader section, the tab titles and the ink line the user asked for
# (220 words at the polish pass, 21 of them the labels of the picture buttons).
MAX_VISIBLE_WORDS = 240


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


def _unit(record: RecordModel, measurement: str, where: str) -> str:
    """The recorded unit of a measurement, with a leading space; nothing for the unit "1" (a pure number)."""
    found = [m for m in record.declaration.measurements if m.name == measurement]
    if len(found) != 1:
        raise NotebookError(where, f"{measurement} is not one measurement of {record.name}")
    return "" if found[0].unit == "1" else f" {found[0].unit}"


def _measured(record: RecordModel, outcome: Outcome, unit: str, where: str) -> list[Segment]:
    source = _source(record, outcome.seq)
    if outcome.value is not None:
        return html.text(pencil(f"{numbers.short(outcome.value, where)}{unit}", source))
    if outcome.not_measured is not None:
        return html.text(pencil(outcome.not_measured, source))
    raise NotebookError(
        source, f"the miss of {outcome.prediction} has neither a value nor a not-measured outcome"
    )


def _measure_list(
    record: RecordModel, prediction: Prediction, outcome: Outcome, hypothesis: Hypothesis, where: str
) -> list[Segment]:
    """Predicted, measured and outcome, one under the other, each with a small heading; the missed stamp lies
    across the corner of the list."""
    source = _source(record, hypothesis.seq)
    unit = _unit(record, prediction.measurement, where)
    low, high = numbers.short(prediction.low, where), numbers.short(prediction.high, where)
    out_source = _source(record, outcome.seq)
    items = [
        ("COVER_PREDICTED", html.text(pencil(f"{prediction.measurement} in [{low}, {high}]{unit}", source))),
        (
            "COVER_MEASURED_HEAD",
            html.element("span", {"class": "miss-value"}, _measured(record, outcome, unit, where)),
        ),
        (
            "COVER_OUTCOME_HEAD",
            html.element("span", {"class": "miss"}, html.text(pencil(outcome.outcome, out_source))),
        ),
    ]
    rows: list[Segment] = []
    for head, value in items:
        rows += html.element("dt", None, say_text(head))
        rows += html.element("dd", None, value)
    return html.element(
        "dl",
        {"class": "measures"},
        [*rows, *html.element("span", {"class": "miss-stamp"}, say_text("COVER_MISSED_STAMP"))],
    )


def _sticky(
    record: RecordModel, prediction: Prediction, outcome: Outcome, hypothesis: Hypothesis, where: str
) -> list[Segment]:
    """The one number to read at a glance, on a yellow sticky note: the measured value with its unit, the
    range that was predicted and the conditions of the prediction. Every figure is from the record."""
    source = _source(record, hypothesis.seq)
    unit = _unit(record, prediction.measurement, where)
    low, high = numbers.short(prediction.low, where), numbers.short(prediction.high, where)
    conditions: list[Segment] = []
    for i, param in enumerate(prediction.when):
        if i:
            conditions += say_text("LIST_SEPARATOR")
        conditions += [
            *html.text(param.name.segment()),
            *html.text(pencil(f" = {numbers.short(param.value, where)}", source)),
        ]
    return parts.sticky(
        [
            *html.element(
                "span",
                {"class": "sticky-number"},
                [
                    *html.text(pencil(prediction.measurement, source)),
                    markup(" "),
                    *_measured(record, outcome, unit, where),
                ],
            ),
            *html.element(
                "span",
                {"class": "sticky-line"},
                [*say_text("COVER_STICKY_PREDICTED"), *html.text(pencil(f"[{low}, {high}]{unit}", source))],
            ),
            *html.element("span", {"class": "sticky-line"}, [*say_text("COVER_STICKY_WHEN"), *conditions]),
        ]
    )


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
    heading = html.element("h2", {"class": "cap-heading"}, say_text("COVER_MISS_HEADING"))
    if miss.prediction is None:
        return html.element(
            "section",
            {"class": "cover-miss", "id": "miss"},
            [
                *heading,
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
    source = _source(record, hypothesis.seq)
    figure, pictures = photo(
        record,
        trial,
        layout_for(layouts, record.application, record.name),
        "large",
        captions=("COVER_CAPTION_MOVING", "COVER_CAPTION_MAGNIFIED"),
    )
    # The photo pair and the track are siblings in one container (visual steering, "Cover layout").
    track = plots.track(
        record,
        trial,
        "TRACK_CAPTION_COVER",
        label=html.text(pencil(html.check_id("trial", trial.id, source), source)),
    )
    evidence = html.element("section", {"class": "cover-evidence"}, [*figure, *track])
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
        *_measure_list(record, prediction, outcome, hypothesis, where),
    ]
    # The rule cards and the details come after the picture row, across the page (visual steering).
    rules: list[Segment] = []
    end = tables.end_snapshot(record)
    if end is not None:
        table = tables.read(record, end)
        if not isinstance(table, Table):
            raise NotebookError(end.design.source, "the accepted end table cannot be read")
        rules += html.element("h3", {"class": "cap-heading"}, say_text("COVER_RULES_HEAD"))
        rules += _rows(record, end, table, pid)
    rules += _details(record, hypothesis, prediction, outcome, end is not None, where)
    section = html.element(
        "section",
        {"class": "cover-miss", "id": "miss"},
        [
            *heading,
            *evidence,
            *html.element(
                "section",
                {"class": "cover-claim"},
                [
                    *_sticky(record, prediction, outcome, hypothesis, where),
                    *html.element("section", {"class": "claim-card"}, claim),
                ],
            ),
            *html.element("section", {"class": "cover-rules"}, rules),
        ],
    )
    return section, pictures


# The reader


def _reader(runs: list[readerruns.Run], requests: dict[str, readerrequest.Request]) -> list[Segment]:
    """What the reader's runs were, the request in words and how many runs of each setup passed. Nothing when
    the build has no reader run. The section is for one request: a second request fails the build. Every
    number comes from the run files and the sentence from the committed request file the runs name."""
    if not runs:
        return []
    ids = sorted({r.request_id for r in runs})
    if len(ids) != 1:
        raise NotebookError(
            readerruns.FOLDER, f"the cover's reader section is for one request; the runs hold {len(ids)}"
        )
    request = requests[ids[0]]
    source = f"{readerruns.FOLDER}: the runs of one request"
    chips: list[Segment] = []
    for setup, passes, total, other in readerruns.tally(runs, ids[0]):
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
        [
            *html.element("h2", {"class": "cap-heading"}, say_text("COVER_READER_HEADING")),
            *html.element("p", None, say_text("COVER_READER_ABOUT")),
            *html.element(
                "blockquote",
                {"class": "request-note"},
                html.text(commentary(request.words, request.where)),
            ),
            *html.element("p", {"class": "cover-reader-line"}, [*say_text("COVER_READER"), *chips]),
        ],
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


def _session_line(record: RecordModel, card: Card) -> list[Segment]:
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
                [
                    *html.text(commentary(f"{card.unit} ", card.source)),
                    *html.text(pencil(str(len(record.trials)), seal)),
                ],
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
            *html.element("ul", {"class": "session-list"}, [s for r in mine for s in _session_line(r, card)]),
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
        record = _record(records, card.application, card.session, card.source)
        labels += html.element(
            "label",
            {"for": f"tab-{app}", "class": "tab-label"},
            [
                *html.element(
                    "span", {"class": "tab-kicker"}, html.text(commentary(card.kicker, card.source))
                ),
                *html.element("span", {"class": "tab-title"}, html.text(commentary(card.title, card.source))),
                *html.element(
                    "span",
                    {"class": "tab-note"},
                    [
                        *html.text(commentary(f"{card.engine} · ", card.source)),
                        *html.text(pencil(str(record.budget), _source(record, 1))),
                        *html.text(commentary(f" {card.unit}", card.source)),
                    ],
                ),
            ],
        )
        panel, picture = _panel(records, card, layouts)
        panels += panel
        pictures.append(picture)
    section = html.element(
        "section",
        {"class": "cover-labs"},
        [
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


def _head() -> list[Segment]:
    swatches = (
        ("k", "COVER_INK_BLUE"),
        ("red", "COVER_INK_RED"),
        ("p", "COVER_INK_PENCIL"),
    )
    key: list[Segment] = []
    for swatch, name in swatches:
        key += html.element(
            "span",
            {"class": "ink-key-item"},
            [
                *html.element("span", {"class": f"swatch swatch-{swatch}", "aria-hidden": "true"}, []),
                *say_text(name),
            ],
        )
    return html.element(
        "header",
        {"class": "cover-head"},
        [
            *html.element("p", {"class": "kicker"}, say_text("COVER_KICKER")),
            *html.element("h1", None, say_text("SITE_TITLE")),
            *html.element("p", {"class": "cover-tagline"}, say_text("TAGLINE")),
            *html.element(
                "p", {"class": "ink-key"}, [*key, *link(addresses.LEGEND, say_text("LEGEND_LINK"))]
            ),
        ],
    )


def page(
    records: list[RecordModel],
    cover: Cover,
    layouts: dict[str, Layout],
    runs: list[readerruns.Run],
    requests: dict[str, readerrequest.Request],
) -> tuple[list[Segment], tuple[PictureFile, ...]]:
    """The cover page and the pictures it shows (each once, in the order first shown). Order: the head, the
    missed prediction with its rule cards, the reader, the lab tabs with their sessions."""
    miss, pictures = _miss(records, cover, layouts)
    tabs, tab_pictures = _tabs(records, cover, layouts)
    pictures += tab_pictures
    body = [*_head(), *miss, *_reader(runs, requests), *tabs]
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
