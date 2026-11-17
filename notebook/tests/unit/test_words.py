"""Unit tests of the commentary word list check (task 6.4, Requirement 5.5).

The word lists here are test lists written into `tmp_path`. They are not the committed
`notebook/commentary-words.txt`, whose content needs the user's approval.
"""

from pathlib import Path

import pytest

from notebook.errors import NotebookError
from notebook.words import load, parse


def test_parse_names_the_given_source() -> None:
    with pytest.raises(NotebookError) as caught:
        parse("Foo\n", "test list")
    assert caught.value.where == "test list line 1"


TEST_LIST = "# test list, not the committed word list\nfoo\n\nbarn  # a trailing comment\n"


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "test-words.txt"
    path.write_text(text, encoding="utf-8")
    return path


def test_parser_reads_words_and_skips_comments_and_blanks(tmp_path: Path) -> None:
    words = load(_write(tmp_path, TEST_LIST))
    assert words.words == ("foo", "barn")
    assert words.source == str(tmp_path / "test-words.txt")


@pytest.mark.parametrize(
    ("text", "where", "fragment"),
    [
        ("foo\nFoo\n", "line 2", "is not one lowercase word"),
        ("foo bar\n", "line 1", "is not one lowercase word"),
        ("foo-bar\n", "line 1", "is not one lowercase word"),
        ("foo1\n", "line 1", "is not one lowercase word"),
        ("caf\u00e9\n", "line 1", "is not one lowercase word"),
        ("foo\n# x\nfoo\n", "line 3", "already listed on line 1"),
        ("# only a comment\n\n", "test-words.txt", "holds no word"),
    ],
)
def test_parser_refuses(tmp_path: Path, text: str, where: str, fragment: str) -> None:
    with pytest.raises(NotebookError) as caught:
        load(_write(tmp_path, text))
    assert where in caught.value.where
    assert fragment in caught.value.problem


def test_missing_file_is_named(tmp_path: Path) -> None:
    path = tmp_path / "absent.txt"
    with pytest.raises(NotebookError) as caught:
        load(path)
    assert caught.value.where == str(path)


@pytest.mark.parametrize("suffix", ["", "s", "es", "ed", "ing"])
def test_planted_word_with_each_suffix_fails(tmp_path: Path, suffix: str) -> None:
    words = load(_write(tmp_path, TEST_LIST))
    text = f"The body moved, then foo{suffix}, then stopped."
    with pytest.raises(NotebookError) as caught:
        words.check(text, "text.py SAMPLE")
    assert caught.value.where == "text.py SAMPLE"
    assert f'"foo{suffix}" (listed word "foo")' in caught.value.problem


def test_match_ignores_case_and_punctuation(tmp_path: Path) -> None:
    words = load(_write(tmp_path, TEST_LIST))
    assert words.matches("FOO! (Barns)") == [("foo", "foo"), ("barns", "barn")]


def test_digits_and_underscores_split_tokens(tmp_path: Path) -> None:
    words = load(_write(tmp_path, TEST_LIST))
    assert words.matches("x_foo 2barn") == [("foo", "foo"), ("barn", "barn")]


@pytest.mark.parametrize(
    "text",
    [
        "foods and barnacles",  # the listed word is only the start of a longer word
        "a buffoon",  # the listed word is inside a longer word
    ],
)
def test_word_only_as_a_part_passes(tmp_path: Path, text: str) -> None:
    words = load(_write(tmp_path, TEST_LIST))
    assert words.matches(text) == []
    words.check(text, "text.py SAMPLE")


def test_other_suffixes_are_not_in_the_rule(tmp_path: Path) -> None:
    words = load(_write(tmp_path, TEST_LIST))
    assert words.matches("fooer fooly foosing barned") == [("barned", "barn")]


def test_every_finding_is_named(tmp_path: Path) -> None:
    words = load(_write(tmp_path, TEST_LIST))
    with pytest.raises(NotebookError) as caught:
        words.check("foo and barning", "text.py SAMPLE")
    assert '"foo" (listed word "foo")' in caught.value.problem
    assert '"barning" (listed word "barn")' in caught.value.problem
