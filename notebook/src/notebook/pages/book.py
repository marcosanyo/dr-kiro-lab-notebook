"""The opened notebook: one session as a story (notebook-shelf design 4 to 9).
The first screen says what was found: the claim, the summary, the chips, the two large photos with their
handwritten line, three sticky notes with numbers from the record, and the best so far trial by trial. Below
it come the discovered spec, Dr. Kiro's plan, every experiment with its hypothesis, and the reader's results.
The title, the summary and the words on the photos are written by a person (choice file, orange pen); every
number comes from the record; Dr. Kiro's words keep Dr. Kiro's ink.
"""

import hashlib
import math
import re
from dataclasses import dataclass

from bench.specfiles.discovered import Row, Table

from notebook import addresses, html, numbers, progress, readerrequest, readerruns, refusals, tables, text
from notebook.choices import App, Choices, Note, Polaroid
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
SEALED = "sealed"
AT_BENCH = "at_bench"
MODES = (SEALED, AT_BENCH)
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
    track: tuple[str, str] | None = None  # the application's track series (`App.track`)

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


def _chips(
    record: RecordModel, chosen: Choices | None, lab: App, table: Table | None, mode: str = SEALED
) -> list[Segment]:
    """`chosen` is None at the bench: the model and the date are a person's words, written after the seal."""
    source = f"{record.name}: chips"
    counts = progress.predictions(record)
    chips: list[list[Segment]] = []
    if chosen is not None:
        chips.append([*say_text("CHIP_MODEL"), *_human(chosen.model, f"{chosen.file} key model")])
    chips.append(
        [
            *html.text(pencil(str(len(record.trials)), source)),
            markup(" "),
            *_human(lab.unit_one if len(record.trials) == 1 else lab.unit, lab.source),
        ]
    )
    if chosen is not None:
        chips.append([*say_text("CHIP_DATE"), *_human(chosen.date, f"{chosen.file} key date")])
    if record.variant is not None:
        chips.append(
            [*say_text("CHIP_BODY"), *html.text(pencil(record.variant, f"{record.name}: start entry"))]
        )
    elif chosen is not None and chosen.body is not None:
        chips.append([*say_text("CHIP_BODY"), *_human(chosen.body, f"{chosen.file} key body")])
    if table is None:
        running = mode == AT_BENCH and record.seal is None
        chips.append(say_text("CHIP_NO_TABLE_YET" if running else "CHIP_NO_TABLE"))
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
    chips.append(
        [
            *html.text(pencil(str(counts.hit), source)),
            *say_text("OF"),
            *html.text(pencil(str(counts.total), source)),
            *say_text("CHIP_PREDICTIONS"),
        ]
    )
    if record.seal is not None and record.seal.end == "stopped":
        chips.append([*say_text("CHIP_STOPPED"), *html.text(record.seal.reason.segment())])
    return _el("ul", "chips", [s for chip in chips for s in html.element("li", None, chip)])


def _sentence(source: str, *pieces: str) -> list[Segment]:
    """One sentence of the story: a piece that starts with `@` is a string of `text.py` (our words); any other
    piece is a number the notebook counted from the record, in pencil."""
    out: list[Segment] = []
    for piece in pieces:
        out += say_text(piece[1:]) if piece.startswith("@") else html.text(pencil(piece, source))
    return out


def _own(record: RecordModel, runs: list[readerruns.Run]) -> list[readerruns.Run]:
    """The reader's runs made from this session's record, on the body this session ran on."""
    return [
        r
        for r in runs
        if (r.source_application, r.source_session) == (record.application, record.session)
        and r.variant == record.variant
    ]


def _borrowed(record: RecordModel, runs: list[readerruns.Run]) -> list[readerruns.Run]:
    """The reader's runs on this session's body that were given another session's spec: an earlier spec tried
    on a body that has changed since. Only a record with a body label has them."""
    if record.variant is None:
        return []
    return [
        r
        for r in runs
        if r.source_application == record.application
        and r.source_session != record.session
        and r.variant == record.variant
        and r.setup == "spec"
    ]


