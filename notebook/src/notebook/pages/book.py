"""The opened notebook: one session as a story (notebook-shelf design 4 to 9).
The first screen says what was found: the claim, the summary, the chips, the two large photos with their
handwritten line, three sticky notes with numbers from the record, and the best so far trial by trial. Below
it come the discovered spec, Dr. Kiro's plan, every experiment with its hypothesis, and the reader's results.
The title, the summary and the words on the photos are written by a person (choice file, orange pen); every
number comes from the record; Dr. Kiro's words keep Dr. Kiro's ink.
"""

import re
from dataclasses import dataclass

from bench.specfiles.discovered import Row, Table

from notebook import addresses, html, numbers, progress, readerrequest, readerruns, tables, text
from notebook.choices import Choices, Lab, Polaroid
from notebook.display import Retake, Retakes
from notebook.errors import NotebookError
from notebook.ink import Authored, Ink, Segment, commentary, markup, pencil
from notebook.ink import stamp as stamp_segment
from notebook.layouts import Layout
from notebook.pages import parts, photo
from notebook.pages.parts import link, say_text, stamp
from notebook.records import (
    Experiment,
    Hypothesis,
    NotMeasuredValue,
    Outcome,
    RecordModel,
    Snapshot,
    Trial,
)

STATUS_ICONS = {
    "validated": "M3 9 L7 13 L15 4",
    "partly": "M9 2 A7 7 0 0 1 9 16 Z",
    "observed": "M2 9 Q9 2 16 9 Q9 16 2 9 Z M9 7 A2 2 0 1 0 9.01 7",
    "rejected": "M4 4 L14 14 M14 4 L4 14",
}
LABEL_SHARE = 0.1
MAX_LABELS = 4
LABEL_CHAR = 8.5  # pixels of the chart's own scale taken by one character of a name
LABEL_HEIGHT = 20.0
_TASK = re.compile(r"^\s*- \[([ xX])\] (.+?)\s*$")


@dataclass
class Shown:
    """What the page collects while it is made: the picture files it shows, in order."""

    files: list[photo.PictureFile]
    retakes: Retakes

    def retake(self, record: RecordModel, trial: Trial) -> Retake | None:
        return self.retakes.get((record.application, record.session, trial.id))


def _ours() -> list[Segment]:
    """The small orange mark beside a text a person wrote."""
    return [markup(" "), *_el("span", "ours", say_text("OURS"))]


def _new_best() -> list[Segment]:
    """A star and the words "new best"; the star is markup, so the commentary stays plain text."""
    return [markup("&#9733; "), *say_text("NEW_BEST")]


def _src(record: RecordModel, seq: int) -> str:
    return f"{record.name}/log.jsonl line {seq}"


def _human(text: str, source: str) -> list[Segment]:
    return html.text(commentary(text, source))


def _el(tag: str, cls: str | None, children: list[Segment], **attrs: str) -> list[Segment]:
    return html.element(tag, ({"class": cls} if cls else {}) | attrs, children)


def _unit(record: RecordModel, name: str) -> str:
    unit = next(m.unit for m in record.declaration.measurements if m.name == name)
    return "" if unit == "1" else unit


def _values(record: RecordModel, trial: Trial, *, full: bool = False) -> str:
    """The scalar measurements of a trial as one line of pencil: short at the top of a page ("x 0.75 m"), and
    with four significant digits in an opened note (`full`)."""
    source = _src(record, trial.seq)
    values = dict(trial.measurements)
    out = []
    for m in (m for m in record.declaration.measurements if m.kind == "scalar"):
        value = values[m.name]
        where = f"{source}: {trial.id} {m.name}"
        if isinstance(value, NotMeasuredValue):
            if full:
                out.append(f"{m.name} {value.outcome}")
        elif full:
            out.append(f"{m.name} {numbers.short(value, where)} {_unit(record, m.name)}".strip())
        else:
            out.append(f"{m.name} {numbers.brief(value, _unit(record, m.name), where)}")
    return " · ".join(out)


