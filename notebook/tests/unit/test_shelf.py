"""The choice files, the best-so-far series and the shelf page on the labelled fixture session (notebook-shelf
design 2 to 5). The record is fake (`fixtures.session`); its numbers are not results."""

import re

import pytest

from fixtures.choices import APP, CHOICE, write_app
from fixtures.session import accepted_session
from notebook import choices, progress, records
from notebook.errors import NotebookError


@pytest.fixture(scope="module")
def record(tmp_path_factory):
    made = accepted_session(tmp_path_factory.mktemp("shelf") / "lab")
    (loaded,) = records.load(made.sessions, allow_fake=True)
    return loaded


def _write(tmp_path, text, name="s1.toml"):
    folder = tmp_path / "fake"
    folder.mkdir(exist_ok=True)
    path = folder / name
    path.write_text(text)
    return path


def test_a_valid_choice_file_is_read(tmp_path, record):
    chosen = choices.load_file(_write(tmp_path, CHOICE), record)
    assert chosen.title == "A Fake Notebook"
    assert [p.trial for p in chosen.polaroids] == ["T7", "T1"]
    assert chosen.progress.measurement == "distance"


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        ('trial = "T7"', 'trial = "T99"', "not a trial"),
        ('trial = "T7"', 'trial = "T1"', "different trials"),
        ('measurement = "distance"', 'measurement = "nothing"', "not a scalar measurement"),
        ('measurement = "distance"', 'measurement = "trace"', "not a scalar measurement"),
        ('better = "higher"', 'better = "up"', "must be one of"),
        ('color = "violet"', 'color = "pink"', "must be one of"),
        ('date = "2026-01-01"', 'date = "1 Jan"', "YYYY-MM-DD"),
        ('title = "A Fake Notebook"', 'title = "A Fake Notebook"\nextra = 1', "unknown key"),
        ('line = "A fixture line."', 'line = ""', "non-empty"),
    ],
)
def test_a_bad_choice_file_fails_naming_the_key(tmp_path, record, old, new, problem):
    assert old in CHOICE
    with pytest.raises(NotebookError, match=problem) as caught:
        choices.load_file(_write(tmp_path, CHOICE.replace(old, new)), record)
    assert str(tmp_path) in caught.value.where


def test_the_file_needs_two_photos_and_a_progress_table(tmp_path, record):
    one = CHOICE[: CHOICE.index('[[polaroid]]\nheading = "Best"')]
    with pytest.raises(NotebookError, match="needs 2"):
        choices.load_file(_write(tmp_path, one), record)
    no_progress = re.sub(r"\[progress\]\n.*?\n\n", "", CHOICE, flags=re.S)
    with pytest.raises(NotebookError, match="needs a .progress. table"):
        choices.load_file(_write(tmp_path, no_progress), record)


def test_an_application_folder_gives_its_settings_and_choices(tmp_path, record):
    apps = choices.load_apps([write_app(tmp_path / "fake-app")], [record])
    (app,) = apps.apps
    assert (app.application, app.open, app.unit, app.theme, app.pen, app.decoration) == (
        "fake",
        "s1",
        "runs",
        "day",
        "blue",
        "none",
    )
    assert app.display is None and set(apps.choices) == {("fake", "s1")}


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        ('open = "s1"', 'open = "s9"', "names no record"),
        ('theme = "day"', 'theme = "dusk"', "must be one of"),
        ('pen = "blue"', 'pen = "red"', "must be one of"),
        ('decoration = "none"', 'decoration = "pumpkins"', "must be one of"),
        ("order = 1", "order = 0", "whole number from 1"),
        ('application = "fake"', 'application = "other"', "no session of"),
        ('unit = "runs"', 'unit = "runs"\nextra = 1', "unknown key"),
        ('unit = "runs"', 'unit = "runs"\ndisplay = "nowhere"', "is not a folder"),
    ],
)
def test_a_bad_application_file_fails_naming_the_key(tmp_path, record, old, new, problem):
    folder = write_app(tmp_path / "fake-app")
    assert old in APP
    (folder / "app.toml").write_text(APP.replace(old, new))
    with pytest.raises(NotebookError, match=problem) as caught:
        choices.load_apps([folder], [record])
    assert str(folder) in caught.value.where


def test_every_application_of_the_records_needs_a_folder_and_every_session_a_choice_file(tmp_path, record):
    with pytest.raises(NotebookError, match="no notebook folder is given for the application fake"):
        choices.load_apps([], [record])
    folder = write_app(tmp_path / "fake-app")
    (folder / "choices" / "s1.toml").rename(folder / "choices" / "s2.toml")
    with pytest.raises(NotebookError, match="names no record"):
        choices.load_apps([folder], [record])


