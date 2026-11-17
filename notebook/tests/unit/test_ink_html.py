"""Unit tests for ink.py and html.py (task 3.1; Requirements 4.1, 4.3, 20.3)."""

import json
from html.parser import HTMLParser
from pathlib import Path

import pytest
from bench.scan.levels import sidecar_pieces

from notebook import html as h
from notebook.errors import NotebookError
from notebook.ink import Authored, Ink, Segment, commentary, join, pencil, stamp


class _Content(HTMLParser):
    """Collects the text content of the first element with a given class."""

    def __init__(self, cls: str) -> None:
        super().__init__(convert_charrefs=True)
        self.cls = cls
        self.depth = 0
        self.text = ""

    def handle_starttag(self, tag, attrs):
        if self.depth:
            self.depth += 1
        elif (self.cls in (dict(attrs).get("class") or "").split()) and not self.text:
            self.depth = 1

    def handle_endtag(self, tag):
        if self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.text += data


def _round_trip(value: str, block: bool) -> str:
    seg = Authored(value, "dr-kiro", "rec/log.jsonl line 3").segment()
    page, _ = join(h.element("p", None, h.text(seg, block=block)))
    parser = _Content("ink-k")
    parser.feed(page)
    parser.close()
    return parser.text


@pytest.mark.parametrize("block", [False, True])
def test_dr_kiro_text_shows_as_written(block):
    value = "a < b && c > \"d\" 'e'\n\tline two\r\nline three: ü, 実験, —"
    assert _round_trip(value, block) == value


def test_escaping_of_markup_characters_and_carriage_return():
    page, _ = join(h.text(Authored("<b>&\"'\r", "dr-kiro", "src").segment()))
    assert page == '<span class="ink-k">&lt;b&gt;&amp;&quot;&#x27;&#13;</span>'


def test_markdown_is_not_rendered():
    page, _ = join(h.text(Authored("**bold** <em>x</em>", "dr-kiro", "src").segment()))
    assert "<em>" not in page and "**bold**" in page


@pytest.mark.parametrize("char", ["\x00", "\x07", "\x0b", "\x0c", "\x1b", "\x1f"])
def test_control_character_fails_naming_the_source(char):
    seg = Authored(f"ok{char}ok", "dr-kiro", "body-2/log.jsonl line 7").segment()
    with pytest.raises(NotebookError) as error:
        join(h.text(seg))
    assert error.value.where == "body-2/log.jsonl line 7"
    assert f"U+{ord(char):04X}" in error.value.problem


def test_ink_follows_the_recorded_author():
    assert Authored("x", "dr-kiro", "s").segment().ink is Ink.DRKIRO
    assert Authored("x", "bench", "s").segment().ink is Ink.PENCIL
    with pytest.raises(NotebookError) as error:
        Authored("x", "someone", "wt-004/log.jsonl line 2").segment()
    assert error.value.where == "wt-004/log.jsonl line 2"


@pytest.mark.parametrize(
    ("kind", "good", "bad"),
    [
        ("experiment", "E12", ["E0", "e1", "E01", "E1 ", 'E1"', ""]),
        ("trial", "T3", ["T", "T-1", "X3"]),
        ("hypothesis", "H4", ["H04", "H4.P1"]),
        ("prediction", "H4.P1", ["H4", "H4.P0", "H4-P1"]),
        ("row", "R13", ["R0", "r13", "R13a"]),
    ],
)
def test_id_checks(kind, good, bad):
    assert h.check_id(kind, good, "src") == good
    for value in bad:
        with pytest.raises(NotebookError) as error:
            h.check_id(kind, value, "body-2/blobs/abc")
        assert error.value.where == "body-2/blobs/abc"


def test_ranges_of_a_three_segment_page(tmp_path: Path):
    segments = [
        *h.element("h1", {"id": "row-R1"}, [commentary("Table", "text.py")]),
        *h.text(Authored("x < 1", "dr-kiro", "rec/log.jsonl line 4").segment()),
        *h.text(stamp("validated", "rec/blobs/abc")),
    ]
    text, ranges = join(segments)
    k_open = '<h1 id="row-R1">Table</h1><span class="ink-k">'
    k_text = "x &lt; 1"
    assert text == k_open + k_text + '</span><span class="ink-s">validated</span>'
    assert ranges == [
        {"start": 0, "end": len(k_open), "author": "bench"},
        {"start": len(k_open), "end": len(k_open) + len(k_text), "author": "dr-kiro"},
        {"start": len(k_open) + len(k_text), "end": len(text), "author": "bench"},
    ]
    # The bench's sidecar reader accepts the ranges and sees Dr. Kiro's escaped text at its level.
    page = tmp_path / "index.html"
    page.write_text(text, encoding="utf-8")
    (tmp_path / "index.html.authors.json").write_text(json.dumps({"ranges": ranges}), encoding="utf-8")
    pieces = sidecar_pieces(page, text)
    assert [(p.text, p.level) for p in pieces] == [
        (k_open, "builder"),
        (k_text, "dr-kiro"),
        (text[len(k_open) + len(k_text) :], "builder"),
    ]


def test_ranges_count_code_points_and_skip_empty_segments():
    text, ranges = join(
        [pencil("実験", "s"), Segment("", Ink.DRKIRO, "s"), Authored("ü", "dr-kiro", "s").segment()]
    )
    assert text == "実験ü"
    assert ranges == [
        {"start": 0, "end": 2, "author": "bench"},
        {"start": 2, "end": 3, "author": "dr-kiro"},
    ]


def test_attribute_values_are_escaped_and_markup_is_not_text():
    page, _ = join(h.void("img", {"alt": 'a"b<'}))
    assert page == '<img alt="a&quot;b&lt;">'
    with pytest.raises(ValueError):
        h.text(Segment("<b>", Ink.MARKUP, "s"))