# The chips under the summary


def _icon(status: str) -> list[Segment]:
    return html.element(
        "svg",
        {"class": "icon", "viewbox": "0 0 18 18", "width": "16", "height": "16", "aria-hidden": "true"},
        html.element(
            "path",
            {"d": STATUS_ICONS[status], "fill": "none", "stroke": "currentColor", "stroke-width": "2"},
            [],
        ),
    )


def _chips(record: RecordModel, chosen: Choices, lab: Lab, table: Table | None) -> list[Segment]:
    source = f"{record.name}: chips"
    counts = progress.predictions(record)
    chips: list[list[Segment]] = [
        [*say_text("CHIP_MODEL"), *_human(chosen.model, f"{chosen.file} key model")],
        [*html.text(pencil(str(len(record.trials)), source)), markup(" "), *_human(lab.unit, lab.source)],
        [*say_text("CHIP_DATE"), *_human(chosen.date, f"{chosen.file} key date")],
    ]
    if table is None:
        chips.append(say_text("CHIP_NO_TABLE"))
    else:
        by_status = progress.status_counts(table)
        for status in progress.STATUSES:
            chips.append(
                _el(
                    "span",
                    f"chip-status chip-{status}",
                    [
                        *_icon(status),
                        *html.text(pencil(str(by_status[status]), source)),
                        markup(" "),
                        *html.text(stamp_segment(status, source)),
                    ],
                )
            )
    chips.append([*say_text("CHIP_PREDICTIONS"), *html.text(pencil(f"{counts.hit}/{counts.total}", source))])
    if record.seal.end == "stopped":
        chips.append([*say_text("CHIP_STOPPED"), *html.text(record.seal.reason.segment())])
    return _el("ul", "chips", [s for chip in chips for s in html.element("li", None, chip)])


# The highlight


def _hypothesis_of(record: RecordModel, trial: Trial) -> str:
    for experiment in record.experiments:
        if trial.id in experiment.trials:
            return experiment.hypothesis
    raise NotebookError(_src(record, trial.seq), f"{trial.id} belongs to no experiment")


def _polaroid(
    record: RecordModel,
    layout: Layout,
    found: progress.Series,
    chosen: Choices,
    pol: Polaroid,
    shown: Shown,
) -> list[Segment]:
    trial = next(t for t in record.trials if t.id == pol.trial)
    source = _src(record, trial.seq)
    figure, files = photo.photo(
        record, trial, layout, "large", trial_word=False, retake=shown.retake(record, trial)
    )
    shown.files += files
    point = next(p for p in found.points if p.trial.id == trial.id)
    head = [
        *_human(pol.heading, pol.source),
        markup(" "),
        *html.text(pencil(f"({_hypothesis_of(record, trial)})", source)),
    ]
    if pol.star:
        head += _el("span", "star", [markup("&#9733;")], title="best")
    values = [*html.text(pencil(f"{trial.id} · {_values(record, trial)}", source))]
    if point.improved and point.delta is not None:
        values += [markup(" "), *_new_best()]
    tilt = "tilt-left" if chosen.polaroids[0] is pol else "tilt-right"
    return _el(
        "section",
        f"polaroid {tilt}",
        [
            *_el("p", "cap", head),
            *figure,
            *_el("p", "pol-words", _human(pol.words, pol.source)),
            *_el("p", "pol-values", values),
        ],
    )


