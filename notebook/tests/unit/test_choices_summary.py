"""The summary under a session's title is at most 40 words (notebook-shelf Requirement 2.3).
A longer one fails the build, naming the key; it is never cut."""

import pytest

from notebook import choices
from notebook.errors import NotebookError


def test_a_summary_of_forty_words_is_accepted() -> None:
    text = " ".join(["word"] * choices.SUMMARY_WORDS_MAX)
    assert choices._summary("x.toml key summary", text) == text


def test_a_summary_of_forty_one_words_fails_naming_the_key() -> None:
    text = " ".join(["word"] * (choices.SUMMARY_WORDS_MAX + 1))
    with pytest.raises(NotebookError) as caught:
        choices._summary("x.toml key summary", text)
    assert "x.toml key summary" in str(caught.value)
    assert "41 words" in str(caught.value)


def test_every_committed_choice_file_has_a_summary_within_the_limit() -> None:
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    files = sorted(root.glob("*/notebook/choices/*.toml"))
    assert files, "no choice files found"
    for path in files:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        assert len(data["summary"].split()) <= choices.SUMMARY_WORDS_MAX, path.name
