"""The front page, `index.html` at the site root (notebook-shelf design 1).
A short page that says what the two applications have in common and where they differ. Each application
has one card (a "door" in the code): a moving picture of the session its notebook opens on, what the lab is,
the one line a person wrote on that session, how many sessions its notebook holds, and a link "Open the
notebook". The day card is on the day paper and the night card on the night paper. Under both stands the one
skeleton they share, the notebook and the bench. The text of a card is written by a person (`app.toml` and
the choice file); the labels and the skeleton are the builder's.
"""

from notebook import addresses, html, layouts
from notebook.choices import App, Choices
from notebook.display import Retakes
from notebook.errors import NotebookError
from notebook.ink import Segment, commentary, markup, pencil
from notebook.pages import parts, photo
from notebook.pages.parts import say_text
from notebook.pages.photo import PictureFile
from notebook.records import RecordModel


def _el(tag: str, cls: str | None, children: list[Segment], **attrs: str) -> list[Segment]:
    return html.element(tag, ({"class": cls} if cls else {}) | attrs, children)


def _door(
    app: App,
    records: list[RecordModel],
    choices: dict[tuple[str, str], Choices],
    table: dict[str, layouts.Layout],
    retakes: Retakes,
) -> tuple[list[Segment], list[PictureFile]]:
    opened = next((r for r in records if r.session == app.open), None)
    if opened is None:
        raise NotebookError(app.source, f"names no record ({app.application}/{app.open})")
    chosen = choices[(opened.application, opened.session)]
    href = addresses.door(app.slug, app.source)
    figure: list[Segment] = []
    files: list[PictureFile] = []
    if chosen.polaroids:
        # The card shows the session's starred photo (its best result) when it has one, as the highlight does.
        first = next((p for p in chosen.polaroids if p.star), chosen.polaroids[0])
        trial = next(t for t in opened.trials if t.id == first.trial)
        layout = layouts.layout_for(table, opened.application, opened.name)
        figure, files = photo.photo(
            opened,
            trial,
            layout,
            "small",
            trial_word=False,
            retake=retakes.get((opened.application, opened.session, trial.id)),
        )
    count = str(len(records))
    found = [
        *say_text("DOOR_OPENS_ON"),
        *html.text(commentary(chosen.title, chosen.file)),
        markup(": "),
        *html.text(commentary(chosen.line, chosen.file)),
    ]
    link = [
        *html.element(
            "a", {"href": href, "class": "door-open"}, [*say_text("DOOR_OPEN"), markup(" &#8594;")]
        ),
        *_el(
            "span",
            "door-count",
            [
                *html.text(pencil(count, f"{app.source}: sessions")),
                *say_text("DOOR_SESSION" if count == "1" else "DOOR_SESSIONS"),
            ],
        ),
    ]
    out = _el(
        "article",
        f"door door-{app.theme} door-{app.slug}",
        [
            *figure,
            *_el("span", "door-case", html.text(commentary(app.case, app.source))),
            *_el(
                "h2",
                "door-title",
                html.element("a", {"href": href}, html.text(commentary(app.door, app.source))),
            ),
            *_el("p", "door-about", html.text(commentary(app.about, app.source))),
            *_el("p", "door-found", found),
            *_el("p", "door-actions", link),
        ],
    )
    return out, files


def page(
    apps: tuple[App, ...],
    records: list[RecordModel],
    choices: dict[tuple[str, str], Choices],
    table: dict[str, layouts.Layout],
    retakes: Retakes,
) -> tuple[list[Segment], tuple[PictureFile, ...]]:
    """The front page of the site: one card per application in their order, and the skeleton under them."""
    head = _el(
        "header",
        "front-head",
        [
            *_el("p", "kicker", say_text("FRONT_KICKER")),
            *_el("h1", "big-title", say_text("MASTHEAD_TITLE")),
            *_el("p", "front-claim", say_text("FRONT_CLAIM")),
            *_el("p", "front-lead", say_text("FRONT_LEAD")),
        ],
    )
    cards: list[Segment] = []
    pictures: list[PictureFile] = []
    for app in apps:
        mine = [r for r in records if r.application == app.application]
        card, files = _door(app, mine, choices, table, retakes)
        cards += card
        pictures += files
    doors = _el("section", "doors", cards)
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
    return parts.page("SHELF_TITLE", [*head, *doors, *skeleton]), tuple(pictures)