def _notes(record: RecordModel, found: progress.Series, table: Table | None) -> list[Segment]:
    source = f"{record.name}: sticky notes"
    counts = progress.predictions(record)
    best = found.best
    best_text = progress.best_value_text(found)
    if best is None or best_text is None:
        first = html.text(pencil("-", source))
        first_about = say_text("NOTE_NO_BEST")
    else:
        first = html.text(pencil(best_text, source))
        first_about = [
            *say_text("NOTE_BEST_BEFORE"),
            *html.text(pencil(found.spec.measurement, source)),
            *say_text("NOTE_BEST_AFTER"),
            *html.text(pencil(f"{best.trial.id} ({best.hypothesis})", source)),
        ]
    if table is not None:
        rejected = progress.status_counts(table)["rejected"]
        third_about = say_text("NOTE_REJECTED_RULES")
    else:
        rejected = sum(1 for v in record.verdicts if v.verdict == "rejected")
        third_about = say_text("NOTE_REJECTED_VERDICTS")
    notes = [
        ("note-yellow tilt-one", first, first_about),
        (
            "note-pink tilt-two",
            html.text(pencil(f"{counts.hit}/{counts.total}", source)),
            say_text("NOTE_HITS"),
        ),
        ("note-blue tilt-three", html.text(pencil(str(rejected), source)), third_about),
    ]
    out: list[Segment] = []
    for cls, big, about in notes:
        out += _el("aside", f"note {cls}", [*_el("p", "note-big", big), *_el("p", "note-about", about)])
    return _el("section", "notes", out)


def _value_text(value: float, unit: str, where: str) -> str:
    return f"{numbers.short(value, where)} {unit}".strip()


def _chart(record: RecordModel, found: progress.Series) -> list[Segment]:
    """The best so far after every trial, as a step line. Only the largest steps up are named, each with its
    hypothesis and the change ("H10: +9.2 cm"), and no two names overlap."""
    source = f"{record.name}: progress"
    width, height, left, right, top, bottom = 520.0, 250.0, 62.0, 16.0, 40.0, 30.0
    points = found.points
    raws = [p.raw for p in points if p.raw is not None]
    bests = [p.best for p in points if p.best is not None]
    if not bests:
        return _el("p", "chart-none", say_text("PROGRESS_NONE"))
    low, high = min(raws), max(raws)
    pad = (high - low) * 0.1 or 1.0
    low, high = low - pad, high + pad
    n = len(points)
    unit = found.unit

    def x(i: int) -> float:
        return left + (width - left - right) * (i / (n - 1) if n > 1 else 0.5)

    def y(v: float) -> float:
        return top + (height - top - bottom) * (1 - (v - low) / (high - low))

    marks: list[Segment] = []
    for v in (min(raws), max(raws)):
        marks += html.shape(
            "line",
            {
                "class": "ch-grid",
                "x1": f"{left}",
                "x2": f"{width - right}",
                "y1": f"{y(v):.1f}",
                "y2": f"{y(v):.1f}",
            },
        )
        marks += html.element(
            "text",
            {"class": "ch-tick", "x": f"{left - 6}", "y": f"{y(v) + 4:.1f}"},
            [pencil(numbers.brief(v, unit, source), source)],
        )
    d = ""
    for i, p in enumerate(points):
        if p.best is None:
            continue
        d += f"M{x(i):.1f} {y(p.best):.1f}" if not d else f"H{x(i):.1f}V{y(p.best):.1f}"
    marks += html.element("path", {"class": "ch-line", "d": d + f"H{x(n - 1):.1f}", "fill": "none"}, [])
    for i, p in enumerate(points):
        if p.raw is not None:
            cls = "ch-dot" if p.value is not None else "ch-dot ch-dot-off"
            marks += html.shape(
                "circle", {"class": cls, "cx": f"{x(i):.1f}", "cy": f"{y(p.raw):.1f}", "r": "2"}
            )
    span = max(bests) - min(bests)
    steps = [
        (i, p)
        for i, p in enumerate(points)
        if p.improved and p.delta is not None and abs(p.delta) >= LABEL_SHARE * span
    ]
    steps.sort(key=lambda item: -abs(item[1].delta))
    named: list[tuple[float, float, float]] = []  # (left, right, y) of each name
    shown_steps: list[tuple[int, str, float, float]] = []
    for i, p in steps[:MAX_LABELS]:
        text = f"{p.hypothesis}: {numbers.brief(p.delta, unit, source, signed=True)}"
        size = LABEL_CHAR * len(text)
        end = x(i) > width * 0.6
        box_left, box_right = (x(i) - size, x(i)) if end else (x(i) + 6, x(i) + 6 + size)
        for dy in (-12, -32, 22):
            at = y(p.best) + dy
            if box_left < 0 or box_right > width or at < 12 or at > height - bottom:
                continue
            if all(box_right < a or box_left > b or abs(at - c) > LABEL_HEIGHT for a, b, c in named):
                named.append((box_left, box_right, at))
                shown_steps.append((i, text, at, 0.0 if not end else 1.0))
                break
    for i, p in enumerate(points):
        if p.improved and p.best is not None:
            marks += html.shape(
                "circle", {"class": "ch-best", "cx": f"{x(i):.1f}", "cy": f"{y(p.best):.1f}", "r": "4"}
            )
    for i, label, at, end in shown_steps:
        cls = "ch-note ch-note-end" if end else "ch-note"
        marks += html.element(
            "text",
            {"class": cls, "x": f"{x(i) - (2 if end else -6):.1f}", "y": f"{at:.1f}"},
            [pencil(label, source)],
        )
    for i in {0, n - 1}:
        marks += html.element(
            "text",
            {"class": "ch-tick ch-tick-x", "x": f"{x(i):.1f}", "y": f"{height - 10}"},
            [pencil(points[i].trial.id, source)],
        )
    svg = html.element(
        "svg",
        {
            "class": "chart",
            "viewbox": f"0 0 {width:.0f} {height:.0f}",
            "role": "img",
            "aria-label": "best so far after every trial",
        },
        marks,
    )
    caption = [
        *say_text("PROGRESS_LINE"),
        *html.text(pencil(found.spec.measurement, source)),
        *say_text("PROGRESS_BETTER_HIGHER" if found.spec.better == "higher" else "PROGRESS_BETTER_LOWER"),
    ]
    if found.spec.require is not None:
        caption += [
            *say_text("PROGRESS_ONLY_WHEN"),
            *html.text(pencil(f"{found.spec.require} = {numbers.short(found.spec.equals, source)}", source)),
            *say_text("PROGRESS_OFF"),
        ]
    return _el("figure", "progress", [*svg, *_el("figcaption", None, caption)])


