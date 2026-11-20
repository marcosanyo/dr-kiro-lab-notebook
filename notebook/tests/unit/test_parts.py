"""Shared page parts (task 7.5): stamp classes, the tab, the footer links."""

from notebook import ink, text
from notebook.ink import Segment
from notebook.pages import parts


def _html(segments: list[Segment]) -> str:
    return ink.join(segments)[0]


def test_stamp_colour_only_for_the_four_words() -> None:
    page = _html(parts.stamp(ink.stamp("rejected", "fixture"), "CHECKED"))
    assert '<span class="stamp stamp-rejected">' in page and text.CHECKED in page
    page = _html(parts.stamp(ink.stamp("Rejected ", "fixture"), "NOT_CHECKED"))
    assert '<span class="stamp">' in page and "Rejected " in page and text.NOT_CHECKED in page


def test_footer_links_the_legend_and_how_the_lab_works_inside_the_folder_and_the_front_page() -> None:
    page = _html(parts.footer())
    assert page.startswith('<footer class="footer"><a href="legend.html">')
    hrefs = [part.split('"', 1)[0] for part in page.split('href="')[1:]]
    assert hrefs == ["legend.html", "how.html", "/index.html"]
    assert text.HOW_LINK in page
    assert ".." not in page and all("/" not in href for href in hrefs[:2])
    assert parts.footer(links=False)[0].text == '<footer class="footer">'  # the front page has none


def test_sticky_note_and_blocks_use_no_generic_block_element() -> None:
    page = _html(parts.sticky([], stamped=True))
    assert page == '<aside class="sticky sticky-stamp"></aside>'
    assert "<div" not in page
