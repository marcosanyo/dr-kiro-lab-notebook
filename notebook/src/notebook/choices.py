"""Choice files and the cover file (notebook-shelf design 2). A person writes them; the notebook reads them.
A choice file `<folder>/<application>/<session-id>.toml` holds what a person says about one session: the
title of its notebook and the sentence after the dash, a summary, the one line on its card, the model that
ran Dr. Kiro, the date, the colour of its card, which measurement is "the best so far" and in which
direction, and the trials shown as the two large photos with a handwritten line each.
The cover file `<folder>/cover.toml` holds one `[[lab]]` per application: the text on its round tab, the
description under the title and the session whose notebook the first page opens.
Everything is checked against the records before anything is rendered; a failure names the file and the key.
Every text here is builder-level text (orange pen); this module does not scan, `scan.choice_segments` does.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from notebook.errors import NotebookError
from notebook.records import RecordModel

COVER_NAME = "cover.toml"
COLORS = ("violet", "green", "amber", "rose", "blue", "teal")
BETTER = ("higher", "lower")
POLAROIDS = 2
BOOK_KEYS = frozenset(
    {"title", "subtitle", "summary", "line", "model", "date", "color", "progress", "polaroid", "note"}
)
NOTE_KINDS = ("best", "hits", "rejected", "trials", "miss")
NOTE_KEYS = frozenset({"kind", "prediction"})
NOTES = 3
PROGRESS_KEYS = frozenset({"measurement", "better", "require", "equals"})
POLAROID_KEYS = frozenset({"heading", "trial", "words", "star"})
LAB_KEYS = frozenset({"application", "case", "about", "open", "unit"})
COVER_KEYS = frozenset({"lab"})
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


@dataclass(frozen=True)
class Lab:
    application: str
    case: str
    about: str
    open: str  # the session id the first page opens
    unit: str  # the word for one budgeted step, "trials" or "runs"
    source: str


@dataclass(frozen=True)
class Cover:
    file: str
    labs: tuple[Lab, ...]  # in the order of the cover file


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
    return Progress(measurement, better, require, equals, where)


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
    _exact(file, data, BOOK_KEYS, BOOK_KEYS - {"progress", "polaroid", "note"})
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
    )


def load(folder: Path, records: list[RecordModel]) -> dict[tuple[str, str], Choices]:
    """Every choice file in `folder`, one per record, keyed by (application, session id). The folder holds the
    cover file and one subfolder per application; anything else fails, naming it."""
    folder = Path(folder)
    if not folder.is_dir():
        raise NotebookError(str(folder), "the choices folder is not a folder")
    by_key = {(r.application, r.session): r for r in records}
    found: dict[tuple[str, str], Choices] = {}
    for entry in sorted(folder.iterdir(), key=lambda p: p.name):
        if entry.name == COVER_NAME and entry.is_file():
            continue
        if not entry.is_dir():
            raise NotebookError(str(entry), "not an application folder of choice files")
        for path in sorted(entry.iterdir(), key=lambda p: p.name):
            if not (path.is_file() and path.suffix == ".toml"):
                raise NotebookError(str(path), "not a choice file (<session-id>.toml)")
            key = (entry.name, path.stem)
            if key not in by_key:
                raise NotebookError(str(path), f"names no record ({entry.name}/{path.stem})")
            found[key] = load_file(path, by_key[key])
    for key in sorted(by_key):
        if key not in found:
            raise NotebookError(
                str(folder / key[0] / f"{key[1]}.toml"), f"the record {by_key[key].name} has no choice file"
            )
    return found


def load_cover(folder: Path, records: list[RecordModel]) -> Cover:
    """Read and check `<folder>/cover.toml`: one `[[lab]]` per application of the records."""
    path = Path(folder) / COVER_NAME
    file = str(path)
    if not path.is_file():
        raise NotebookError(file, "the cover file is missing")
    data = _read_toml(path)
    _exact(file, data, COVER_KEYS, COVER_KEYS)
    value = data["lab"]
    if not (isinstance(value, list) and all(isinstance(t, dict) for t in value)):
        raise NotebookError(f"{file} key lab", "must be an array of tables ([[lab]])")
    sessions = {(r.application, r.session) for r in records}
    labs: dict[str, Lab] = {}
    for i, table in enumerate(value, start=1):
        where = f"{file} key lab {i}"
        _exact(where, table, LAB_KEYS, LAB_KEYS)
        application = _string(f"{where} application", table["application"], 40)
        if application in labs:
            raise NotebookError(where, f"a second [[lab]] for {application}")
        opened = _string(f"{where} open", table["open"], 40)
        if (application, opened) not in sessions:
            raise NotebookError(f"{where} open", f"names no record ({application}/{opened})")
        labs[application] = Lab(
            application,
            _string(f"{where} case", table["case"], 80),
            _string(f"{where} about", table["about"], 400),
            opened,
            _string(f"{where} unit", table["unit"], 20),
            where,
        )
    for application in sorted({r.application for r in records}):
        if application not in labs:
            raise NotebookError(f"{file} key lab", f"no [[lab]] for the application {application}")
    return Cover(file, tuple(labs.values()))
