"""Choice and cover file checks (task 6.1), against the committed records with choice files written to
`tmp_path`. The ids used are facts of the records (requirements introduction and Decisions 36, 37); these
files are test inputs, not the committed choice files of task 6.2. Every refusal names the file and the
key."""

from pathlib import Path

import pytest

from notebook import choices, records
from notebook.errors import NotebookError

SESSIONS = Path(__file__).resolve().parents[3] / "sessions"

VALID = {
    "body-lab/body-1": 'contrast = ["T22", "T30"]\nbest = "T39"\nmissed = "H8.P1"\n',
    "body-lab/body-2": 'contrast = ["T25", "T30"]\nbest = "T36"\nmissed = "H8.P6"\n',
    "wind-tunnel/wt-002": (
        'contrast = ["T1", "T3"]\nbest = "none"\nbest_reason = "no trial without shedding"\n'
        'missed = "none"\nmissed_reason = "no prediction missed"\n'
    ),
    "wind-tunnel/wt-003": (
        'contrast = "none"\ncontrast_reason = "no trial was run"\nbest = "none"\n'
        'best_reason = "no trial was run"\nmissed = "none"\nmissed_reason = "no trial was run"\n'
    ),
    "wind-tunnel/wt-004": 'contrast = ["T1", "T8"]\nbest = "T12"\nmissed = "H5.P3"\n',
}

COVER = """\
[miss]
application = "body-lab"
session = "body-2"
prediction = "H4.P1"

[[card]]
application = "wind-tunnel"
session = "wt-004"
trial = "T1"
kicker = "LAB I · BY DAYLIGHT"
title = "The Wind Tunnel"
engine = "OpenFOAM"
unit = "runs"

[[card]]
application = "body-lab"
session = "body-2"
trial = "T31"
kicker = "LAB II · KEPT SECRET"
title = "The Stitched Body"
engine = "MuJoCo"
unit = "trials"
"""


@pytest.fixture(scope="module")
def loaded() -> list[records.RecordModel]:
    return records.load(SESSIONS)


def _by(loaded: list[records.RecordModel], name: str) -> records.RecordModel:
    return next(r for r in loaded if r.name == f"sessions/{name}")


def _write(folder: Path, files: dict[str, str], cover: str | None = COVER) -> Path:
    for name, text in files.items():
        path = folder / f"{name}.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    if cover is not None:
        (folder / "cover.toml").write_text(cover, encoding="utf-8")
    return folder


def _refused(call, where_part: str, problem_part: str) -> None:
    with pytest.raises(NotebookError) as caught:
        call()
    assert where_part in caught.value.where
    assert problem_part in caught.value.problem


# Accepted files


def test_the_approved_content_is_accepted(tmp_path: Path, loaded) -> None:
    folder = _write(tmp_path, VALID)
    found = choices.load(folder, loaded)
    assert sorted(found) == [
        ("body-lab", "body-1"),
        ("body-lab", "body-2"),
        ("wind-tunnel", "wt-002"),
        ("wind-tunnel", "wt-003"),
        ("wind-tunnel", "wt-004"),
    ]
    body2 = found[("body-lab", "body-2")]
    assert body2.contrast.value == ("T25", "T30")
    assert body2.best.value == ("T36",)
    assert body2.missed.value == ("H8.P6",)
    wt2 = found[("wind-tunnel", "wt-002")]
    assert wt2.best.value is None and wt2.best.reason == "no trial without shedding"
    cover = choices.load_cover(folder, loaded)
    assert (cover.miss.session, cover.miss.prediction) == ("body-2", "H4.P1")
    assert cover.miss.outcome is not None and cover.miss.outcome.trial == "T12"
    assert [(c.application, c.session, c.trial) for c in cover.cards] == [
        ("wind-tunnel", "wt-004", "T1"),
        ("body-lab", "body-2", "T31"),
    ]