def _story(
    record: RecordModel, table: Table | None, runs: list[readerruns.Run], mode: str = SEALED
) -> list[Segment]:
    """What happened in this session, in three steps joined by arrows. Every number is counted from the
    record, the table or the reader's runs; the words are plain English. At the bench before the seal the
    second and third steps say what is so far and when the rest comes (Requirement 23.7), never 'final'."""
    running = mode == AT_BENCH and record.seal is None
    source = f"{record.name}: what happened"
    counts = progress.predictions(record)
    registered = sum(len(h.predictions) for h in record.hypotheses)
    head = [
        *_el("h3", "cap", say_text("STORY_HEADING")),
    ]
    if registered == 0:
        return _el("section", "story", [*head, *_el("p", "story-none", say_text("STORY_NONE"))], id="story")
    first = _sentence(
        source,
        "@STORY_WROTE_BEFORE",
        str(registered),
        "@STORY_WROTE_AFTER_ONE" if registered == 1 else "@STORY_WROTE_AFTER",
    )
    stopped = record.seal is not None and record.seal.end == "stopped"
    if stopped:
        second = _sentence(source, str(counts.hit), "@OF", str(counts.total), "@STORY_CHECKED_STOPPED")
    elif running:
        second = _sentence(source, str(counts.miss), "@STORY_MISSED_SO_FAR")
    elif table is None:
        second = _sentence(source, str(counts.miss), "@STORY_MISSED_NO_TABLE")
    else:
        rejected = progress.status_counts(table)["rejected"]
        missed = {o.prediction for o in record.outcomes if o.outcome == "miss"}
        # Rows that cite a missed prediction and are not validated: what the misses changed, when no rule
        # had to be struck out.
        left = [
            (r.id, r.status)
            for r in table.rows
            if r.status in ("partly", "observed") and missed & set(r.predictions)
        ]
        if rejected:
            second = _sentence(
                source,
                str(counts.miss),
                "@STORY_MISSED",
                str(rejected),
                "@STORY_STRUCK_ONE" if rejected == 1 else "@STORY_STRUCK",
            )
        elif left:
            pieces: list[str] = [
                str(counts.miss),
                "@STORY_MISSED_LEFT" if counts.miss == 1 else "@STORY_MISSES_LEFT",
            ]
            for n, (row_id, status) in enumerate(left):
                if n:
                    pieces.append("@LIST_SEPARATOR")
                pieces += [row_id, "@STORY_LEFT_AS", status]
            pieces.append("@STORY_LEFT_END")
            second = _sentence(source, *pieces)
        else:
            second = _sentence(source, str(counts.miss), "@STORY_MISSED_NONE_STRUCK")
    mine = _own(record, runs)
    if running:
        third = say_text("STORY_AT_BENCH")
    elif mine:
        tally = {
            setup: (passes, total) for setup, passes, total, _ in readerruns.tally(mine, mine[0].request_id)
        }
        spec, none = tally["spec"], tally["none"]
        third = _sentence(
            source,
            "@STORY_READER_A",
            str(spec[0]),
            "@OF",
            str(spec[1]),
            "@STORY_READER_B",
            str(none[0]),
            "@OF",
            str(none[1]),
            "@STORY_END",
        )
        for session in sorted({r.source_session for r in _borrowed(record, runs)}):
            theirs = [r for r in _borrowed(record, runs) if r.source_session == session]
            third += _sentence(
                source,
                "@STORY_BORROWED_A",
                session,
                "@STORY_BORROWED_B",
                str(sum(1 for r in theirs if r.result == "pass")),
                "@OF",
                str(len(theirs)),
                "@STORY_END",
            )
    elif table is not None:
        by = progress.status_counts(table)
        rest = by["partly"] + by["observed"]
        third = _sentence(
            source,
            str(by["validated"]),
            "@STORY_TRUST_A_ONE" if by["validated"] == 1 else "@STORY_TRUST_A",
            str(rest),
            "@STORY_TRUST_B_ONE" if rest == 1 else "@STORY_TRUST_B",
        )
    else:
        third = say_text("STORY_NO_SPEC")
    steps = [
        s
        for n, words in enumerate((first, second, third), start=1)
        for s in html.element("li", {"class": f"story-step story-{n}"}, words)
    ]
    return _el(
        "section",
        "story",
        [*head, *_el("ol", "story-steps", steps)],
        id="story",
    )


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


def _note(
    record: RecordModel,
    found: progress.Series,
    table: Table | None,
    lab: App,
    note: Note,
    outcomes: dict[str, Outcome],
) -> tuple[list[Segment], list[Segment]]:
    """The big number and the few words of one sticky note, from the record (the person chose which)."""
    source = f"{record.name}: sticky note {note.kind}"
    counts = progress.predictions(record)
    if note.kind == "best":
        best = found.best
        text_ = progress.best_value_text(found)
        if best is None or text_ is None:
            return html.text(pencil("-", source)), say_text("NOTE_NO_BEST")
        return html.text(pencil(text_, source)), [
            *say_text("NOTE_BEST_BEFORE"),
            *html.text(pencil(found.spec.measurement, source)),
            *say_text("NOTE_BEST_AFTER"),
            *html.text(pencil(f"{best.trial.id} ({best.hypothesis})", source)),
        ]
    if note.kind == "hits":
        return html.text(pencil(f"{counts.hit}/{counts.total}", source)), say_text("NOTE_HITS")
    if note.kind == "rejected":
        if table is not None:
            return html.text(pencil(str(progress.status_counts(table)["rejected"]), source)), say_text(
                "NOTE_REJECTED_RULES"
            )
        rejected = sum(1 for v in record.verdicts if v.verdict == "rejected")
        return html.text(pencil(str(rejected), source)), say_text("NOTE_REJECTED_VERDICTS")
    if note.kind == "trials":
        return html.text(pencil(f"{len(record.trials)}/{record.budget}", source)), [
            *_human(lab.unit, lab.source),
            *say_text("NOTE_TRIALS_USED"),
        ]
    outcome = outcomes[note.prediction]
    prediction = next(p for h in record.hypotheses for p in h.predictions if p.id == note.prediction)
    unit = _unit(record, prediction.measurement)
    where = f"{source}: {note.prediction}"
    low = numbers.brief(prediction.low, unit, where)
    high = numbers.brief(prediction.high, unit, where)
    return html.text(pencil(numbers.brief(outcome.value, unit, where), source)), [
        *html.text(pencil(note.prediction, source)),
        *say_text("NOTE_MISSED"),
        *html.text(pencil(prediction.measurement, source)),
        *say_text("NOTE_EXPECTED"),
        *html.text(pencil(f"{low} to {high}", source)),
    ]


