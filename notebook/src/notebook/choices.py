"""The settings of an application's notebook and the choice files of its sessions (notebook-shelf design 2).
An application's notebook folder (`<application>/notebook/`) holds `app.toml`, the choice files
`choices/<session-id>.toml` and, when the application has retaken pictures, a display folder.
`app.toml` says how the application's notebook opens: its place in the order of the cases, the text of its
tab and of its door on the front page, the description under the title, the session whose notebook the first
page opens, the word for one budgeted step, the theme it opens in (day or night), the colour of the pen of our
notes (blue or orange) and the decoration (none or halloween).
A choice file holds what a person says about one session: the title of its notebook and the sentence after
the dash, a summary, the one line on its card, the model that ran Dr. Kiro, the date, the colour of its card,
which measurement is "the best so far" and in which direction, the trials shown as the two large photos with
a handwritten line each, and the three sticky notes.
Everything is checked against the records before anything is rendered; a failure names the file and the key.
Every text here is builder-level text; this module does not scan, `scan.choice_segments` does.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from notebook.errors import NotebookError
from notebook.records import RecordModel

APP_NAME = "app.toml"
THEMES = ("day", "night")
PENS = ("blue", "orange")
DECORATIONS = ("none", "halloween")
COLORS = ("violet", "green", "amber", "rose", "blue", "teal")
BETTER = ("higher", "lower")
POLAROIDS = 2
BOOK_KEYS = frozenset(
    {"title", "subtitle", "summary", "line", "model", "date", "color", "progress", "polaroid", "note", "body"}
)
NOTE_KINDS = ("best", "hits", "rejected", "trials", "miss")
NOTE_KEYS = frozenset({"kind", "prediction"})
NOTES = 3
PROGRESS_KEYS = frozenset({"measurement", "better", "require", "equals", "mark", "mark_equals", "mark_words"})
POLAROID_KEYS = frozenset({"heading", "trial", "words", "star"})
APP_KEYS = frozenset(
    {
        "application",
        "order",
        "case",
        "door",
        "door_line",
        "about",
        "open",
        "unit",
        "theme",
        "pen",
        "decoration",
        "display",
        "symbols",
    }
)
SUMMARY_MAX = 700
TITLE_MAX = 60
SUBTITLE_MAX = 110
LINE_MAX = 120
HEADING_MAX = 24
WORDS_MAX = 90


@dataclass(frozen=True)
class Progress:
    """What "the best so far" is: the measurement, the better direction and, optionally, a second measurement
    that must equal a value for a trial to count (the wind tunnel's goal: no shedding)."""

    measurement: str
    better: str
    require: str | None
    equals: float | None
    mark: str | None  # a measurement whose first value `mark_equals` is flagged on the chart
    mark_equals: float | None
    mark_words: str | None  # the words a person writes at the flag
    source: str


@dataclass(frozen=True)
class Polaroid:
    heading: str
    trial: str
    words: str
    star: bool
    source: str


@dataclass(frozen=True)
class Note:
    """One of the three sticky notes: which number of the record it shows; `miss` names a prediction."""

    kind: str
    prediction: str | None
    source: str


@dataclass(frozen=True)
class Choices:
    record: str  # RecordModel.name
    file: str
    title: str
    subtitle: str
    summary: str
    line: str
    model: str
    date: str
    color: str
    progress: Progress | None  # None only when the record holds no trial
    polaroids: tuple[Polaroid, ...]
    notes: tuple[Note, ...]  # three when the record holds a trial, else none
    body: str | None = None  # a person's word on the body, for a record without a label


@dataclass(frozen=True)
class App:
    """One application of the front page: how its notebook opens and what its door says."""

    application: str
    order: int
    case: str
    door: str
    door_line: str
    about: str
    open: str  # the session id the application's first page opens
    unit: str  # the word for one budgeted step, "trials" or "runs"
    theme: str  # "day" or "night": the theme its notebook opens in
    pen: str  # "blue" or "orange": the colour of the pen of our notes
    decoration: str  # "none" or "halloween"
    display: Path | None  # the folder of retaken pictures, when the application has one
    symbols: str | None  # one line on the names a reader meets on the pages (cd, x, ...), written by a person
    folder: Path
    source: str  # the file, for messages

    @property
    def slug(self) -> str:
        return self.application


@dataclass(frozen=True)
class Apps:
    apps: tuple[App, ...]  # in the order of the front page
    choices: dict[tuple[str, str], Choices]


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise NotebookError(str(path), f"not valid TOML: {error}") from error
    except OSError as error:
        raise NotebookError(str(path), f"cannot be read: {error}") from error


def _exact(where: str, data: dict[str, Any], expected: frozenset[str], required: frozenset[str]) -> None:
    extra = sorted(data.keys() - expected)
    if extra:
        raise NotebookError(f"{where} key {extra[0]}", f"unknown key(s): {', '.join(extra)}")
    missing = sorted(required - data.keys())
    if missing:
        raise NotebookError(where, f"missing key(s): {', '.join(missing)}")


def _string(where: str, value: Any, limit: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NotebookError(where, "must be a non-empty string")
    value = value.strip()
    if len(value) > limit:
        raise NotebookError(where, f"is {len(value)} characters; at most {limit}")
    return value


def _progress(file: str, data: Any, record: RecordModel) -> Progress:
    where = f"{file} key progress"
    if not isinstance(data, dict):
        raise NotebookError(where, "must be a table")
    _exact(where, data, PROGRESS_KEYS, frozenset({"measurement", "better"}))
    scalars = {m.name for m in record.declaration.measurements if m.kind == "scalar"}
    measurement = _string(f"{where} measurement", data["measurement"], 40)
    if measurement not in scalars:
        raise NotebookError(f"{where} measurement", f"{measurement!r} is not a scalar measurement of the lab")
    better = _string(f"{where} better", data["better"], 10)
    if better not in BETTER:
        raise NotebookError(f"{where} better", f"must be one of {', '.join(BETTER)}")
    if ("require" in data) != ("equals" in data):
        raise NotebookError(where, "`require` and `equals` are given together or not at all")
    require = equals = None
    if "require" in data:
        require = _string(f"{where} require", data["require"], 40)
        if require not in scalars:
            raise NotebookError(f"{where} require", f"{require!r} is not a scalar measurement of the lab")
        equals = data["equals"]
        if isinstance(equals, bool) or not isinstance(equals, int | float):
            raise NotebookError(f"{where} equals", "must be a number")
        equals = float(equals)
    given = [k for k in ("mark", "mark_equals", "mark_words") if k in data]
    if given and len(given) != 3:
        raise NotebookError(where, "`mark`, `mark_equals` and `mark_words` are given together or not at all")
    mark = mark_equals = mark_words = None
    if given:
        mark = _string(f"{where} mark", data["mark"], 40)
        if mark not in scalars:
            raise NotebookError(f"{where} mark", f"{mark!r} is not a scalar measurement of the lab")
        value = data["mark_equals"]
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise NotebookError(f"{where} mark_equals", "must be a number")
        mark_equals = float(value)
        mark_words = _string(f"{where} mark_words", data["mark_words"], 30)
    return Progress(measurement, better, require, equals, mark, mark_equals, mark_words, where)


def _polaroid(file: str, index: int, data: Any, record: RecordModel) -> Polaroid:
    where = f"{file} key polaroid {index}"
    if not isinstance(data, dict):
        raise NotebookError(where, "must be a table ([[polaroid]])")
    _exact(where, data, POLAROID_KEYS, frozenset({"heading", "trial", "words"}))
    trial = _string(f"{where} trial", data["trial"], 20)
    if trial not in {t.id for t in record.trials}:
        raise NotebookError(f"{where} trial", f"{trial!r} is not a trial of {record.name}")
    star = data.get("star", False)
    if not isinstance(star, bool):
        raise NotebookError(f"{where} star", "must be true or false")
    return Polaroid(
        _string(f"{where} heading", data["heading"], HEADING_MAX),
        trial,
        _string(f"{where} words", data["words"], WORDS_MAX),
        star,
        where,
    )


def _note(file: str, index: int, data: object, record: RecordModel) -> Note:
    where = f"{file} key note {index}"
    if not isinstance(data, dict):
        raise NotebookError(where, "must be a table ([[note]])")
    _exact(where, data, NOTE_KEYS, frozenset({"kind"}))
    kind = _string(f"{where} kind", data["kind"], 12)
    if kind not in NOTE_KINDS:
        raise NotebookError(f"{where} kind", f"must be one of {', '.join(NOTE_KINDS)}")
    if (kind == "miss") != ("prediction" in data):
        raise NotebookError(where, "a `miss` note names its `prediction`, and no other note does")
    prediction = None
    if kind == "miss":
        prediction = _string(f"{where} prediction", data["prediction"], 20)
        found = [o for o in record.outcomes if o.prediction == prediction]
        if not found or found[0].outcome != "miss" or found[0].value is None:
            raise NotebookError(
                f"{where} prediction",
                f"{prediction!r} is not a missed prediction of {record.name} with a value",
            )
    return Note(kind, prediction, where)


def load_file(path: Path, record: RecordModel) -> Choices:
    """Read and check one choice file against its record."""
    file = str(path)
    data = _read_toml(path)
    _exact(file, data, BOOK_KEYS, BOOK_KEYS - {"progress", "polaroid", "note", "body"})
    # `body` is a person's word on which body a session ran on, for a record made before bodies had labels. A
    # record that names its body is not contradicted.
    body = _string(f"{file} key body", data["body"], 10) if "body" in data else None
    if body is not None and record.variant is not None and body != record.variant:
        raise NotebookError(f"{file} key body", f"says {body!r}; the record says {record.variant!r}")
    color = _string(f"{file} key color", data["color"], 10)
    if color not in COLORS:
        raise NotebookError(f"{file} key color", f"must be one of {', '.join(COLORS)}")
    date = _string(f"{file} key date", data["date"], 10)
    if len(date) != 10 or date[4] != "-" or date[7] != "-" or not (date[:4] + date[5:7] + date[8:]).isdigit():
        raise NotebookError(f"{file} key date", "must be written YYYY-MM-DD")
    polaroids_value = data.get("polaroid", [])
    if not isinstance(polaroids_value, list):
        raise NotebookError(f"{file} key polaroid", "must be an array of tables ([[polaroid]])")
    wanted = min(POLAROIDS, len(record.trials))
    if len(polaroids_value) != wanted:
        raise NotebookError(
            f"{file} key polaroid",
            f"{record.name} has {len(record.trials)} trial(s), so the file needs {wanted} [[polaroid]]; "
            f"it has {len(polaroids_value)}",
        )
    polaroids = tuple(_polaroid(file, i, p, record) for i, p in enumerate(polaroids_value, start=1))
    if len({p.trial for p in polaroids}) != len(polaroids):
        raise NotebookError(f"{file} key polaroid", "the two photos must be of different trials")
    if record.trials and "progress" not in data:
        raise NotebookError(file, f"{record.name} has trials, so the file needs a [progress] table")
    if not record.trials and "progress" in data:
        raise NotebookError(f"{file} key progress", f"{record.name} has no trial, so it has no progress")
    progress = _progress(file, data["progress"], record) if "progress" in data else None
    notes_value = data.get("note", [])
    wanted_notes = NOTES if record.trials else 0
    if not isinstance(notes_value, list) or len(notes_value) != wanted_notes:
        raise NotebookError(
            f"{file} key note",
            f"{record.name} needs {wanted_notes} [[note]]; the file has {len(notes_value)}",
        )
    notes = tuple(_note(file, i, n, record) for i, n in enumerate(notes_value, start=1))
    if len({n.kind if n.kind != "miss" else n.prediction for n in notes}) != len(notes):
        raise NotebookError(f"{file} key note", "the notes must show different things")
    return Choices(
        record=record.name,
        file=file,
        title=_string(f"{file} key title", data["title"], TITLE_MAX),
        subtitle=_string(f"{file} key subtitle", data["subtitle"], SUBTITLE_MAX),
        summary=_string(f"{file} key summary", data["summary"], SUMMARY_MAX),
        line=_string(f"{file} key line", data["line"], LINE_MAX),
        model=_string(f"{file} key model", data["model"], 60),
        date=date,
        color=color,
        progress=progress,
        polaroids=polaroids,
        notes=notes,
        body=body,
    )


def _app(folder: Path, records: list[RecordModel]) -> App:
    path = folder / APP_NAME
    where = str(path)
    if not path.is_file():
        raise NotebookError(where, "the application's settings file is missing")
    data = _read_toml(path)
    _exact(where, data, APP_KEYS, APP_KEYS - {"display", "symbols"})
    application = _string(f"{where} application", data["application"], 40)
    sessions = {r.session for r in records if r.application == application}
    if not sessions:
        raise NotebookError(f"{where} application", f"the records hold no session of {application!r}")
    opened = _string(f"{where} open", data["open"], 40)
    if opened not in sessions:
        raise NotebookError(f"{where} open", f"names no record ({application}/{opened})")
    order = data["order"]
    if type(order) is not int or order < 1:
        raise NotebookError(f"{where} order", "must be a whole number from 1")
    theme = _string(f"{where} theme", data["theme"], 10)
    if theme not in THEMES:
        raise NotebookError(f"{where} theme", f"must be one of {', '.join(THEMES)}")
    pen = _string(f"{where} pen", data["pen"], 10)
    if pen not in PENS:
        raise NotebookError(f"{where} pen", f"must be one of {', '.join(PENS)}")
    decoration = _string(f"{where} decoration", data["decoration"], 12)
    if decoration not in DECORATIONS:
        raise NotebookError(f"{where} decoration", f"must be one of {', '.join(DECORATIONS)}")
    display = None
    if "display" in data:
        display = folder / _string(f"{where} display", data["display"], 40)
        if not display.is_dir():
            raise NotebookError(f"{where} display", f"{display} is not a folder")
    return App(
        application=application,
        order=order,
        case=_string(f"{where} case", data["case"], 80),
        door=_string(f"{where} door", data["door"], 40),
        door_line=_string(f"{where} door_line", data["door_line"], 100),
        about=_string(f"{where} about", data["about"], 400),
        open=opened,
        unit=_string(f"{where} unit", data["unit"], 20),
        theme=theme,
        pen=pen,
        decoration=decoration,
        display=display,
        symbols=_string(f"{where} symbols", data["symbols"], 400) if "symbols" in data else None,
        folder=folder,
        source=where,
    )


def _choice_files(app: App, records: list[RecordModel]) -> dict[tuple[str, str], Choices]:
    folder = app.folder / "choices"
    if not folder.is_dir():
        raise NotebookError(str(folder), "the choices folder is not a folder")
    mine = {r.session: r for r in records if r.application == app.application}
    found: dict[tuple[str, str], Choices] = {}
    for path in sorted(folder.iterdir(), key=lambda p: p.name):
        if not (path.is_file() and path.suffix == ".toml"):
            raise NotebookError(str(path), "not a choice file (<session-id>.toml)")
        if path.stem not in mine:
            raise NotebookError(str(path), f"names no record ({app.application}/{path.stem})")
        found[(app.application, path.stem)] = load_file(path, mine[path.stem])
    for session in sorted(mine):
        if (app.application, session) not in found:
            raise NotebookError(
                str(folder / f"{session}.toml"), f"the record {mine[session].name} has no choice file"
            )
    return found


def load_apps(folders: list[Path], records: list[RecordModel]) -> Apps:
    """Read and check every application's notebook folder. Every application of the records has exactly one;
    the applications are in the order of their `order` key, and no two share one."""
    apps = [_app(Path(f), records) for f in folders]
    seen: dict[str, App] = {}
    for app in apps:
        if app.application in seen:
            raise NotebookError(app.source, f"a second settings file for {app.application}")
        seen[app.application] = app
    for application in sorted({r.application for r in records}):
        if application not in seen:
            raise NotebookError("apps", f"no notebook folder is given for the application {application}")
    orders = [a.order for a in apps]
    if len(set(orders)) != len(orders):
        raise NotebookError("apps", "two applications have the same order")
    chosen: dict[tuple[str, str], Choices] = {}
    for app in apps:
        chosen.update(_choice_files(app, records))
    return Apps(tuple(sorted(apps, key=lambda a: a.order)), chosen)