def _highlight(
    record: RecordModel,
    layout: Layout,
    chosen: Choices,
    table: Table | None,
    shown: Shown,
) -> list[Segment]:
    head = _el("h3", "cap", say_text("HIGHLIGHT_HEADING"))
    if chosen.progress is None:
        return _el(
            "section", "highlight", [*head, *_el("p", None, say_text("HIGHLIGHT_NONE"))], id="highlight"
        )
    found = progress.series(record, chosen.progress)
    pols = [s for p in chosen.polaroids for s in _polaroid(record, layout, found, chosen, p, shown)]
    first = next(t for t in record.trials if t.id == chosen.polaroids[0].trial)
    retake = shown.retake(record, first)
    interval = retake.interval if retake is not None else layout.interval
    together = _el(
        "section",
        "polaroids",
        pols,
        **{
            "data-sync": "yes",
            "data-interval": str(interval),
            "data-play": text.SYNC_PLAY,
            "data-pause": text.SYNC_PAUSE,
            "data-label": text.SYNC_LABEL,
        },
    )
    side = _el("section", "side", [*_notes(record, found, table), *_chart(record, found)])
    return _el(
        "section", "highlight", [*head, *_el("section", "hl-grid", [*together, *side])], id="highlight"
    )


# The discovered spec


def _cell(snapshot: Snapshot, row: Row, value: str) -> Segment:
    return Authored(value, snapshot.design.author, f"{snapshot.design.source} line {row.line}").segment()


def _anchors(record: RecordModel) -> set[str]:
    ids = {e.id for e in record.experiments}
    ids |= {p.id for h in record.hypotheses for p in h.predictions}
    return ids


