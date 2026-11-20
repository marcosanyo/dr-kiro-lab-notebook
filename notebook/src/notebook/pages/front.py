"""The front page, `index.html` at the site root (notebook-shelf design 1).
A short page that says what the two applications have in common and where they differ: a bright door for the
application that opens by day, a dark door for the one that opens at night, and under both the one skeleton
they stand on, the notebook and the bench. The text of a door is written by a person in the application's
`app.toml`; the text of the skeleton is the builder's.
"""

from notebook import addresses, html
from notebook.choices import App
from notebook.ink import Segment, commentary
from notebook.pages import parts
from notebook.pages.parts import say_text


def _el(tag: str, cls: str | None, children: list[Segment], **attrs: str) -> list[Segment]:
    return html.element(tag, ({"class": cls} if cls else {}) | attrs, children)


def _door(app: App) -> list[Segment]:
    when = "DOOR_DAY" if app.theme == "day" else "DOOR_NIGHT"
    return html.element(
        "a",
        {"href": addresses.door(app.slug, app.source), "class": f"door door-{app.theme} door-{app.slug}"},
        [
            *_el("span", "door-case", html.text(commentary(app.case, app.source))),
            *_el("span", "door-title", html.text(commentary(app.door, app.source))),
            *_el("span", "door-line", html.text(commentary(app.door_line, app.source))),
            *_el("span", "door-open", say_text(when)),
        ],
    )


def page(apps: tuple[App, ...]) -> list[Segment]:
    """The front page of the site: the doors in the order of the applications, and the skeleton under them."""
    head = _el(
        "header",
        "front-head",
        [
            *_el("p", "kicker", say_text("FRONT_KICKER")),
            *_el("h1", "big-title", say_text("MASTHEAD_TITLE")),
            *_el("p", "front-claim", say_text("FRONT_CLAIM")),
            *_el("p", "front-tagline", say_text("FRONT_TAGLINE")),
            *_el("p", "front-lead", say_text("FRONT_LEAD")),
        ],
    )
    doors = _el("section", "doors", [s for app in apps for s in _door(app)])
    layers = _el(
        "ol",
        "skeleton-layers",
        [
            *html.element("li", {"class": "layer layer-notebook"}, say_text("SKELETON_NOTEBOOK")),
            *html.element("li", {"class": "layer layer-bench"}, say_text("SKELETON_BENCH")),
        ],
    )
    skeleton = _el(
        "section",
        "skeleton",
        [*_el("h2", "cap", say_text("SKELETON_HEADING")), *layers],
    )
    return parts.page("SHELF_TITLE", [*head, *doors, *skeleton])