def test_the_best_so_far_never_gets_worse_and_names_the_trial_that_set_it(tmp_path, record):
    chosen = choices.load_file(_write(tmp_path, CHOICE), record)
    found = progress.series(record, chosen.progress)
    assert [p.trial.id for p in found.points] == [t.id for t in record.trials]
    bests = [p.best for p in found.points if p.best is not None]
    assert bests == sorted(bests)
    improved = [p for p in found.points if p.improved]
    assert improved and improved[0].delta is None
    assert all(p.delta is not None and p.delta > 0 for p in improved[1:])
    assert found.best is improved[-1]
    assert found.best.value == max(p.raw for p in found.points if p.raw is not None)


def test_the_lower_direction_and_a_second_measurement_pick_the_counting_trials(tmp_path, record):
    lower = CHOICE.replace('better = "higher"', 'better = "lower"')
    found = progress.series(record, choices.load_file(_write(tmp_path, lower), record).progress)
    bests = [p.best for p in found.points if p.best is not None]
    assert bests == sorted(bests, reverse=True)
    never = lower.replace('better = "lower"', 'better = "lower"\nrequire = "distance"\nequals = -12345')
    found = progress.series(record, choices.load_file(_write(tmp_path, never), record).progress)
    assert found.best is None and all(p.value is None for p in found.points)
    assert progress.best_value_text(found) is None


def test_prediction_counts_come_from_the_outcomes(record):
    counts = progress.predictions(record)
    assert counts.total == len(record.outcomes)
    assert counts.hit == sum(1 for o in record.outcomes if o.outcome == "hit")


def test_three_notes_are_chosen_and_a_miss_note_names_a_missed_prediction(tmp_path, record):
    chosen = choices.load_file(_write(tmp_path, CHOICE), record)
    assert [n.kind for n in chosen.notes] == ["best", "hits", "trials"]
    missed = [o.prediction for o in record.outcomes if o.outcome == "miss"]
    assert missed
    swapped = CHOICE.replace('kind = "trials"', f'kind = "miss"\nprediction = "{missed[0]}"')
    assert choices.load_file(_write(tmp_path, swapped), record).notes[2].prediction == missed[0]


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        ('kind = "trials"', 'kind = "luck"', "must be one of"),
        ('kind = "trials"', 'kind = "hits"', "different things"),
        ('kind = "trials"', 'kind = "miss"', "names its .prediction."),
        ('kind = "trials"', 'kind = "miss"\nprediction = "H1.P1"', "not a missed prediction"),
        ('kind = "trials"', 'kind = "trials"\nprediction = "H2.P1"', "names its .prediction."),
    ],
)
def test_a_bad_note_fails_naming_the_key(tmp_path, record, old, new, problem):
    with pytest.raises(NotebookError, match=problem):
        choices.load_file(_write(tmp_path, CHOICE.replace(old, new)), record)


def test_the_file_needs_exactly_three_notes(tmp_path, record):
    two = CHOICE[: CHOICE.rindex("[[note]]")]
    with pytest.raises(NotebookError, match="needs 3"):
        choices.load_file(_write(tmp_path, two), record)


def test_a_flag_names_the_first_trial_where_a_measurement_takes_a_value(tmp_path, record):
    flagged = CHOICE.replace(
        'better = "higher"',
        'better = "higher"\nmark = "distance"\nmark_equals = 0.3\nmark_words = "turns up"',
    )
    chosen = choices.load_file(_write(tmp_path, flagged), record)
    found = progress.series(record, chosen.progress)
    values = [dict(t.measurements)["distance"] for t in record.trials]
    expected = next((i for i, v in enumerate(values) if v == 0.3), None)
    assert found.mark_index == expected
    assert (
        progress.series(record, choices.load_file(_write(tmp_path, CHOICE), record).progress).mark_index
        is None
    )


def test_a_flag_needs_its_three_keys_and_a_scalar_measurement(tmp_path, record):
    base = 'better = "higher"'
    with pytest.raises(NotebookError, match="given together"):
        choices.load_file(_write(tmp_path, CHOICE.replace(base, base + '\nmark = "distance"')), record)
    three = '\nmark = "trace"\nmark_equals = 0\nmark_words = "x"'
    with pytest.raises(NotebookError, match="not a scalar measurement"):
        choices.load_file(_write(tmp_path, CHOICE.replace(base, base + three)), record)
