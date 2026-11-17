"""Choice files and the cover file (design 7, "Data Models"; Requirements 12, 13.5).

A choice file `<folder>/<application>/<session-id>.toml` names a contrast (two different trial ids), a best
result (one trial id) and a missed prediction (one prediction id whose outcome is miss). Each may instead be
`"none"`, and then `<key>_reason` must be given: a reason written by the user of 1 to 300 characters. A
`<key>_reason` is allowed only when `<key>` is `"none"`. Every record has exactly one choice file and every
choice file names a record. A record with no trial must say `"none"` for all three choices.

The cover file `<folder>/cover.toml` names the session and prediction of the cover (`[miss]`, the prediction
may be `"none"` only when that session has no missed prediction) and one `[[card]]` with a trial per
application present in the records. Every session it names must be an ended session.

Everything is checked before anything is rendered; a failure names the file and the key. The reasons are
builder-level text and go to the blind scan (12.8); this module does not scan.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from notebook.errors import NotebookError
from notebook.records import Outcome, RecordModel

NONE = "none"
CHOICE_KEYS = ("contrast", "best", "missed")
REASON_MAX = 300
COVER_NAME = "cover.toml"
COVER_KEYS = frozenset({"miss", "card"})
MISS_KEYS = frozenset({"application", "session", "prediction"})
CARD_KEYS = frozenset({"application", "session", "trial"})


@dataclass(frozen=True)
class Choice:
    """One choice: `value` is the chosen id(s), or None with the user's `reason` when the file says "none"."""

    value: tuple[str, ...] | None
    reason: str | None
    source: str  # "<file> key <key>", where the choice comes from


@dataclass(frozen=True)
class Choices:
    record: str  # RecordModel.name
    file: str
    contrast: Choice  # two trial ids
    best: Choice  # one trial id
    missed: Choice  # one prediction id


@dataclass(frozen=True)
class CoverMiss:
    application: str
    session: str
    prediction: str | None  # None when the file says "none"
    outcome: Outcome | None  # the miss outcome of the prediction
    source: str


@dataclass(frozen=True)
class Card:
    application: str
    session: str
    trial: str
    source: str


@dataclass(frozen=True)
class Cover:
    file: str
    miss: CoverMiss
    cards: tuple[Card, ...]  # in application code-point order


# Reading


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise NotebookError(str(path), f"not valid TOML: {error}") from error
    except UnicodeDecodeError as error:
        raise NotebookError(str(path), f"not UTF-8 text: {error}") from error


def _exact_keys(where: str, data: dict[str, Any], expected: frozenset[str]) -> None:
    missing = sorted(expected - data.keys())
    extra = sorted(data.keys() - expected)
    if missing:
        raise NotebookError(where, f"missing key(s): {', '.join(missing)}")
    if extra:
        raise NotebookError(where, f"unknown key(s): {', '.join(extra)}")


def _string(where: str, value: Any) -> str:
    if not isinstance(value, str):
        raise NotebookError(where, f"must be a string, got {value!r}")
    return value


def _outcomes_of(record: RecordModel, prediction: str) -> list[Outcome]:
    return [o for o in record.outcomes if o.prediction == prediction]


def _has_miss(record: RecordModel) -> bool:
    return any(o.outcome == "miss" for o in record.outcomes)


def _registered(record: RecordModel) -> set[str]:
    return {p.id for h in record.hypotheses for p in h.predictions}


def _miss_outcome(where: str, record: RecordModel, prediction: str) -> Outcome:
    """The one outcome of `prediction`, which must be a miss (Requirements 12.4, 13.5)."""
    if prediction not in _registered(record):
        raise NotebookError(where, f"prediction {prediction!r} is not in the record {record.name}")
    outcomes = _outcomes_of(record, prediction)
    if not outcomes:
        raise NotebookError(where, f"prediction {prediction} has no recorded outcome in {record.name}")
    if len(outcomes) > 1:
        raise NotebookError(
            where, f"prediction {prediction} has {len(outcomes)} recorded outcomes in {record.name}"
        )
    if outcomes[0].outcome != "miss":
        raise NotebookError(
            where, f"prediction {prediction} has the outcome {outcomes[0].outcome!r}, not 'miss'"
        )
    return outcomes[0]


def _trial(where: str, record: RecordModel, value: Any) -> str:
    trial = _string(where, value)
    if trial not in {t.id for t in record.trials}:
        raise NotebookError(where, f"trial {trial!r} is not in the record {record.name}")
    return trial


# Choice files