def _notes(
    record: RecordModel,
    found: progress.Series,
    table: Table | None,
    chosen: Choices,
    lab: App,
) -> list[Segment]:
    outcomes = {o.prediction: o for o in record.outcomes}
    styles = ("note-yellow tilt-one", "note-pink tilt-two", "note-blue tilt-three")
    out: list[Segment] = []
    for style, note in zip(styles, chosen.notes, strict=True):
        big, about = _note(record, found, table, lab, note, outcomes)
        out += _el("aside", f"note {style}", [*_el("p", "note-big", big), *_el("p", "note-about", about)])
    return _el("section", "notes", out)


def _value_text(value: float, unit: str, where: str) -> str:
    return f"{numbers.short(value, where)} {unit}".strip()


def _jitter(seed: str, k: int) -> float:
    """A number from -1 to 1 that depends only on the seed and k, so the same record always draws the same
    line."""
    digest = hashlib.sha256(f"{seed}:{k}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF * 2 - 1


def _pencil_line(corners: list[tuple[float, float]], seed: str) -> str:
    """The step line as a path that wavers a little between its corners, like a line drawn by hand. The
    corners themselves are exact."""
    out = f"M{corners[0][0]:.1f} {corners[0][1]:.1f}"
    k = 0
    for (x0, y0), (x1, y1) in zip(corners, corners[1:], strict=False):
        length = math.hypot(x1 - x0, y1 - y0) or 1.0
        pieces = max(2, int(length / 9))
        for j in range(1, pieces + 1):
            px, py = x0 + (x1 - x0) * j / pieces, y0 + (y1 - y0) * j / pieces
            if j < pieces:
                k += 1
                wobble = _jitter(seed, k) * 2.4
                px += -(y1 - y0) / length * wobble
                py += (x1 - x0) / length * wobble
            out += f"L{px:.1f} {py:.1f}"
    return out


def _chart(record: RecordModel, found: progress.Series) -> list[Segment]:
    """The best so far after every trial, as a step line. Only the largest steps up are named, each with its
    hypothesis and the change ("H10: +9.2 cm"), and no two names overlap."""
    source = f"{record.name}: progress"
    width, height, left, right, top, bottom = 520.0, 250.0, 62.0, 16.0, 40.0, 30.0
    points = found.points
    bests = [p.best for p in points if p.best is not None]
    if not bests:
        return _el("p", "chart-none", say_text("PROGRESS_NONE"))
    # The axis fits the line, so the line never lies on the bottom of the frame.
    low, high = min(bests), max(bests)
    pad = (high - low) * 0.25 or abs(high) * 0.05 or 1.0
    low, high = low - pad, high + pad
    n = len(points)
    unit = found.unit

    def x(i: int) -> float:
        return left + (width - left - right) * (i / (n - 1) if n > 1 else 0.5)

    def y(v: float) -> float:
        return top + (height - top - bottom) * (1 - (v - low) / (high - low))

    marks: list[Segment] = []
    for v in sorted({min(bests), max(bests)}):
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
    corners: list[tuple[float, float]] = []
    for i, p in enumerate(points):
        if p.best is None:
            continue
        if corners and abs(corners[-1][1] - y(p.best)) > 0.01:
            corners += [(x(i), corners[-1][1]), (x(i), y(p.best))]
        elif not corners:
            corners.append((x(i), y(p.best)))
    corners.append((x(n - 1), corners[-1][1]))
    # The line, and a second fainter pass of the pencil beside it.
    line = _pencil_line(corners, record.name)
    marks += html.element("path", {"class": "ch-line", "d": line, "fill": "none"}, [])
    marks += html.element(
        "path", {"class": "ch-pass", "d": _pencil_line(corners, f"{record.name}:second"), "fill": "none"}, []
    )
    if found.mark_index is not None:
        m = found.mark_index
        marks += html.shape(
            "line",
            {
                "class": "ch-mark",
                "x1": f"{x(m):.1f}",
                "x2": f"{x(m):.1f}",
                "y1": f"{top - 12}",
                "y2": f"{height - bottom + 6}",
            },
        )
        marks += html.element(
            "text",
            {"class": "ch-flag", "x": f"{x(m):.1f}", "y": f"{height - 6}"},
            [commentary(found.spec.mark_words, f"{found.spec.source} key mark_words")],
        )
    span = max(bests) - min(bests)
    steps = [
        (i, p)
        for i, p in enumerate(points)
        if p.improved and p.delta is not None and abs(p.delta) >= LABEL_SHARE * span
    ]
    steps.sort(key=lambda item: -abs(item[1].delta))
    named: list[tuple[float, float, float]] = []  # (left, right, y) of each name
    shown_steps: list[tuple[int, str, float, float, float]] = []
    for i, p in steps[:MAX_LABELS]:
        text = f"{p.hypothesis}: {numbers.brief(p.delta, unit, source, signed=True)}"
        size = LABEL_CHAR * len(text)
        end = x(i) > width * 0.6
        box_left, box_right = (x(i) - 10 - size, x(i) - 10) if end else (x(i) + 8, x(i) + 8 + size)
        for dy in (-12, -32, 22):
            at = y(p.best) + dy
            if box_left < 0 or box_right > width or at < 12 or at > height - bottom:
                continue
            if all(box_right < a or box_left > b or abs(at - c) > LABEL_HEIGHT for a, b, c in named):
                named.append((box_left, box_right, at))
                shown_steps.append((i, text, at, 0.0 if not end else 1.0, y(p.best)))
                break
    for i, p in enumerate(points):
        if p.improved and p.best is not None:
            marks += html.shape(
                "circle", {"class": "ch-best", "cx": f"{x(i):.1f}", "cy": f"{y(p.best):.1f}", "r": "4"}
            )
    for i, label, at, end, dot in shown_steps:
        edge = x(i) - 8 if end else x(i) + 6
        aim = (x(i) - 3, dot - 5) if at < dot else (x(i) - 3, dot + 5)
        marks += html.element(
            "path",
            {
                "class": "ch-leader",
                "fill": "none",
                "d": f"M{edge:.1f} {at + (3 if at < dot else -9):.1f} Q{edge + (3 if end else -3):.1f} "
                f"{(at + dot) / 2:.1f} {aim[0]:.1f} {aim[1]:.1f}",
            },
            [],
        )
        cls = "ch-note ch-note-end" if end else "ch-note"
        marks += html.element(
            "text",
            {"class": cls, "x": f"{x(i) - (10 if end else -8):.1f}", "y": f"{at:.1f}"},
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
    if found.spec.mark is not None and found.mark_index is not None:
        caption += [
            *say_text("PROGRESS_MARK_A"),
            *html.text(
                pencil(f"{found.spec.mark} = {numbers.short(found.spec.mark_equals, source)}", source)
            ),
            *say_text("PROGRESS_MARK_B"),
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
    lab: App,
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
    side = _el("section", "side", [*_notes(record, found, table, chosen, lab), *_chart(record, found)])
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
    label: str,
    known: set[str],
) -> list[Segment]:
    """One compact card: the id and stamp, the rule, and where it was rewritten. The scope and the evidence
    are in a closed note."""
    rv = view.rows[index]
    row = rv.row
    src = f"{snapshot.design.source} line {row.line}"
    head = [
        *html.text(_cell(snapshot, row, row.id)),
        *stamp(stamp_segment(row.status, src), label),
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
    if refusals.refused_end_note(row.id, record.refusals) is not None:
        # The end refusals are shown once above the table (`_end_refusals`); a row they name gets this mark.
        body += _el("span", "refused-mark", [], **{"aria-hidden": "true"})
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


def _spec(record: RecordModel, table: Table | None, checked: bool, mode: str) -> list[Segment]:
    """At the bench every status is labelled "not yet checked by the bench", whatever the latest snapshot
    is, and the note about an unchecked table is left out."""
    label = "NOT_YET_CHECKED" if mode == AT_BENCH else "CHECKED" if checked else "NOT_CHECKED"
    head = [*_el("h3", "cap", say_text("SPEC_HEADING")), *_el("p", "intro", say_text("SPEC_INTRO"))]
    snapshot = tables.end_snapshot(record) or (record.snapshots[-1] if record.snapshots else None)
    if table is None or snapshot is None:
        return _el("section", "spec", [*head, *_el("p", None, say_text("SPEC_NONE"))], id="spec")
    view = tables.table_view(table)
    known = _anchors(record)
    items = [s for i in range(len(view.rows)) for s in _rule(record, snapshot, view, i, label, known)]
    note = [] if checked or mode == AT_BENCH else _el("p", "spec-note", say_text("SPEC_UNCHECKED"))
    ended = _end_refusals(record)
    return _el("section", "spec", [*head, *note, *ended, *_el("ul", "rules", items)], id="spec")


def _end_refusals(record: RecordModel) -> list[Segment]:
    """The session's `end` refusals, once above the table: the heading with the count, each message as the
    bench recorded it, and the quote note once. Nothing is added to what the messages say."""
    ends = [r for r in record.refusals if r.action == "end"]
    if not ends:
        return []
    source = f"{record.name}/log.jsonl: end refusals"
    messages = [refusals.message(r) for r in ends]
    items = [_el("li", None, list(m.parts)) for m in messages]
    quote = _el("p", "rule-refused-quote", [messages[0].note]) if messages[0].note is not None else []
    return _el(
        "section",
        "end-refusals",
        [
            *_el("p", "end-refusals-head", list(refusals.end_heading(len(ends), source))),
            *_el("p", "rule-refused-sealed", [refusals.sealed_note()]),
            *_el("ul", "end-refusals-list", [s for item in items for s in item]),
            *quote,
        ],
    )


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
            *_el("p", "intro", say_text("PLAN_INTRO")),
            *_el("p", "hint", say_text("PLAN_HINT")),
            *_el("ol", "plan-list", items),
        ],
        id="plan",
    )


# Every experiment and hypothesis


def _waiting(record: RecordModel, mode: str, hypothesis: str) -> bool:
    """At the bench, a prediction with no outcome entry is waiting until its hypothesis has a verdict. After
    the verdict (whose flag counts it as not run, 23.10), or once the seal entry is in the prefix, it was not
    run, as on the finished page."""
    if mode != AT_BENCH or record.seal is not None:
        return False
    return not any(v.hypothesis == hypothesis for v in record.verdicts)


def _outcome_line(
    record: RecordModel, hypothesis: Hypothesis, outcomes: dict[str, Outcome], mode: str
) -> list[Segment]:
    out: list[Segment] = []
    for i, prediction in enumerate(hypothesis.predictions):
        source = _src(record, hypothesis.seq)
        if i:
            out += say_text("LIST_SEPARATOR")
        outcome = outcomes.get(prediction.id)
        short = prediction.id.split(".")[-1]
        if outcome is None:
            out += [
                *html.text(pencil(short, source)),
                *say_text("OUTCOME_WAITING" if _waiting(record, mode, hypothesis.id) else "OUTCOME_NOT_RUN"),
            ]
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


def _prediction(record: RecordModel, prediction, outcomes: dict[str, Outcome], mode: str) -> list[Segment]:
    """One registered prediction as a line to read: "x in [0.1, 2] when a0 = 1, f = 1 -> hit"."""
    owner = next(h for h in record.hypotheses if prediction in h.predictions)
    source = _src(record, owner.seq)
    where = f"{source}: {prediction.id}"
    outcome = outcomes.get(prediction.id)
    line = [
        *html.text(pencil(prediction.id, source)),
        markup(" "),
        *html.text(pencil(prediction.measurement, source)),
        *say_text("PREDICTION_IN"),
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
    line += [markup(" &rarr; ")]
    if outcome is None and _waiting(record, mode, owner.id):
        line += say_text("PREDICTION_WAITING")
    elif outcome is None:
        line += html.text(pencil("not run", source))
    else:
        word = html.text(pencil(outcome.outcome, source))
        line += _el("span", "miss", word) if outcome.outcome == "miss" else word
        if outcome.value is not None:
            shown = numbers.short(outcome.value, f"{_src(record, outcome.seq)}: {prediction.id}")
            line += html.text(pencil(f" ({prediction.measurement} {shown})", source))
    line += [
        markup(" "),
        *_el(
            "span",
            "label-k",
            [*say_text("PREDICTION_LABEL"), *html.text(Segment(prediction.label, Ink.DRKIRO, source))],
        ),
    ]
    return html.element("li", {"id": addresses.never_run(prediction.id, source)}, line)


def _frozen(hypothesis: Hypothesis) -> list[Segment]:
    """Dr. Kiro's hypothesis text as it reads: the heading as a heading, the sentence as a paragraph. The
    fenced prediction block is left out here; the predictions are listed under it, one line each."""
    frozen = hypothesis.frozen.text()
    out: list[Segment] = []
    fence: str | None = None
    for number, line in enumerate(frozen.text.splitlines(), start=1):
        source = f"{frozen.source} line {number}"
        if line.startswith("```"):
            fence = None if fence is not None else line[3:].strip()
            continue
        if fence is not None or not line.strip():
            continue
        heading = re.match(r"^#{1,6}\s+(.*)$", line)
        piece = Authored(heading.group(1) if heading else line, frozen.author, source).segment()
        out += _el("h4" if heading else "p", "frozen-title" if heading else "frozen-text", html.text(piece))
    return out


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
    words = [*_el("p", "trial-params", params), *_el("p", "pol-values", values)]
    card = "trial-card"
    # A retaken picture carries the track in its corner map; a card without one gets the sketch (10.10).
    if shown.track is not None and shown.retake(record, trial) is None:
        kinds = {m.name: m.kind for m in record.declaration.measurements}
        words += photo.track_sketch(trial, shown.track, kinds, source)
        card = "trial-card with-track"
    return html.element(
        "li",
        {"class": card, "id": addresses.trial(experiment.id, trial.id, source)},
        [*figure, *words],
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
    mode: str,
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
        not_yet = mode == AT_BENCH and record.seal is None
        pic = _el("p", "never-run", say_text("NOT_RUN_YET" if not_yet else "NEVER_RUN"))
    verdict = next((v for v in record.verdicts if v.hypothesis == hypothesis.id), None)
    summary = [
        *_el("span", "hnum", html.text(pencil(hid, source))),
        *_el("span", "hyp-title", html.text(hypothesis.title.segment())),
        *_el("span", "hyp-expect", [*say_text("EXPECTS"), *html.text(hypothesis.statement.segment())]),
        *_el("span", "hyp-results", _outcome_line(record, hypothesis, outcomes, mode)),
        *_el("span", "hyp-stamps", _row_stamps(record, table, checked, {e.id for e in experiments})),
    ]
    # At the bench, the hypothesis that is registered and has no verdict yet is the one being run (23.9).
    running = mode == AT_BENCH and record.seal is None and verdict is None
    if running:
        summary += _el("span", "at-bench-mark", say_text("AT_BENCH"))
    if star:
        summary += _el("span", "newbest", [markup("&#9733; "), *say_text("NEW_BEST")])
    inside: list[Segment] = [
        *_el("p", "sticky-label", say_text("WRITTEN_BY_DRKIRO")),
        *_frozen(hypothesis),
        *_el(
            "ul",
            "predictions",
            [s for p in hypothesis.predictions for s in _prediction(record, p, outcomes, mode)],
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
        **({"open": "open"} if running else {}),
    )
    return html.element("li", {"class": "hyp", "id": hid}, [*_el("section", "hyp-pic", pic), *detail])


def _experiments(
    record: RecordModel, layout: Layout, chosen: Choices | None, table: Table | None, shown: Shown, mode: str
) -> list[Segment]:
    if not record.hypotheses:
        return []
    found = (
        progress.series(record, chosen.progress)
        if chosen is not None and chosen.progress is not None
        else None
    )
    checked = mode == SEALED and tables.end_snapshot(record) is not None
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
        for s in _hypothesis_row(record, layout, h, found, table, checked, outcomes, shown, mode)
    ]
    return _el(
        "section",
        "experiments",
        [
            *_el("h3", "cap", heading),
            *_el("p", "intro", say_text("ALL_INTRO")),
            *_el("p", "hint", say_text("ALL_HINT")),
            *_el("ul", "hyps", rows),
        ],
        id="experiments",
    )


# The reader


def _run_line(
    run: readerruns.Run, source: str, rows: set[str], known: set[str], page: str | None = None
) -> list[Segment]:
    """One run: its name and result, the trial at which it was first in range (or that it never was) and its
    last trial, and the ids it said it relied on, linked where the page holds them."""
    out = [*html.text(pencil(run.name, source)), markup(" "), *html.text(pencil(run.result, source))]
    if run.first_in_range is None:
        out += [*say_text("READER_RUN_NEVER"), *html.text(pencil(run.last_trial, source))]
    else:
        out += [
            *say_text("READER_RUN_FIRST"),
            *html.text(pencil(run.first_in_range, source)),
            *say_text("READER_RUN_LAST"),
            *html.text(pencil(run.last_trial, source)),
        ]
    cited = [i for i in run.relied_ids if i != "none"]
    if not cited:
        return [*out, *say_text("READER_RUN_CITED_NONE")]
    out += say_text("READER_RUN_CITED")
    for n, item in enumerate(cited):
        if n:
            out += say_text("LIST_SEPARATOR")
        piece = html.text(pencil(item, source))
        if item in rows:
            anchor = addresses.row(item, source)
            out += link(addresses.on_page(page, anchor) if page else addresses.here(anchor), piece)
        elif item in known and page is None:
            out += link(addresses.here(item), piece)
        else:
            out += piece
    return out


def _limits(runs: list[readerruns.Run], request: readerrequest.Request, source: str) -> list[Segment]:
    """The budget of each run and the pass ranges, one line under the request sentence. A run whose budget
    or units differ from the others, or a pass measurement no run declares, fails the build.
    Nothing is filled in."""
    budgets = {r.budget for r in runs}
    if len(budgets) != 1:
        raise NotebookError(source, f"the runs of {request.id!r} hold {len(budgets)} different budgets")
    units = dict(runs[0].units)
    for run in runs:
        if dict(run.units) != units:
            raise NotebookError(run.where, "its declared units differ from the other runs of this request")
    if not request.passes:
        raise NotebookError(request.where, "the request holds no pass range")
    ranges: list[Segment] = []
    for i, item in enumerate(request.passes):
        if item.measurement not in units:
            raise NotebookError(
                request.where, f"pass {i + 1} names {item.measurement!r}, which the runs do not declare"
            )
        unit = units[item.measurement]
        if i:
            ranges += say_text("LIST_SEPARATOR")
        ranges += html.text(pencil(f"{item.measurement} {item.low:g}", source))
        ranges += say_text("READER_LIMIT_TO")
        ranges += html.text(pencil(f"{item.high:g} {unit}", source))
    budget = budgets.pop()
    return [
        *_el(
            "p",
            "reader-limits",
            [
                *say_text("READER_LIMIT_BUDGET"),
                *html.text(pencil(str(budget), source)),
                *say_text("READER_LIMIT_TRIALS"),
                *say_text("LINK_SEPARATOR"),
                *say_text("READER_LIMIT_PASS"),
                *ranges,
            ],
        )
    ]


def setup_caption(setup: str, session: str, source: str, has_old_spec: bool) -> list[Segment]:
    """The heading of one column of the reader's test. With an old spec beside it, the spec column is the new
    spec, so the three columns read old spec, new spec, no spec."""
    if setup == "spec" and has_old_spec:
        return [*say_text("READER_SETUP_NEW"), *html.text(pencil(session, source))]
    return say_text(f"READER_SETUP_{setup.upper()}")


def _reader(
    record: RecordModel,
    runs: list[readerruns.Run],
    requests: dict[str, readerrequest.Request],
    table: Table | None,
    others: dict[str, RecordModel],
) -> list[Segment]:
    mine = _own(record, runs)
    if not mine:
        return []
    ids = sorted({r.request_id for r in mine})
    if len(ids) != 1:
        raise NotebookError(record.name, f"the reader section is for one request; the runs hold {len(ids)}")
    request = requests[ids[0]]
    source = f"{readerruns.FOLDER}: the runs of {ids[0]}"
    tiles: list[Segment] = []
    for session in sorted({r.source_session for r in _borrowed(record, runs)}):
        theirs = [r for r in _borrowed(record, runs) if r.source_session == session]
        for r in theirs:
            if requests[r.request_id].words != request.words:
                raise NotebookError(
                    record.name, f"{r.name} asked {r.request_id!r}, whose words differ from {ids[0]!r}"
                )
        other = others.get(session)
        if other is None:
            raise NotebookError(
                record.name, f"{theirs[0].name} names source {session!r}, which has no record"
            )
        other_table, _ = progress.table_of(other)
        other_rows = {r.id for r in other_table.rows} if other_table is not None else set()
        page = addresses.session(other.application, other.session, other.name)
        chips: list[Segment] = []
        for run in theirs:
            chips += html.element(
                "li",
                {"class": f"run run-{run.result}"},
                _run_line(run, source, other_rows, set(), page),
            )
        relied = sorted(
            {i for r in theirs for i in r.relied_ids if i in other_rows}, key=lambda i: int(i[1:])
        )
        snapshot = tables.end_snapshot(other) or (other.snapshots[-1] if other.snapshots else None)
        if relied and snapshot is not None and other_table is not None:
            by_id = {r.id: r for r in other_table.rows}
            said: list[Segment] = []
            for rid in relied:
                row = by_id[rid]
                said += html.element(
                    "li",
                    None,
                    [
                        *html.text(pencil(rid, source)),
                        markup(" "),
                        *html.text(_cell(snapshot, row, row.rule)),
                    ],
                )
            chips += _el(
                "li", "run-limit", [*say_text("READER_BORROWED_RULES"), *_el("ul", "borrowed-rules", said)]
            )
        passes = sum(1 for r in theirs if r.result == "pass")
        tiles += _el(
            "section",
            "tile tile-borrowed",
            [
                *_el("p", "cap", [*say_text("READER_SETUP_BORROWED"), *html.text(pencil(session, source))]),
                *_el("p", "tile-big", html.text(pencil(f"{passes}/{len(theirs)}", source))),
                *_el("p", "tile-about", say_text("READER_PASSED")),
                *_el("ul", "runs", chips),
            ],
        )
    rows = {r.id for r in table.rows} if table is not None else set()
    known = _anchors(record) | {h.id for h in record.hypotheses}
    for setup, passes, total, _other in readerruns.tally(mine, ids[0]):
        runs_of = [r for r in mine if r.setup == setup]
        chips: list[Segment] = []
        for run in runs_of:
            chips += html.element(
                "li", {"class": f"run run-{run.result}"}, _run_line(run, source, rows, known)
            )
        limits = sorted({limit for run in runs_of for limit in run.limits})
        for limit in limits:
            chips += _el(
                "li", "run-limit", [*say_text("READER_RUN_LIMIT"), *html.text(pencil(limit, source))]
            )
        tiles += _el(
            "section",
            f"tile tile-{setup}",
            [
                *_el("p", "cap", setup_caption(setup, record.session, source, bool(_borrowed(record, runs)))),
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
            *_el("p", "intro", say_text("READER_INTRO")),
            *_el("p", None, say_text("READER_ABOUT")),
            *_el("blockquote", "request", html.text(commentary(request.words, request.where))),
            *_limits(mine, request, source),
            *_el("section", "tiles", tiles),
        ],
        id="reader",
    )


# The page body
def _after_seal(heading: str, line: str, cls: str, **attrs: str) -> list[Segment]:
    """A part that only a person or a later run writes: its heading and one line saying when it comes."""
    return _el(
        "section",
        cls,
        [*_el("h3", "cap", say_text(heading)), *_el("p", "after-seal", say_text(line))],
        **attrs,
    )


def _at_bench_head(record: RecordModel, replay: bool, finished: str | None) -> list[Segment]:
    """The head of the page at the bench: the label and the session id in place of the title, the heading of
    the summary with the line saying when it comes, and the sealed statement once the seal entry is in. A
    replay of a sealed record says so in place of "at the bench" (16.7). `finished` is the address of the
    session's finished page when the watch was given a built site that holds it."""
    source = _src(record, 1)
    head = [
        *_el(
            "h2",
            "book-title",
            [
                *html.text(pencil(record.session, source)),
                markup(" "),
                *_el("span", "at-bench-label", say_text("REPLAY_LABEL" if replay else "AT_BENCH")),
            ],
        ),
        *_after_seal("SUMMARY_HEADING", "WRITTEN_AFTER_SEAL", "book-summary"),
    ]
    if record.seal is not None:
        banner = say_text("SEALED_BANNER")
        if finished is not None:
            banner += [markup(" "), *html.element("a", {"href": finished}, say_text("FINISHED_PAGE"))]
        head += _el("p", "sealed-banner", banner)
    return head


def body(
    record: RecordModel,
    layout: Layout,
    chosen: Choices | None,
    lab: App,
    runs: list[readerruns.Run],
    requests: dict[str, readerrequest.Request],
    retakes: Retakes,
    others: dict[str, RecordModel] | None = None,
    mode: str = SEALED,
    *,
    replay: bool = False,
    finished: str | None = None,
) -> tuple[list[Segment], list[photo.PictureFile]]:
    """The opened notebook of one session, and the picture files it shows. `mode` is `sealed` (the build) or
    `at_bench` (the watch, notebook-watch design N34): at the bench there is no choice file, so `chosen` is
    None, and the parts a person or a later run writes show their heading and when they come."""
    if mode not in MODES:
        raise NotebookError(record.name, f"the page mode must be one of {', '.join(MODES)}, not {mode!r}")
    if (mode == AT_BENCH) != (chosen is None):
        raise NotebookError(
            record.name, "a page at the bench has no choice file, and a sealed page needs one"
        )
    others = others or {}
    shown = Shown([], retakes, lab.track)
    holes = _el(
        "span", "holes", [markup("<span></span><span></span><span></span>")], **{"aria-hidden": "true"}
    )
    web = [*parts.web("book-web"), *parts.page_marks()] if lab.decoration != "none" else []
    if chosen is None:
        table, _ = progress.table_of(record)
        out = [
            *web,
            *holes,
            *_at_bench_head(record, replay, finished),
            *_story(record, table, [], mode),
            *_chips(record, None, lab, table, mode),
            *_after_seal("HIGHLIGHT_HEADING", "WRITTEN_AFTER_SEAL", "highlight", id="highlight"),
            *_after_seal("READER_HEADING", "RUNS_AFTER_SEAL", "reader", id="reader"),
            *_spec(record, table, False, mode),
            *_plan(record),
            *_experiments(record, layout, None, table, shown, mode),
        ]
    else:
        if chosen.record != record.name:
            raise NotebookError(chosen.file, f"the choice file is for {chosen.record}, not {record.name}")
        table, checked = progress.table_of(record)
        start = f"{chosen.file} key title"
        out = [
            *web,
            *holes,
            *_el(
                "h2",
                "book-title",
                [
                    *_human(chosen.title, start),
                    *_ours(),
                    *_el("span", "book-sub", _human(chosen.subtitle, start)),
                ],
            ),
            *_el("p", "book-summary", [*_human(chosen.summary, f"{chosen.file} key summary"), *_ours()]),
            *_chips(record, chosen, lab, table),
            *_highlight(record, layout, chosen, table, lab, shown),
            *_story(record, table, runs),
            *_reader(record, runs, requests, table, others),
            *_spec(record, table, checked, mode),
            *_plan(record),
            *_experiments(record, layout, chosen, table, shown, mode),
        ]
    unique: dict[str, photo.PictureFile] = {}
    for picture in shown.files:
        unique.setdefault(picture.path, picture)
    return out, list(unique.values())
