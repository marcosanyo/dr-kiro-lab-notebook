"""Shared page parts: stamp, sticky note, tab, footer links (design 9). Task 7.5.

Every part returns a list of segments. Commentary comes only from `text.py` (`say`); record text keeps the ink
of its recorded author. Every `href` comes from `addresses.py`, which checks the ids it puts in an address.
"""

from typing import TYPE_CHECKING

from bench.specfiles.discovered import STATUSES

from notebook import addresses, html, text
from notebook.errors import NotebookError
from notebook.ink import Ink, Segment, commentary, markup

if TYPE_CHECKING:
    from notebook.choices import App


def say(name: str) -> Segment:
    """The commentary string `name` of `text.py`, as a segment whose source names it."""
    return commentary(getattr(text, name), text.source(name))


def say_text(name: str) -> list[Segment]:
    """The commentary string `name` in its ink."""
    return html.text(say(name))


def link(href: str, children: list[Segment]) -> list[Segment]:
    """`<a href>`; `href` comes from `addresses.py`, the one place that builds the site's addresses."""
    return html.element("a", {"href": href}, children)


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


# The Halloween decoration: drawn with paths only, no text, hidden from assistive technology (design N28).
# Each piece is its own inline SVG; the stylesheet places them at the corners of the page and shows the night
# pieces only at night and the day piece only by day. No namespace attribute (HTML puts an inline `<svg>` in
# the SVG namespace by itself) and no `<div>` (the generic block element is a term of the blind scan).
_WEB = (
    "M64 0 L0 0",
    "M64 0 L64 64",
    "M64 0 L4 60",
    "M64 0 L32 62",
    "M64 0 L2 32",
    "M50 0 Q52 12 64 14",
    "M36 0 Q38 18 46 18 Q46 26 64 28",
    "M20 0 Q23 24 34 30 Q40 41 64 44",
    "M4 0 Q8 32 20 44 Q32 56 64 60",
)
_BAT = (
    "M32 100 C28 94 20 92 10 94 C14 97 15 100 14 104 C18 102 22 103 24 106 C26 103 29 102 32 104 "
    "C35 102 38 103 40 106 C42 103 46 102 50 104 C49 100 50 97 54 94 C44 92 36 94 32 100 Z",
    "M29 97 L30 93 L32 96 L34 93 L35 97 Z",
)
_SPIDER_LIMBS = (
    "M20 22 Q10 12 4 18 M20 24 Q8 22 2 30 M20 26 Q10 32 6 42 M20 28 Q14 36 12 46 "
    "M28 22 Q38 12 44 18 M28 24 Q40 22 46 30 M28 26 Q38 32 42 42 M28 28 Q34 36 36 46"
)


def _svg(cls: str, box: str, width: int, height: int, children: list[Segment]) -> list[Segment]:
    # HTML parsers turn `viewbox` into the SVG attribute `viewBox`; `html.py` takes lowercase names only.
    return html.element(
        "svg",
        {
            "class": f"deco {cls}",
            "viewbox": box,
            "width": str(width),
            "height": str(height),
            "aria-hidden": "true",
            "focusable": "false",
        },
        children,
    )


def _path(d: str, **attrs: str) -> list[Segment]:
    return html.shape("path", {"d": d, **attrs})


def web(cls: str) -> list[Segment]:
    """A cobweb in the top right corner of its box, drawn in the colour of the text around it."""
    lines = html.element(
        "g",
        {"fill": "none", "stroke": "currentColor", "stroke-width": "1", "stroke-linecap": "round"},
        [s for d in _WEB for s in _path(d)],
    )
    return _svg(f"deco-web {cls}".strip(), "0 0 64 64", 120, 120, lines)


