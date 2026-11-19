"""Shared page parts: stamp, sticky note, tab, footer links (design 9). Task 7.5.

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
_RAYS = (
    "M30 4 L30 14 M30 46 L30 56 M4 30 L14 30 M46 30 L56 30 "
    "M12 12 L19 19 M41 41 L48 48 M48 12 L41 19 M19 41 L12 48"
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


def decoration() -> list[Segment]:
    """The Halloween pieces: moon and cobweb (night), a sun (day), a hanging spider, bats and a pumpkin."""
    moon = [
        *html.shape("circle", {"class": "moon-disc", "cx": "44", "cy": "44", "r": "34"}),
        *html.shape("circle", {"class": "moon-pit", "cx": "32", "cy": "36", "r": "6"}),
        *html.shape("circle", {"class": "moon-pit", "cx": "54", "cy": "52", "r": "8"}),
        *html.shape("circle", {"class": "moon-pit", "cx": "50", "cy": "28", "r": "4"}),
    ]
    sun = [
        *html.shape("circle", {"class": "sun-disc", "cx": "30", "cy": "30", "r": "13"}),
        *html.element(
            "path",
            {"d": _RAYS, "stroke": "currentColor", "stroke-width": "3", "stroke-linecap": "round"},
            [],
        ),
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
    pumpkin = [
        *html.shape("ellipse", {"class": "pk-side", "cx": "24", "cy": "52", "rx": "20", "ry": "26"}),
        *html.shape("ellipse", {"class": "pk-side", "cx": "62", "cy": "52", "rx": "20", "ry": "26"}),
        *html.shape("ellipse", {"class": "pk-mid", "cx": "43", "cy": "52", "rx": "20", "ry": "28"}),
        *html.element("path", {"class": "pk-stem", "d": "M40 26 Q40 12 50 8 L54 14 Q46 17 47 26 Z"}, []),
        *html.element("path", {"class": "pk-face", "d": "M24 44 L36 44 L30 33 Z M50 44 L62 44 L56 33 Z"}, []),
        *html.element(
            "path",
            {"class": "pk-face", "d": "M22 58 L30 64 L36 58 L43 66 L50 58 L56 64 L64 58 Q43 80 22 58 Z"},
            [],
        ),
    ]
    return [
        *web(""),
        *_svg("deco-moon", "0 0 88 88", 96, 96, moon),
        *_svg("deco-sun", "0 0 60 60", 84, 84, sun),
        *_svg("deco-spider", "0 0 48 112", 44, 100, spider),
        *_svg("deco-bat deco-bat-one", "0 88 64 24", 54, 20, bats),
        *_svg("deco-bat deco-bat-two", "0 88 64 24", 38, 14, bats),
        *_svg("deco-pumpkin", "0 0 86 82", 104, 100, pumpkin),
    ]


def mode_button() -> list[Segment]:
    """The switch between the night lab and the day lab. It is hidden until the page script runs; without
    the script the notebook stays in the night lab."""
    return html.element(
        "button",
        {
            "type": "button",
            "class": "mode-toggle",
            "hidden": "hidden",
            "data-to-day": text.MODE_DAY,
            "data-to-night": text.MODE_NIGHT,
        },
        say_text("MODE_DAY"),
    )


def footer() -> list[Segment]:
    """The page footer: the link to the ink legend (Requirement 4.5) and, next to it, the link to how the lab
    works, `how.html` (user, 2026-11-17). Every page is at the site root, so both links are relative without
    `..` (design N28)."""
    return html.element(
        "footer",
        {"class": "footer"},
        [
            *link(addresses.LEGEND, say_text("LEGEND_LINK")),
            *say_text("LIST_SEPARATOR"),
            *link(addresses.HOW, say_text("HOW_LINK")),
        ],
    )


def page(title: str, children: list[Segment]) -> list[Segment]:
    """A whole page at the site root: the head with the stylesheet, the decoration, `children` in the content
    column, the footer with its links to the ink legend and to how the lab works, and the page script. `title`
    is the name of a string in `text.py`. The `<title>` holds plain text, so its segment is not wrapped in an
    ink element."""
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
            *mode_button(),
            *html.element("main", {"class": "page"}, children),
            *footer(),
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
