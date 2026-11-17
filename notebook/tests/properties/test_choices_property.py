"""Property test of the choice and cover file checks (task 6.3).

The records are synthesized fake fixtures (`tests/fixtures/synth.py`) and the choice and cover files are
generated test inputs written to a temporary folder; nothing here is a result. A reference predicate, written
directly from Requirements 12.1, 12.3-12.6 and 13.5 over the raw generated entries (not over the notebook's
record model), lists every problem of the generated files. The build must accept the files exactly when the
reference finds no problem, and a refusal must name a file and a choice the reference names.
"""

# Feature: lab-notebook, Property 11: Choice and cover validation matches the rules
# **Validates: Requirements 12.1, 12.3, 12.4, 12.5, 12.6, 13.5**

import json
import tempfile
from pathlib import Path
from typing import Any

from hypothesis import HealthCheck, event, given, settings
from hypothesis import strategies as st

from fixtures.synth import SynthRecord, record_sets, records, write_all
from notebook import choices
from notebook import records as notebook_records
from notebook.errors import NotebookError

SLOW = settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])

APPLICATIONS = ("fake", "fake-two")
KEYS = ("contrast", "best", "missed")
NONE = "none"
MISSING = object()  # a key left out of a generated file
BOGUS_TRIAL = "T99"
BOGUS_PREDICTION = "H9.P9"
REASON_LENGTHS = (0, 1, 2, 300, 301)


# Facts of a generated record, read from its raw entries


def _trials(r: SynthRecord) -> list[str]:
    return [t["trial"] for t in r.kinds("trial")]


def _registered(r: SynthRecord) -> list[str]:
    return [p["id"] for h in r.kinds("register") for p in h["predictions"]]


def _outcomes(r: SynthRecord) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for o in r.kinds("outcome"):
        out.setdefault(o["prediction"], []).append(o["outcome"])
    return out


def _misses(r: SynthRecord) -> list[str]:
    return [p for p, kinds in _outcomes(r).items() if "miss" in kinds]


def _ended(r: SynthRecord) -> bool:
    return r.kinds("seal")[0]["end"] == "ended"


# The reference predicate


Problem = tuple[str, str | None]  # (file, choice key or None for the whole file)


def _reason_ok(value: Any) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= 300


def choice_problems(file: str, data: dict[str, Any], r: SynthRecord) -> list[Problem]:
    """Requirements 12.1, 12.4, 12.5, 12.6 for one choice file of record `r`."""
    problems: list[Problem] = []
    allowed = set(KEYS) | {f"{k}_reason" for k in KEYS}
    problems += [(file, k) for k in data if k not in allowed]
    trials = set(_trials(r))
    outcomes = _outcomes(r)
    for key in KEYS:
        reason_key = f"{key}_reason"
        if key not in data:
            problems.append((file, key))
            continue
        value = data[key]
        if value == NONE:
            # "none" needs the user's reason of 1 to 300 characters (12.1); for the miss it is accepted
            # with its reason even when the record has a miss (12.5).
            if not _reason_ok(data.get(reason_key)):
                problems.append((file, reason_key))
            continue
        if reason_key in data:
            problems.append((file, reason_key))  # a reason only goes with "none"
        if not trials:
            problems.append((file, key))  # 12.6: no trial, so all three must be "none"
            continue
        if key == "contrast":
            ok = (
                isinstance(value, list)
                and len(value) == 2
                and all(isinstance(v, str) and v in trials for v in value)
                and value[0] != value[1]
            )
        elif key == "best":
            ok = isinstance(value, str) and value in trials
        else:
            ok = isinstance(value, str) and outcomes.get(value) == ["miss"]
        if not ok:
            problems.append((file, key))  # 12.4
    return problems


def folder_problems(
    folder: Path, files: dict[tuple[str, str], dict[str, Any]], recs: list[SynthRecord]
) -> list[Problem]:
    """Requirement 12.3 and every file's own problems."""
    by_key = {(r.application, r.session): r for r in recs}
    problems: list[Problem] = []
    for key, data in files.items():
        file = str(folder / key[0] / f"{key[1]}.toml")
        if key not in by_key:
            problems.append((file, None))  # a choice file names no record
        else:
            problems += choice_problems(file, data, by_key[key])
    for key in by_key:
        if key not in files:
            problems.append((str(folder / key[0] / f"{key[1]}.toml"), None))  # a record has no file
    return problems