def decoration(kind: str) -> list[Segment]:
    """The pieces of an application's decoration. `none` has none (the page holds no drawing at all);
    `halloween` is the moon, cobweb, hanging spider and bats of the night lab."""
    if kind == "none":
        return []
    if kind != "halloween":
        raise ValueError(f"unknown decoration {kind!r}")
    moon = [
        *html.shape("circle", {"class": "moon-disc", "cx": "44", "cy": "44", "r": "34"}),
        *html.shape("circle", {"class": "moon-pit", "cx": "32", "cy": "36", "r": "6"}),
        *html.shape("circle", {"class": "moon-pit", "cx": "54", "cy": "52", "r": "8"}),
        *html.shape("circle", {"class": "moon-pit", "cx": "50", "cy": "28", "r": "4"}),
    ]
    spider = [
        *html.element(
            "path", {"class": "thread", "d": "M24 0 L24 64", "stroke": "currentColor", "fill": "none"}, []
        ),
        *html.element(
            "path",
            {
                "d": _SPIDER_LIMBS,
                "stroke": "currentColor",
                "fill": "none",
                "stroke-width": "1.6",
                "stroke-linecap": "round",
                "transform": "translate(0 66)",
            },
            [],
        ),
        *html.shape("ellipse", {"class": "spider-body", "cx": "24", "cy": "98", "rx": "9", "ry": "11"}),
        *html.shape("circle", {"class": "spider-head", "cx": "24", "cy": "84", "r": "6"}),
    ]
    bats = [s for d in _BAT for s in html.element("path", {"d": d, "fill": "currentColor"}, [])]
    return [
        *web(""),
        *_svg("deco-moon", "0 0 88 88", 140, 140, moon),
        *_svg("deco-spider", "0 0 48 112", 44, 100, spider),
        *_svg("deco-bat deco-bat-one", "0 88 64 24", 62, 24, bats),
        *_svg("deco-bat deco-bat-two", "0 88 64 24", 42, 16, bats),
        *_svg("deco-bat deco-bat-three", "0 88 64 24", 52, 20, bats),
        *_svg("deco-bat deco-bat-four", "0 88 64 24", 34, 13, bats),
    ]


def page_marks() -> list[Segment]:
    """The mad scientist's traces on the night lab's notebook page itself: green drips from the top edge (the
    burns along the edges are in the stylesheet). Paths only, no words, hidden from assistive technology,
    under the writing (design N28)."""
    drips = [
        *html.element(
            "path",
            {
                "d": "M0 0 H88 C86 5 83 9 82 16 C81 24 83 31 80 34 C77 37 74 33 75 26 C76 18 73 11 67 9 "
                "C62 13 63 22 62 34 C61 46 63 58 59 61 C55 64 52 59 53 50 C54 38 51 22 45 13 "
                "C41 17 40 22 39 27 C38 31 34 31 34 27 C34 20 30 12 24 9 C21 14 22 21 20 25 "
                "C18 29 14 27 15 22 C16 14 10 7 0 5 Z",
            },
            [],
        ),
    ]
    return [
        *_svg("mark mark-drips", "0 0 88 64", 88, 64, drips),
    ]


def footer(*, links: bool = True, at_bench: bool = False) -> list[Segment]:
    """The page footer: the links to the ink legend (Requirement 4.5) and to how the lab works, relative
    inside the application's folder, and a link to the front page. The front page has no footer links. At the
    bench only the legend is served, so only its link is left."""
    if not links:
        return html.element("footer", {"class": "footer"}, [])
    if at_bench:
        return html.element("footer", {"class": "footer"}, link(addresses.LEGEND, say_text("LEGEND_LINK")))
    return html.element(
        "footer",
        {"class": "footer"},
        [
            *link(addresses.LEGEND, say_text("LEGEND_LINK")),
            *say_text("LIST_SEPARATOR"),
            *link(addresses.HOW, say_text("HOW_LINK")),
            *say_text("LIST_SEPARATOR"),
            *link(addresses.apps_link("", "footer"), say_text("FRONT_LINK")),
        ],
    )


def framed(children: list[Segment]) -> list[Segment]:
    """Plain pages (the legend, how the lab works) set on the same paper as a notebook: one `article.book`
    with the binder holes, so no decoration of the page lies over the text."""
    holes = html.element(
        "span", {"class": "holes", "aria-hidden": "true"}, [markup("<span></span><span></span><span></span>")]
    )
    return html.element("article", {"class": "book plain-book"}, [*holes, *children])


def page(
    title: str, children: list[Segment], *, app: "App | None" = None, at_bench: bool = False
) -> list[Segment]:
    """A whole page: the head with the stylesheet, the decoration of its application, `children` in the
    content column, the footer, and the page script. `app` is None for the front page. The `<html>` element
    carries the application and the theme the page opens in (`data-app`, `data-mode`), so the page has its
    look before the script runs. `title` is the name of a string in `text.py`; the `<title>` is plain text."""
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
            *(decoration(app.decoration) if app is not None else []),
            *html.element("main", {"class": "page"}, children),
            *footer(links=app is not None, at_bench=at_bench),
            *html.element("script", {"src": addresses.SCRIPT, "defer": "defer"}, []),
            *(
                html.element("script", {"src": addresses.WATCH_SCRIPT, "defer": "defer"}, [])
                if at_bench
                else []
            ),
        ],
    )
    attrs = {"lang": "en", "data-app": "front", "data-mode": "night"}
    if app is not None:
        attrs = {"lang": "en", "data-app": app.slug, "data-mode": app.theme, "data-pen": app.pen}
    return [markup("<!doctype html>\n"), *html.element("html", attrs, [*head, *body]), markup("\n")]


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
