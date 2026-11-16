# Feature: lab-notebook, Property 1: Dr. Kiro's text round-trips through the HTML
"""For any string (with `<`, `>`, `&`, quotes, tab, line feed, carriage return and non-ASCII characters, and
without the other C0 control characters), rendering it as a Dr. Kiro segment and parsing the written HTML with
`html.parser` gives an element whose text content equals the string character for character; a string with
another C0 control character fails the build, naming its source.

**Validates: Requirements 4.3, 4.4**
"""

from html.parser import HTMLParser

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from notebook import html as nbhtml
from notebook import ink
from notebook.errors import NotebookError

SOURCE = "fixture-record/log.jsonl line 7"

# The C0 control characters other than tab, line feed and carriage return.
FORBIDDEN = [chr(c) for c in range(0x20) if chr(c) not in "\t\n\r"]

# Characters HTML must keep as written: markup characters, quotes, the allowed white space, and any
# non-control character (surrogates excluded, as they cannot be written as UTF-8).
_SPECIAL = st.sampled_from(list("<>&\"'\t\n\r") + ["&amp;", "&#13;", "</span>", "<!--", "]]>", "\r\n"])
_GENERAL = st.characters(blacklist_categories=("Cs",), blacklist_characters="".join(FORBIDDEN))
allowed_text = st.lists(st.one_of(_SPECIAL, _GENERAL.map(str)), max_size=40).map("".join)


class _Collector(HTMLParser):
    """Collects the text content of the one top-level element of a rendered segment."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.tags: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.depth += 1

    def handle_endtag(self, tag):
        self.depth -= 1

    def handle_data(self, data):
        assert self.depth == 1, "text outside the element"
        self.text.append(data)

    def handle_comment(self, data):
        raise AssertionError(f"text was read as a comment: {data!r}")


def _render(text: str, block: bool) -> str:
    segment = ink.Segment(text, ink.Ink.DRKIRO, SOURCE)
    written, _ = ink.join(nbhtml.text(segment, block=block))
    return written


@settings(max_examples=200)
@given(text=allowed_text, block=st.booleans())
def test_drkiro_text_round_trips(text, block):
    written = _render(text, block)
    parser = _Collector()
    parser.feed(written)
    parser.close()
    assert parser.tags == (["div"] if block else ["span"])
    assert parser.depth == 0
    assert "".join(parser.text) == text


@settings(max_examples=100)
@given(
    before=allowed_text,
    bad=st.sampled_from(FORBIDDEN),
    after=allowed_text,
    block=st.booleans(),
)
def test_other_control_character_fails_naming_source(before, bad, after, block):
    with pytest.raises(NotebookError) as caught:
        _render(before + bad + after, block)
    assert caught.value.where == SOURCE
    assert f"U+{ord(bad):04X}" in str(caught.value)