def _refs(snapshot: Snapshot, row: Row, items: tuple[str, ...], known: set[str]) -> list[Segment]:
    out: list[Segment] = []
    for i, item in enumerate(items):
        if i:
            out += say_text("LIST_SEPARATOR")
        piece = html.text(_cell(snapshot, row, item))
        out += link(addresses.here(item), piece) if item in known else piece
    return out


def _rule(
    record: RecordModel,
    snapshot: Snapshot,
    view: tables.TableView,
    index: int,
    checked: bool,
    known: set[str],
) -> list[Segment]:
    """One compact card: the id and stamp, the rule, and where it was rewritten. The scope and the evidence
    are in a closed note."""
    rv = view.rows[index]
    row = rv.row
    src = f"{snapshot.design.source} line {row.line}"
    head = [
        *html.text(_cell(snapshot, row, row.id)),
        *stamp(stamp_segment(row.status, src), "CHECKED" if checked else "NOT_CHECKED"),
    ]
    body = [
        *_el("p", "rule-head", head),
        *_el(
            "p", "rule-text struck" if rv.struck else "rule-text", html.text(_cell(snapshot, row, row.rule))
        ),
    ]
    if rv.target is not None:
        target = view.rows[rv.target].row
        body += _el(
            "p",
            "rule-rewrite",
            [
                *say_text("REWRITTEN_AS"),
                *link(
                    addresses.here(addresses.row(target.id, src)),
                    html.text(_cell(snapshot, target, target.id)),
                ),
                markup(" "),
                *html.text(_cell(snapshot, target, target.rule)),
            ],
        )
    elif rv.note is not None:
        body += _el("p", "rule-rewrite", [*say_text("REWRITTEN_NOWHERE"), *html.text(pencil(rv.note, src))])
    more = _el("p", "rule-scope", html.text(_cell(snapshot, row, row.scope)))
    evidence: list[Segment] = []
    if row.experiments:
        evidence += [*say_text("FROM_EXPERIMENTS"), *_refs(snapshot, row, row.experiments, known)]
    if row.predictions:
        evidence += [*say_text("FROM_PREDICTIONS"), *_refs(snapshot, row, row.predictions, known)]
    if evidence:
        more += _el("p", "rule-evidence", evidence)
    body += _el("details", "rule-more", [*html.element("summary", None, say_text("RULE_MORE")), *more])
    cls = f"rule rule-{row.status}" if row.status in progress.STATUSES else "rule"
    return html.element("li", {"class": cls, "id": addresses.row(row.id, src)}, body)


def _spec(record: RecordModel, table: Table | None, checked: bool) -> list[Segment]:
    head = _el("h3", "cap", say_text("SPEC_HEADING"))
    snapshot = tables.end_snapshot(record) or (record.snapshots[-1] if record.snapshots else None)
    if table is None or snapshot is None:
        return _el("section", "spec", [*head, *_el("p", None, say_text("SPEC_NONE"))], id="spec")
    view = tables.table_view(table)
    known = _anchors(record)
    items = [s for i in range(len(view.rows)) for s in _rule(record, snapshot, view, i, checked, known)]
    note = [] if checked else _el("p", "spec-note", say_text("SPEC_UNCHECKED"))
    return _el("section", "spec", [*head, *note, *_el("ul", "rules", items)], id="spec")


# Dr. Kiro's plan


def _plan(record: RecordModel) -> list[Segment]:
    snapshot = tables.end_snapshot(record) or (record.snapshots[-1] if record.snapshots else None)
    if snapshot is None:
        return []
    text = snapshot.tasks.text()
    steps = []
    for number, line in enumerate(text.text.splitlines(), start=1):
        found = _TASK.match(line)
        if found is None:
            continue
        source = f"{snapshot.tasks.source} line {number}"
        steps.append((found.group(1) != " ", Authored(found.group(2), text.author, source).segment()))
    if not steps:
        return []
    items: list[Segment] = []
    for i, (done, segment) in enumerate(steps, start=1):
        number = _el("span", "plan-num", html.text(pencil(str(i), snapshot.tasks.source)))
        words = _el("span", "plan-text", html.text(segment))
        items += html.element(
            "li",
            {"class": "plan-step plan-done" if done else "plan-step"},
            html.element("details", None, html.element("summary", None, [*number, *words])),
        )
    return _el(
        "section",
        "plan",
        [
            *_el("h3", "cap", say_text("PLAN_HEADING")),
            *_el("p", "hint", say_text("PLAN_HINT")),
            *_el("ol", "plan-list", items),
        ],
        id="plan",
    )