def test_a_reason_of_300_characters_is_accepted(tmp_path: Path, loaded) -> None:
    text = f'contrast = ["T1", "T3"]\nbest = "none"\nbest_reason = "{"r" * 300}"\nmissed = "none"\n'
    path = _write(tmp_path, {"wind-tunnel/wt-002": text + 'missed_reason = "m"\n'}, cover=None)
    choice = choices.load_file(path / "wind-tunnel/wt-002.toml", _by(loaded, "wind-tunnel/wt-002"))
    assert choice.best.reason == "r" * 300


def test_none_for_the_miss_is_accepted_with_a_reason_when_the_record_has_a_miss(tmp_path, loaded) -> None:
    text = 'contrast = ["T25", "T30"]\nbest = "T36"\nmissed = "none"\nmissed_reason = "a reason"\n'
    folder = _write(tmp_path, {"body-lab/body-2": text}, cover=None)
    choice = choices.load_file(folder / "body-lab/body-2.toml", _by(loaded, "body-lab/body-2"))
    assert choice.missed.value is None and choice.missed.reason == "a reason"


# Refused choice files: each names the file and the key


BODY2 = "body-lab/body-2"


@pytest.mark.parametrize(
    ("text", "key", "problem"),
    [
        ('contrast = ["T25", "T30"]\nbest = "T36"\n', "key missed", "missing"),
        (VALID[BODY2] + 'extra = "x"\n', "key extra", "unknown key"),
        (VALID[BODY2] + 'best_reason = "x"\n', "key best_reason", 'only when best is "none"'),
        ('contrast = ["T25", "T30"]\nbest = "none"\nmissed = "H8.P6"\n', "key best_reason", "required"),
        (
            'contrast = ["T25", "T30"]\nbest = "none"\nbest_reason = ""\nmissed = "H8.P6"\n',
            "key best_reason",
            "1 to 300 characters",
        ),
        (
            f'contrast = ["T25", "T30"]\nbest = "none"\nbest_reason = "{"r" * 301}"\nmissed = "H8.P6"\n',
            "key best_reason",
            "it has 301",
        ),
        ('contrast = ["T25", "T25"]\nbest = "T36"\nmissed = "H8.P6"\n', "key contrast", "same trial twice"),
        ('contrast = ["T25"]\nbest = "T36"\nmissed = "H8.P6"\n', "key contrast", "list of two trial ids"),
        ('contrast = ["T25", "T99"]\nbest = "T36"\nmissed = "H8.P6"\n', "key contrast", "'T99' is not in"),
        ('contrast = ["T25", "T30"]\nbest = "T99"\nmissed = "H8.P6"\n', "key best", "'T99' is not in"),
        ('contrast = ["T25", "T30"]\nbest = "T36"\nmissed = "H99.P1"\n', "key missed", "not in the record"),
        ('contrast = ["T25", "T30"]\nbest = 5\nmissed = "H8.P6"\n', "key best", "must be a string"),
    ],
)
def test_a_bad_choice_is_refused_naming_file_and_key(tmp_path: Path, loaded, text, key, problem) -> None:
    folder = _write(tmp_path, {BODY2: text}, cover=None)
    path = folder / f"{BODY2}.toml"
    _refused(lambda: choices.load_file(path, _by(loaded, BODY2)), f"{path} {key}", problem)


def test_a_missed_prediction_that_is_a_hit_is_refused(tmp_path: Path, loaded) -> None:
    record = _by(loaded, BODY2)
    hit = next(o.prediction for o in record.outcomes if o.outcome == "hit")
    folder = _write(tmp_path, {BODY2: f'contrast = ["T25", "T30"]\nbest = "T36"\nmissed = "{hit}"\n'}, None)
    path = folder / f"{BODY2}.toml"
    _refused(lambda: choices.load_file(path, record), f"{path} key missed", "not 'miss'")