def cover_problems(file: str, cover: dict[str, Any] | None, recs: list[SynthRecord]) -> list[Problem]:
    """Requirement 13.5."""
    if cover is None:
        return [(file, None)]
    by_key = {(r.application, r.session): r for r in recs}
    problems: list[Problem] = []
    if set(cover) != {"miss", "card"}:
        problems.append((file, None))

    def ended_record(table: dict[str, Any], key: str) -> SynthRecord | None:
        app, session = table.get("application"), table.get("session")
        r = by_key.get((app, session)) if isinstance(app, str) and isinstance(session, str) else None
        if r is None or not _ended(r):
            problems.append((file, key))
            return None
        return r

    miss = cover.get("miss")
    if isinstance(miss, dict):
        if set(miss) != {"application", "session", "prediction"}:
            problems.append((file, "miss"))
        r = ended_record(miss, "miss")
        prediction = miss.get("prediction")
        if r is not None:
            if prediction == NONE:
                ok = not _misses(r)  # "none" only when the session has no missed prediction
            else:
                ok = isinstance(prediction, str) and _outcomes(r).get(prediction) == ["miss"]
            if not ok:
                problems.append((file, "miss"))

    cards = cover.get("card")
    if isinstance(cards, list):
        carded: list[str] = []
        for card in cards:
            if set(card) != {"application", "session", "trial"}:
                problems.append((file, "card"))
            r = ended_record(card, "card")
            if r is None:
                continue
            if r.application in carded:
                problems.append((file, "card"))  # one card per application
            carded.append(r.application)
            if card.get("trial") not in _trials(r):
                problems.append((file, "card"))
        for app in {r.application for r in recs}:
            if app not in carded:
                problems.append((file, "card"))  # every application present has a card
    return problems


# Generated files


def reasons() -> st.SearchStrategy[Any]:
    return st.one_of(
        st.sampled_from(REASON_LENGTHS).flatmap(
            lambda n: st.text(alphabet="abc xyz", min_size=n, max_size=n)
        ),
        st.just(7),  # not a string
    )


@st.composite
def valid_choice(draw: st.DrawFn, r: SynthRecord) -> dict[str, Any]:
    trials, misses = _trials(r), _misses(r)
    good_reason = st.text(alphabet="abc xyz", min_size=1, max_size=300)
    data: dict[str, Any] = {}

    def none(key: str) -> None:
        data[key] = NONE
        data[f"{key}_reason"] = draw(good_reason)

    if len(trials) >= 2 and draw(st.integers(0, 4)):
        data["contrast"] = draw(st.permutations(trials))[:2]
    else:
        none("contrast")
    if trials and draw(st.integers(0, 4)):
        data["best"] = draw(st.sampled_from(trials))
    else:
        none("best")
    if misses and draw(st.integers(0, 4)):
        data["missed"] = draw(st.sampled_from(misses))
    else:
        none("missed")
    return data


@st.composite
def any_choice(draw: st.DrawFn, r: SynthRecord) -> dict[str, Any]:
    """A choice file that may break any rule: wrong ids, a hit or not-run prediction, the same trial twice,
    wrong shapes, "none" with and without a reason, reasons of 0, 1, 300 and 301 characters, extra keys."""
    trial_ids = st.sampled_from([*_trials(r), BOGUS_TRIAL, "T1"])
    prediction_ids = st.sampled_from([*_registered(r), BOGUS_PREDICTION])
    values = {
        "contrast": st.one_of(
            st.just(NONE), st.lists(trial_ids, min_size=1, max_size=3), trial_ids, st.just(MISSING)
        ),
        "best": st.one_of(st.just(NONE), trial_ids, st.just(3), st.just(MISSING)),
        "missed": st.one_of(st.just(NONE), prediction_ids, st.just(MISSING)),
    }
    data: dict[str, Any] = {}
    for key in KEYS:
        value = draw(values[key])
        if value is not MISSING:
            data[key] = value
        if draw(st.booleans()):
            data[f"{key}_reason"] = draw(reasons())
    if not draw(st.integers(0, 5)):
        data["note"] = "x"
    return data