# Every experiment and hypothesis


def _outcome_line(record: RecordModel, hypothesis: Hypothesis, outcomes: dict[str, Outcome]) -> list[Segment]:
    out: list[Segment] = []
    for i, prediction in enumerate(hypothesis.predictions):
        source = _src(record, hypothesis.seq)
        if i:
            out += say_text("LIST_SEPARATOR")
        outcome = outcomes.get(prediction.id)
        short = prediction.id.split(".")[-1]
        if outcome is None:
            out += [*html.text(pencil(short, source)), *say_text("OUTCOME_NOT_RUN")]
            continue
        word = html.text(pencil(outcome.outcome, source))
        out += [
            *html.text(pencil(short, source)),
            markup(" "),
            *(_el("span", "miss", word) if outcome.outcome == "miss" else word),
        ]
        if outcome.value is not None:
            where = f"{_src(record, outcome.seq)}: {prediction.id}"
            shown = numbers.brief(outcome.value, _unit(record, prediction.measurement), where)
            out += html.text(pencil(f" {prediction.measurement} {shown}", source))
    return out


def _prediction(record: RecordModel, prediction, outcomes: dict[str, Outcome]) -> list[Segment]:
    source = _src(record, next(h.seq for h in record.hypotheses if prediction in h.predictions))
    where = f"{source}: {prediction.id}"
    outcome = outcomes.get(prediction.id)
    line = [
        *html.text(pencil(prediction.id, source)),
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
        line += say_text("PREDICTION_WHEN")
        for i, param in enumerate(prediction.when):
            if i:
                line += say_text("LIST_SEPARATOR")
            line += [
                *html.text(param.name.segment()),
                *html.text(pencil(f" = {numbers.short(param.value, where)}", source)),
            ]
    line += [
        *say_text("PREDICTION_LABEL"),
        *html.text(Segment(prediction.label, Ink.DRKIRO, source)),
        *say_text("PREDICTION_STATE"),
        *html.text(pencil(outcome.outcome if outcome else "not run", source)),
    ]
    return html.element("li", {"id": addresses.never_run(prediction.id, source)}, line)


def _trial_card(
    record: RecordModel, layout: Layout, experiment: Experiment, trial: Trial, best: bool, shown: Shown
) -> list[Segment]:
    source = _src(record, trial.seq)
    figure, files = photo.photo(
        record, trial, layout, "small", trial_word=False, retake=shown.retake(record, trial)
    )
    shown.files += files
    params: list[Segment] = []
    for i, param in enumerate(trial.params):
        if i:
            params += say_text("LIST_SEPARATOR")
        params += [
            *html.text(param.name.segment()),
            *html.text(pencil(f" = {numbers.short(param.value, f'{source}: {trial.id}')}", source)),
        ]
    values = [*html.text(pencil(_values(record, trial, full=True), source))]
    if best:
        values += [markup(" "), *_new_best()]
    return html.element(
        "li",
        {"class": "trial-card", "id": addresses.trial(experiment.id, trial.id, source)},
        [*figure, *_el("p", "trial-params", params), *_el("p", "pol-values", values)],
    )


def _experiment(
    record: RecordModel, layout: Layout, experiment: Experiment, bests: set[str], shown: Shown
) -> list[Segment]:
    source = _src(record, experiment.seq)
    trials = [t for t in record.trials if t.id in experiment.trials]
    cards = [s for t in trials for s in _trial_card(record, layout, experiment, t, t.id in bests, shown)]
    heading = [
        *html.text(pencil(experiment.id, source)),
        markup(" "),
        *html.text(experiment.title.segment()),
    ]
    return _el(
        "section",
        "experiment",
        [*_el("h5", None, heading), *_el("ul", "trial-cards", cards)],
        id=addresses.experiment(experiment.id, source),
    )


def _row_stamps(record: RecordModel, table: Table | None, checked: bool, ids: set[str]) -> list[Segment]:
    snapshot = tables.end_snapshot(record) or (record.snapshots[-1] if record.snapshots else None)
    if table is None or snapshot is None:
        return []
    out: list[Segment] = []
    for row in table.rows:
        if ids & set(row.experiments):
            src = f"{snapshot.design.source} line {row.line}"
            cls = f"mini-stamp stamp-{row.status}" if row.status in progress.STATUSES else "mini-stamp"
            out += _el(
                "span",
                cls,
                [
                    *html.text(_cell(snapshot, row, row.id)),
                    markup(" "),
                    *html.text(stamp_segment(row.status, src)),
                ],
            )
    return out


def _hypothesis_row(
    record: RecordModel,
    layout: Layout,
    hypothesis: Hypothesis,
    found: progress.Series | None,
    table: Table | None,
    checked: bool,
    outcomes: dict[str, Outcome],
    shown: Shown,
) -> list[Segment]:
    source = _src(record, hypothesis.seq)
    hid = html.check_id("hypothesis", hypothesis.id, source)
    experiments = [e for e in record.experiments if e.hypothesis == hypothesis.id]
    bests = (
        {p.trial.id for p in found.points if p.improved and p.delta is not None}
        if found is not None
        else set()
    )
    mine = [t for e in experiments for t in record.trials if t.id in e.trials]
    star = [t for t in mine if t.id in bests]
    pic: list[Segment] = []
    if mine:
        trial = star[-1] if star else mine[0]
        figure, files = photo.photo(
            record, trial, layout, "small", trial_word=True, retake=shown.retake(record, trial)
        )
        shown.files += files
        pic = figure
    else:
        pic = _el("p", "never-run", say_text("NEVER_RUN"))
    verdict = next((v for v in record.verdicts if v.hypothesis == hypothesis.id), None)
    summary = [
        *_el("span", "hnum", html.text(pencil(hid, source))),
        *_el("span", "hyp-title", html.text(hypothesis.title.segment())),
        *_el("span", "hyp-expect", [*say_text("EXPECTS"), *html.text(hypothesis.statement.segment())]),
        *_el("span", "hyp-results", _outcome_line(record, hypothesis, outcomes)),
        *_el("span", "hyp-stamps", _row_stamps(record, table, checked, {e.id for e in experiments})),
    ]
    if star:
        summary += _el("span", "newbest", [markup("&#9733; "), *say_text("NEW_BEST")])
    inside: list[Segment] = [
        *_el("p", "sticky-label", say_text("WRITTEN_BY_DRKIRO")),
        *html.text(hypothesis.frozen.text().segment(), block=True),
        *_el(
            "ul", "predictions", [s for p in hypothesis.predictions for s in _prediction(record, p, outcomes)]
        ),
    ]
    for experiment in experiments:
        inside += _experiment(record, layout, experiment, bests, shown)
    if verdict is not None:
        vsrc = _src(record, verdict.seq)
        inside += _el(
            "p",
            "verdict",
            [
                *say_text("VERDICT_ON"),
                *html.text(pencil(hid, vsrc)),
                *say_text("VERDICT_COLON"),
                *html.text(Segment(verdict.verdict, Ink.DRKIRO, vsrc)),
            ],
        )
        inside += html.text(verdict.words.segment(), block=True)
    detail = _el(
        "details",
        "hyp-detail",
        [*_el("summary", "hyp-summary", summary), *_el("section", "sticky-open", inside)],
    )
    return html.element("li", {"class": "hyp", "id": hid}, [*_el("section", "hyp-pic", pic), *detail])


def _experiments(
    record: RecordModel, layout: Layout, chosen: Choices, table: Table | None, shown: Shown
) -> list[Segment]:
    if not record.hypotheses:
        return []
    found = progress.series(record, chosen.progress) if chosen.progress is not None else None
    checked = tables.end_snapshot(record) is not None
    outcomes = {o.prediction: o for o in record.outcomes}
    source = f"{record.name}: all experiments"
    heading = [
        *say_text("ALL_BEFORE"),
        *html.text(pencil(str(len(record.experiments)), source)),
        *say_text("ALL_AFTER"),
    ]
    rows = [
        s
        for h in record.hypotheses
        for s in _hypothesis_row(record, layout, h, found, table, checked, outcomes, shown)
    ]
    return _el(
        "section",
        "experiments",
        [*_el("h3", "cap", heading), *_el("p", "hint", say_text("ALL_HINT")), *_el("ul", "hyps", rows)],
        id="experiments",
    )


# The reader


def _reader(
    record: RecordModel, runs: list[readerruns.Run], requests: dict[str, readerrequest.Request]
) -> list[Segment]:
    mine = [
        r for r in runs if (r.source_application, r.source_session) == (record.application, record.session)
    ]
    if not mine:
        return []
    ids = sorted({r.request_id for r in mine})
    if len(ids) != 1:
        raise NotebookError(record.name, f"the reader section is for one request; the runs hold {len(ids)}")
    request = requests[ids[0]]
    source = f"{readerruns.FOLDER}: the runs of {ids[0]}"
    tiles: list[Segment] = []
    for setup, passes, total, _other in readerruns.tally(mine, ids[0]):
        runs_of = [r for r in mine if r.setup == setup]
        chips: list[Segment] = []
        for run in runs_of:
            chips += html.element(
                "li",
                {"class": f"run run-{run.result}"},
                [*html.text(pencil(run.name, source)), markup(" "), *html.text(pencil(run.result, source))],
            )
        tiles += _el(
            "section",
            f"tile tile-{setup}",
            [
                *_el("p", "cap", say_text(f"READER_SETUP_{setup.upper()}")),
                *_el("p", "tile-big", html.text(pencil(f"{passes}/{total}", source))),
                *_el("p", "tile-about", say_text("READER_PASSED")),
                *_el("ul", "runs", chips),
            ],
        )
    return _el(
        "section",
        "reader",
        [
            *_el("h3", "cap", say_text("READER_HEADING")),
            *_el("p", None, say_text("READER_ABOUT")),
            *_el("blockquote", "request", html.text(commentary(request.words, request.where))),
            *_el("section", "tiles", tiles),
        ],
        id="reader",
    )


# The page body


def body(
    record: RecordModel,
    layout: Layout,
    chosen: Choices,
    lab: Lab,
    runs: list[readerruns.Run],
    requests: dict[str, readerrequest.Request],
    retakes: Retakes,
) -> tuple[list[Segment], list[photo.PictureFile]]:
    """The opened notebook of one session, and the picture files it shows."""
    if chosen.record != record.name:
        raise NotebookError(chosen.file, f"the choice file is for {chosen.record}, not {record.name}")
    shown = Shown([], retakes)
    table, checked = progress.table_of(record)
    title = f"{chosen.title} — {chosen.subtitle}"
    start = f"{chosen.file} key title"
    out = [
        *parts.web("book-web"),
        *_el("span", "holes", [markup("<span></span><span></span><span></span>")], **{"aria-hidden": "true"}),
        *_el("h2", "book-title", [*_human(title, start), *_ours()]),
        *_el("p", "book-summary", [*_human(chosen.summary, f"{chosen.file} key summary"), *_ours()]),
        *_chips(record, chosen, lab, table),
        *_highlight(record, layout, chosen, table, shown),
        *_spec(record, table, checked),
        *_plan(record),
        *_experiments(record, layout, chosen, table, shown),
        *_reader(record, runs, requests),
    ]
    unique: dict[str, photo.PictureFile] = {}
    for picture in shown.files:
        unique.setdefault(picture.path, picture)
    return out, list(unique.values())