def test_a_record_without_trials_needs_none_everywhere(tmp_path: Path, loaded) -> None:
    text = VALID["wind-tunnel/wt-003"].replace(
        'best = "none"\nbest_reason = "no trial was run"\n', 'best = "T1"\n'
    )
    folder = _write(tmp_path, {"wind-tunnel/wt-003": text}, cover=None)
    path = folder / "wind-tunnel/wt-003.toml"
    _refused(
        lambda: choices.load_file(path, _by(loaded, "wind-tunnel/wt-003")),
        f"{path} key best",
        'must be "none"',
    )


def test_a_record_without_a_choice_file_is_refused(tmp_path: Path, loaded) -> None:
    files = {k: v for k, v in VALID.items() if k != "wind-tunnel/wt-004"}
    folder = _write(tmp_path, files)
    _refused(lambda: choices.load(folder, loaded), "wind-tunnel/wt-004.toml", "has no choice file")


def test_a_choice_file_without_a_record_is_refused(tmp_path: Path, loaded) -> None:
    folder = _write(tmp_path, VALID | {"wind-tunnel/wt-009": VALID["wind-tunnel/wt-003"]})
    _refused(lambda: choices.load(folder, loaded), "wind-tunnel/wt-009.toml", "names no record")


def test_a_stray_file_in_the_choices_folder_is_refused(tmp_path: Path, loaded) -> None:
    folder = _write(tmp_path, VALID)
    (folder / "body-lab" / "notes.txt").write_text("x", encoding="utf-8")
    _refused(lambda: choices.load(folder, loaded), "body-lab/notes.txt", "not a choice file")


# Refused cover files: each names the file and the key


@pytest.mark.parametrize(
    ("old", "new", "key", "problem"),
    [
        (
            'application = "body-lab"\nsession = "body-2"\nprediction',
            'application = "wind-tunnel"\nsession = "wt-002"\nprediction',
            "key miss session",
            "stopped",
        ),
        ('prediction = "H4.P1"', 'prediction = "H9.P9"', "key miss prediction", "not in the record"),
        ('prediction = "H4.P1"', 'prediction = "none"', "key miss prediction", "has a missed prediction"),
        ('prediction = "H4.P1"', 'prediction = "H4.P1"\nextra = 1', "key miss", "unknown key"),
        ('trial = "T31"', 'trial = "T99"', "key card 2 trial", "'T99' is not in"),
        ('session = "wt-004"', 'session = "wt-002"', "key card 1 session", "stopped"),
        ('session = "wt-004"', 'session = "wt-005"', "key card 1 session", "names no record"),
        (
            'application = "wind-tunnel"\nsession = "wt-004"\ntrial = "T1"',
            'application = "body-lab"\nsession = "body-1"\ntrial = "T1"',
            "key card 2",
            "a second card",
        ),
    ],
)
def test_a_bad_cover_is_refused_naming_file_and_key(tmp_path: Path, loaded, old, new, key, problem) -> None:
    assert old in COVER
    folder = _write(tmp_path, {}, cover=COVER.replace(old, new, 1))
    _refused(lambda: choices.load_cover(folder, loaded), f"{folder / 'cover.toml'} {key}", problem)


def test_a_cover_prediction_that_is_a_hit_is_refused(tmp_path: Path, loaded) -> None:
    hit = next(o.prediction for o in _by(loaded, BODY2).outcomes if o.outcome == "hit")
    folder = _write(tmp_path, {}, cover=COVER.replace('"H4.P1"', f'"{hit}"'))
    _refused(lambda: choices.load_cover(folder, loaded), "cover.toml key miss prediction", "not 'miss'")


def test_a_cover_without_a_card_for_an_application_is_refused(tmp_path: Path, loaded) -> None:
    cut = COVER.split('[[card]]\napplication = "body-lab"')[0]
    folder = _write(tmp_path, {}, cover=cut)
    _refused(lambda: choices.load_cover(folder, loaded), "cover.toml key card", "no card for the application")


def test_a_missing_cover_file_is_refused(tmp_path: Path, loaded) -> None:
    _refused(lambda: choices.load_cover(tmp_path, loaded), "cover.toml", "missing")