@st.composite
def choice_files(draw: st.DrawFn, recs: list[SynthRecord]) -> dict[tuple[str, str], dict[str, Any]]:
    files = {}
    for r in recs:
        if not draw(st.integers(0, 12)):
            continue  # the record has no choice file
        broken = not draw(st.integers(0, 5))
        files[(r.application, r.session)] = draw(any_choice(r) if broken else valid_choice(r))
    if not draw(st.integers(0, 12)):
        files[(draw(st.sampled_from(APPLICATIONS)), "s9")] = {"contrast": NONE}  # names no record
    return files


@st.composite
def covers(draw: st.DrawFn, recs: list[SynthRecord]) -> dict[str, Any] | None:
    """A cover file, often valid; it may name stopped sessions, wrong ids, a prediction that is not a miss,
    "none" with or without a miss, duplicate or missing cards, extra or missing keys, or be missing."""
    if not draw(st.integers(0, 15)):
        return None
    ended = [r for r in recs if _ended(r)]
    apps = sorted({x.application for x in recs})
    holders = {a: [x for x in ended if x.application == a and _trials(x)] for a in apps}
    if ended and all(holders.values()) and draw(st.booleans()):
        # A valid cover, so acceptance (including "none" for a session with no miss) is reached often.
        r = draw(st.sampled_from(ended))
        misses = _misses(r)
        cards = []
        for a in apps:
            c = draw(st.sampled_from(holders[a]))
            cards.append({"application": a, "session": c.session, "trial": draw(st.sampled_from(_trials(c)))})
        prediction = draw(st.sampled_from(misses)) if misses else NONE
        return {
            "miss": {"application": r.application, "session": r.session, "prediction": prediction},
            "card": cards,
        }
    pool = ended if ended and draw(st.integers(0, 3)) else recs
    r = draw(st.sampled_from(pool))
    misses = _misses(r)
    if draw(st.integers(0, 3)):
        prediction = draw(st.sampled_from(misses)) if misses else NONE
    else:
        prediction = draw(st.sampled_from([NONE, *_registered(r), BOGUS_PREDICTION]))
    miss: dict[str, Any] = {"application": r.application, "session": r.session, "prediction": prediction}
    if not draw(st.integers(0, 12)):
        miss["session"] = "s9"
    if not draw(st.integers(0, 15)):
        del miss["prediction"]
    if not draw(st.integers(0, 15)):
        miss["extra"] = "x"

    cards = []
    for app in sorted({x.application for x in recs}):
        count = 1 if draw(st.integers(0, 8)) else draw(st.sampled_from((0, 2)))
        for _ in range(count):
            same_app = [x for x in recs if x.application == app]
            good = [x for x in same_app if _ended(x) and _trials(x)]
            c = draw(st.sampled_from(good if good and draw(st.integers(0, 4)) else same_app))
            trial = (
                draw(st.sampled_from(_trials(c))) if _trials(c) and draw(st.integers(0, 6)) else BOGUS_TRIAL
            )
            card: dict[str, Any] = {"application": app, "session": c.session, "trial": trial}
            if not draw(st.integers(0, 20)):
                card["extra"] = "x"
            cards.append(card)

    cover: dict[str, Any] = {}
    if draw(st.integers(0, 15)):
        cover["miss"] = miss
    if cards:
        cover["card"] = cards
    if not draw(st.integers(0, 20)):
        cover["extra"] = "x"
    return cover


# TOML writing (the generated values are ASCII strings, integers and lists of them)


def _toml_value(value: Any) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    if isinstance(value, int):
        return str(value)
    return json.dumps(value)


def _toml_table(data: dict[str, Any]) -> str:
    return "".join(f"{k} = {_toml_value(v)}\n" for k, v in data.items())