def _choice(file: str, data: dict[str, Any], key: str, record: RecordModel) -> Choice:
    where = f"{file} key {key}"
    reason_key = f"{key}_reason"
    if key not in data:
        raise NotebookError(where, "missing")
    value = data[key]
    if value == NONE:
        if reason_key not in data:
            raise NotebookError(f"{file} key {reason_key}", f'required because {key} is "none"')
        reason = _string(f"{file} key {reason_key}", data[reason_key])
        if not 1 <= len(reason) <= REASON_MAX:
            raise NotebookError(
                f"{file} key {reason_key}",
                f"a reason must have 1 to {REASON_MAX} characters, it has {len(reason)}",
            )
        return Choice(None, reason, where)
    if reason_key in data:
        raise NotebookError(f"{file} key {reason_key}", f'allowed only when {key} is "none"')
    if not record.trials:
        # 12.6: a record with no trial (wt-003) says "none" for all three choices.
        raise NotebookError(where, f'the record {record.name} has no trial, so {key} must be "none"')
    if key == "contrast":
        if not (isinstance(value, list) and len(value) == 2):
            raise NotebookError(where, f'must be a list of two trial ids or "none", got {value!r}')
        first, second = (_trial(where, record, v) for v in value)
        if first == second:
            raise NotebookError(where, f"names the same trial twice ({first})")
        return Choice((first, second), None, where)
    if key == "best":
        return Choice((_trial(where, record, value),), None, where)
    prediction = _string(where, value)
    _miss_outcome(where, record, prediction)
    return Choice((prediction,), None, where)


def load_file(path: Path, record: RecordModel) -> Choices:
    """Read and check one choice file against its record (Requirements 12.1, 12.4-12.6)."""
    file = str(path)
    data = _read_toml(path)
    allowed = set(CHOICE_KEYS) | {f"{k}_reason" for k in CHOICE_KEYS}
    extra = sorted(data.keys() - allowed)
    if extra:
        raise NotebookError(f"{file} key {extra[0]}", f"unknown key(s): {', '.join(extra)}")
    contrast, best, missed = (_choice(file, data, key, record) for key in CHOICE_KEYS)
    # 12.5: "none" for the miss while the record has a miss is accepted only with its reason, which
    # _choice has already required. The session page still lists every missed prediction.
    return Choices(record.name, file, contrast, best, missed)


def load(folder: Path, records: list[RecordModel]) -> dict[tuple[str, str], Choices]:
    """Every choice file in `folder`, one per record, keyed by (application, session id) (Requirement 12.3).
    The folder holds the cover file and one subfolder per application; anything else fails, naming it."""
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


# Cover file


def _ended_record(
    where: str, table: dict[str, Any], by_key: dict[tuple[str, str], RecordModel]
) -> RecordModel:
    application = _string(f"{where} application", table["application"])
    session = _string(f"{where} session", table["session"])
    if (application, session) not in by_key:
        raise NotebookError(f"{where} session", f"names no record ({application}/{session})")
    record = by_key[(application, session)]
    if record.seal.end != "ended":
        raise NotebookError(
            f"{where} session",
            f"{record.name} is a {record.seal.end} session; the cover shows only ended ones",
        )
    return record


def load_cover(folder: Path, records: list[RecordModel]) -> Cover:
    """Read and check `<folder>/cover.toml` (Requirement 13.5)."""
    path = Path(folder) / COVER_NAME
    file = str(path)
    if not path.is_file():
        raise NotebookError(file, "the cover file is missing")
    data = _read_toml(path)
    _exact_keys(file, data, COVER_KEYS)
    by_key = {(r.application, r.session): r for r in records}

    where = f"{file} key miss"
    if not isinstance(data["miss"], dict):
        raise NotebookError(where, "must be a table")
    _exact_keys(where, data["miss"], MISS_KEYS)
    record = _ended_record(where, data["miss"], by_key)
    prediction = _string(f"{where} prediction", data["miss"]["prediction"])
    if prediction == NONE:
        if _has_miss(record):
            raise NotebookError(
                f"{where} prediction", f'is "none", but {record.name} has a missed prediction'
            )
        miss = CoverMiss(record.application, record.session, None, None, where)
    else:
        outcome = _miss_outcome(f"{where} prediction", record, prediction)
        miss = CoverMiss(record.application, record.session, prediction, outcome, where)

    cards_value = data["card"]
    if not (isinstance(cards_value, list) and all(isinstance(c, dict) for c in cards_value)):
        raise NotebookError(f"{file} key card", "must be an array of tables ([[card]])")
    cards: dict[str, Card] = {}
    for i, table in enumerate(cards_value, start=1):
        card_where = f"{file} key card {i}"
        _exact_keys(card_where, table, CARD_KEYS)
        card_record = _ended_record(card_where, table, by_key)
        if card_record.application in cards:
            raise NotebookError(card_where, f"a second card for {card_record.application}")
        trial = _trial(f"{card_where} trial", card_record, table["trial"])
        cards[card_record.application] = Card(card_record.application, card_record.session, trial, card_where)
    for application in sorted({r.application for r in records}):
        if application not in cards:
            raise NotebookError(f"{file} key card", f"no card for the application {application}")
    return Cover(file, miss, tuple(cards[a] for a in sorted(cards)))
