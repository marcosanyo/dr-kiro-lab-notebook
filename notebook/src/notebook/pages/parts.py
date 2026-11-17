"""Shared page parts: stamp, sticky note, tab, legend link (design 9). Task 7.5.

Every part returns a list of segments. Commentary comes only from `text.py` (`say`); record text keeps the ink
of its recorded author. Every `href` comes from `addresses.py`, which checks the ids it puts in an address.
"""

from bench.specfiles.discovered import STATUSES

from notebook import addresses, html, text
from notebook.errors import NotebookError
from notebook.ink import Ink, Segment, commentary, markup


def say(name: str) -> Segment:
    """The commentary string `name` of `text.py`, as a segment whose source names it."""
    return commentary(getattr(text, name), text.source(name))


def say_text(name: str) -> list[Segment]:
    """The commentary string `name` in its ink."""
    return html.text(say(name))


def link(href: str, children: list[Segment]) -> list[Segment]:
    """`<a href>`; `href` comes from `addresses.py`, the one place that builds the site's addresses."""
    return html.element("a", {"href": href}, children)


def row_link(row_id: str, source: str, children: list[Segment]) -> list[Segment]:
    """A link to a row of the table on the same page (`#row-<id>`)."""
    return link(addresses.here(addresses.row(row_id, source)), children)


def stamp(status: Segment, label: str) -> list[Segment]:
    """A status word in the bench's stamp style, with its label below (Requirements 8.2, 15.2).

    The word is shown exactly as written. It gets its stamp colour only when it is exactly one of the four
    status words; any other cell is a plain `.stamp`. `label` is the name of a label in `text.py`."""
    classes = "stamp"
    if status.text in STATUSES:
        classes += f" stamp-{status.text}"
    return [
        *html.element("span", {"class": classes}, html.text(status)),
        *html.element("span", {"class": "stamp-label"}, say_text(label)),
    ]


def sticky(children: list[Segment], *, stamped: bool = False) -> list[Segment]:
    """A sticky note in commentary ink; `stamped` gives the stamp border of the refused-end note."""
    return html.element("aside", {"class": "sticky sticky-stamp" if stamped else "sticky"}, children)


def tab(target_id: Segment, target_rule: Segment, source: str) -> list[Segment]:
    """The "replaced by <id>" tab: a `<details>` whose content is the replacing row's rule text in small type
    and a link to that row in its own place (Requirement 8.3)."""
    summary = html.element("summary", None, [*say_text("REPLACED_BY"), *html.text(target_id)])
    content = [
        *html.element("span", {"class": "rule-small"}, html.text(target_rule)),
        *say_text("LIST_SEPARATOR"),
        *row_link(target_id.text, source, html.text(target_id)),
    ]
    return html.element("details", {"class": "tab"}, [*summary, *content])


def drkiro_block(segment: Segment) -> list[Segment]:
    """A block of Dr. Kiro's text with the label "written by Dr. Kiro" (visual steering, `.block-k`)."""
    return [
        *html.element("span", {"class": "block-label"}, say_text("WRITTEN_BY_DRKIRO")),
        *html.text(segment, block=True),
    ]


def chosen() -> list[Segment]:
    """The label of every chosen item (Requirement 12.7)."""
    return html.element("span", {"class": "block-label"}, say_text("CHOSEN_BY_A_PERSON"))


# The Halloween decoration: a cobweb corner and a small bat, drawn with paths only (visual steering,
# "Halloween"; design N28). Coordinates in a 64 x 128 box.
_WEB = (
    "M0 0 L64 0",
    "M0 0 L0 64",
    "M0 0 L60 60",
    "M0 0 L32 62",
    "M0 0 L62 32",
    "M14 0 Q12 12 0 14",
    "M28 0 Q26 18 18 18 Q18 26 0 28",
    "M44 0 Q41 24 30 30 Q24 41 0 44",
    "M60 0 Q56 32 44 44 Q32 56 0 60",
)
_BAT = (
    "M32 100 C28 94 20 92 10 94 C14 97 15 100 14 104 C18 102 22 103 24 106 C26 103 29 102 32 104 "
    "C35 102 38 103 40 106 C42 103 46 102 50 104 C49 100 50 97 54 94 C44 92 36 94 32 100 Z",
    "M29 97 L30 93 L32 96 L34 93 L35 97 Z",
)


def decoration() -> list[Segment]:
    """The Halloween decoration as inline SVG: no text, hidden from assistive technology, no namespace
    attribute (HTML puts an inline `<svg>` in the SVG namespace by itself). It is drawn in `currentColor`, and
    the stylesheet shows it only in the page gutter from 1000px (Requirement 6.5)."""
    web = html.element(
        "g",
        {
            "fill": "none",
            "stroke": "currentColor",
            "stroke-width": "1",
            "stroke-linecap": "round",
            "opacity": "0.55",
        },
        [segment for d in _WEB for segment in html.element("path", {"d": d}, [])],
    )
    bat = [
        segment
        for d in _BAT
        for segment in html.element("path", {"d": d, "fill": "currentColor", "opacity": "0.8"}, [])
    ]
    # HTML parsers turn `viewbox` into the SVG attribute `viewBox`; `html.py` takes lowercase names only.
    # In HTML, an SVG element left open would hold the elements after it, so each one has an end tag.
    return html.element(
        "svg",
        {
            "class": "deco",
            "viewbox": "0 0 64 128",
            "width": "64",
            "height": "128",
            "aria-hidden": "true",
            "focusable": "false",
        },
        [*web, *bat],
    )


def legend_link() -> list[Segment]:
    """The footer link to the ink legend (Requirement 4.5). Every page is at the site root (design N28)."""
    return html.element("footer", {"class": "footer"}, link(addresses.LEGEND, say_text("LEGEND_LINK")))


def page(title: str, children: list[Segment]) -> list[Segment]:
    """A whole page at the site root: the head with the stylesheet, the decoration, `children` in the content
    column, the footer link to the ink legend, and the page script. `title` is the name of a string in
    `text.py`. The `<title>` holds plain text, so its segment is not wrapped in an ink element."""
    head = html.element(
        "head",
        None,
        [
            *html.void("meta", {"charset": "utf-8"}),
            *html.void("meta", {"name": "viewport", "content": "width=device-width, initial-scale=1"}),
            *html.element("title", None, [say(title)]),
            *html.void("link", {"rel": "stylesheet", "href": addresses.STYLESHEET}),
        ],
    )
    body = html.element(
        "body",
        None,
        [
            *decoration(),
            *html.element("main", {"class": "page"}, children),
            *legend_link(),
            *html.element("script", {"src": addresses.SCRIPT, "defer": "defer"}, []),
        ],
    )
    return [markup("<!doctype html>\n"), *html.element("html", {"lang": "en"}, [*head, *body]), markup("\n")]


def with_fixture_banner(segments: list[Segment], where: str) -> list[Segment]:
    """A whole page (from `page`) with the "test fixture" banner as the first thing in its body (design N19).
    Only `build(..., allow_fake=True)` calls this; the command line cannot."""
    opens = [i for i, s in enumerate(segments) if s.ink is Ink.MARKUP and s.text == "<body>"]
    if len(opens) != 1:
        raise NotebookError(
            where, f"a page needs exactly one <body> to carry the fixture banner, found {len(opens)}"
        )
    banner = sticky(html.element("p", None, say_text("FIXTURE_BANNER")))
    at = opens[0] + 1
    return [*segments[:at], *banner, *segments[at:]]