def write_cover(path: Path, cover: dict[str, Any]) -> None:
    text = _toml_table({k: v for k, v in cover.items() if k not in ("miss", "card")})
    if "miss" in cover:
        text += "\n[miss]\n" + _toml_table(cover["miss"])
    for card in cover.get("card", []):
        text += "\n[[card]]\n" + _toml_table(card)
    path.write_text(text, encoding="utf-8")


def write_choices(
    folder: Path, files: dict[tuple[str, str], dict[str, Any]], cover: dict[str, Any] | None
) -> None:
    folder.mkdir()
    for (app, session), data in files.items():
        path = folder / app / f"{session}.toml"
        path.parent.mkdir(exist_ok=True)
        path.write_text(_toml_table(data), encoding="utf-8")
    if cover is not None:
        write_cover(folder / choices.COVER_NAME, cover)


def _names(error: NotebookError, problems: list[Problem]) -> bool:
    """The refusal names a file and a choice that the reference names."""
    for file, key in problems:
        if key is None and error.where == file:
            return True
        if key is not None and (
            error.where == f"{file} key {key}" or error.where.startswith(f"{file} key {key} ")
        ):
            return True
    return False


def _check(call, problems: list[Problem]) -> None:
    if problems:
        try:
            call()
        except NotebookError as error:
            assert _names(error, problems), (error.where, problems)
        else:
            raise AssertionError(f"accepted, but the reference finds {problems}")
    else:
        call()


@SLOW
@given(st.data(), record_sets(applications=APPLICATIONS, max_records=3))
def test_choice_and_cover_validation_matches_the_rules(data: st.DataObject, recs: list[SynthRecord]) -> None:
    files = data.draw(choice_files(recs))
    cover = data.draw(covers(recs))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        loaded = notebook_records.load(write_all(root / "sessions", recs), allow_fake=True)
        folder = root / "choices"
        write_choices(folder, files, cover)

        expected = folder_problems(folder, files, recs)
        event("choice files accepted" if not expected else "choice files refused")
        _check(lambda: choices.load(folder, loaded), expected)

        expected_cover = cover_problems(str(folder / choices.COVER_NAME), cover, recs)
        event("cover accepted" if not expected_cover else "cover refused")
        if cover is not None and "miss" in cover and cover["miss"].get("prediction") == NONE:
            event("cover none " + ("accepted" if not expected_cover else "refused"))
        _check(lambda: choices.load_cover(folder, loaded), expected_cover)


@SLOW
@given(
    st.data(),
    records(application="fake", rounds=st.just(0), endings=("no-table",)),
    records(application="fake-two", session="s1", endings=("table",)),
)
def test_cover_none_is_accepted_for_an_ended_session_with_no_miss(
    data: st.DataObject, quiet: SynthRecord, other: SynthRecord
) -> None:
    """The case task 6.1 left untested: the cover's prediction "none" for an ended session without a miss."""
    assert _ended(quiet) and not _misses(quiet)
    cards = [
        {"application": "fake-two", "session": "s1", "trial": data.draw(st.sampled_from(_trials(other)))}
    ]
    cover = {"miss": {"application": "fake", "session": "s1", "prediction": NONE}, "card": cards}
    # The quiet record has no trial, so its own card cannot name one; a second session of "fake" holds it.
    third = data.draw(records(application="fake", session="s2", endings=("table",)))
    cards.append(
        {"application": "fake", "session": "s2", "trial": data.draw(st.sampled_from(_trials(third)))}
    )
    recs = [quiet, other, third]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        loaded = notebook_records.load(write_all(root / "sessions", recs), allow_fake=True)
        folder = root / "choices"
        write_choices(folder, {}, cover)
        assert cover_problems(str(folder / choices.COVER_NAME), cover, recs) == []
        result = choices.load_cover(folder, loaded)
    assert result.miss.prediction is None and result.miss.outcome is None
    assert (result.miss.application, result.miss.session) == ("fake", "s1")
    assert [c.application for c in result.cards] == ["fake", "fake-two"]
