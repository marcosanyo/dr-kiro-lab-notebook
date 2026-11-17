"""Shared page parts (task 7.5): stamp classes, the tab, the legend link."""

import pytest

from notebook import ink, text
from notebook.errors import NotebookError
from notebook.ink import Ink, Segment
from notebook.pages import parts


def _html(segments: list[Segment]) -> str:
    return ink.join(segments)[0]


def test_stamp_colour_only_for_the_four_words() -> None:
    page = _html(parts.stamp(ink.stamp("rejected", "fixture"), "CHECKED"))
    assert '<span class="stamp stamp-rejected">' in page and text.CHECKED in page
    page = _html(parts.stamp(ink.stamp("Rejected ", "fixture"), "NOT_CHECKED"))
    assert '<span class="stamp">' in page and "Rejected " in page and text.NOT_CHECKED in page


def test_tab_links_the_target_row_and_shows_its_rule() -> None:
    target = Segment("R5", Ink.DRKIRO, "fixture")
    rule = Segment("a <rule> & more", Ink.DRKIRO, "fixture")
    page = _html(parts.tab(target, rule, "fixture"))
    assert page.startswith('<details class="tab"><summary>')
    assert 'href="#row-R5"' in page
    assert "a &lt;rule&gt; &amp; more" in page


def test_a_bad_row_id_is_never_put_in_a_link() -> None:
    with pytest.raises(NotebookError):
        parts.row_link('R1" onclick="x', "fixture", [])


def test_legend_link_is_relative_at_the_site_root() -> None:
    page = _html(parts.legend_link())
    assert '<footer class="footer"><a href="legend.html">' in page
    assert ".." not in page and "/" not in page.split('href="', 1)[1].split('"', 1)[0]


def test_sticky_note_and_blocks_use_no_generic_block_element() -> None:
    page = _html(parts.sticky([], stamped=True))
    assert page == '<aside class="sticky sticky-stamp"></aside>'
    page = _html(parts.drkiro_block(Segment("\nfirst line kept", Ink.DRKIRO, "fixture")))
    assert '<p class="ink-k block-k">\nfirst line kept</p>' in page
    assert "<div" not in page
