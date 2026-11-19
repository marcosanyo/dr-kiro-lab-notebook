"""The shelf: the top of every notebook page (notebook-shelf design 3).
Above the opened notebook sit the small heading, the big handwritten title, the description of the
application, the line that says what each ink is, the round tabs that go to each application, and the cover
cards of this application's sessions side by side. The open card has a green frame. The first page of an
application (`index.html`) is the page of the session its settings file names.
"""

from notebook import addresses, html, layouts, progress
from notebook.choices import App, Choices
from notebook.display import Retakes
from notebook.errors import NotebookError
from notebook.ink import Segment, commentary, pencil
from notebook.pages import book, parts, photo
from notebook.pages.parts import say_text
from notebook.readerrequest import Request
from notebook.readerruns import Run
from notebook.records import RecordModel

Page = tuple[list[Segment], tuple[photo.PictureFile, ...]]


def _el(tag: str, cls: str | None, children: list[Segment], **attrs: str) -> list[Segment]:
    return html.element(tag, ({"class": cls} if cls else {}) | attrs, children)


def _page_of(record: RecordModel) -> str:
    return addresses.session(record.application, record.session, f"{record.name}/log.jsonl line 1")


def _masthead(app: App) -> list[Segment]:
    pen = "KEY_NOTES_BLUE" if app.pen == "blue" else "KEY_NOTES_ORANGE"
    legend = [
        *_el("span", "key key-k", say_text("KEY_GREEN")),
        *_el("span", "key key-c", say_text(pen)),
        *_el("span", "key key-p", say_text("KEY_PENCIL")),
    ]
    return _el(
        "header",
        "masthead",
        [
            *_el("p", "kicker", say_text("KICKER")),
            *_el("h1", "big-title", say_text("MASTHEAD_TITLE")),
            *_el("p", "lab-about", html.text(commentary(app.about, app.source))),
            *_el("p", "ink-key", legend),
        ],
    )


def _tabs(current: App, apps: tuple[App, ...]) -> list[Segment]:
    tabs: list[Segment] = []
    for app in apps:
        here = app is current
        href = addresses.COVER if here else addresses.apps_link(app.slug, app.source)
        attrs = {"href": href, "class": "case-tab is-on" if here else "case-tab"}
        if here:
            attrs["aria-current"] = "page"
        tabs += html.element("a", attrs, html.text(commentary(app.case, app.source)))
    return _el("nav", "cases", tabs, **{"aria-label": "labs"})


def _card(record: RecordModel, chosen: Choices, app: App, is_open: bool) -> list[Segment]:
    source = f"{record.name}: cover card"
    small: list[Segment] = []
    if chosen.progress is not None:
        found = progress.series(record, chosen.progress)
        best = progress.best_value_text(found)
        if best is not None:
            small += [
                *say_text("CARD_BEST"),
                *html.text(pencil(f"{found.spec.measurement} {best}", source)),
                *say_text("LIST_SEPARATOR"),
            ]
    counts = progress.predictions(record)
    small += [
        *html.text(pencil(str(counts.hit), source)),
        *say_text("OF"),
        *html.text(pencil(str(counts.total), source)),
        *say_text("CARD_HITS"),
    ]
    attrs = {"href": _page_of(record), "class": f"card card-{chosen.color}" + (" is-open" if is_open else "")}
    if is_open:
        attrs["aria-current"] = "page"
    return html.element(
        "a",
        attrs,
        [
            *_el("span", "card-title", html.text(commentary(chosen.title, f"{chosen.file} key title"))),
            *_el("span", "card-line", html.text(commentary(chosen.line, f"{chosen.file} key line"))),
            *_el("span", "card-small", small),
        ],
    )


def _shelf(
    app: App, current: RecordModel, records: list[RecordModel], choices: dict[tuple[str, str], Choices]
) -> list[Segment]:
    cards = [s for r in records for s in _card(r, choices[(r.application, r.session)], app, r is current)]
    return _el("section", "shelf", cards)


def _page(
    record: RecordModel,
    app: App,
    apps: tuple[App, ...],
    records: list[RecordModel],
    choices: dict[tuple[str, str], Choices],
    table: dict[str, layouts.Layout],
    runs: list[Run],
    requests: dict[str, Request],
    retakes: Retakes,
) -> Page:
    chosen = choices[(record.application, record.session)]
    layout = layouts.layout_for(table, record.application, record.name)
    inside, files = book.body(record, layout, chosen, app, runs, requests, retakes)
    top = [
        *_masthead(app),
        *_tabs(app, apps),
        *_shelf(app, record, records, choices),
        *_el("article", "book", inside, id="book"),
    ]
    return parts.page("SHELF_TITLE", top, app=app), tuple(files)


def pages(
    app: App,
    apps: tuple[App, ...],
    records: list[RecordModel],
    choices: dict[tuple[str, str], Choices],
    table: dict[str, layouts.Layout],
    runs: list[Run],
    requests: dict[str, Request],
    retakes: Retakes,
) -> dict[str, Page]:
    """Every notebook page of one application, with its folder in the path: one per session, and `index.html`,
    the page of the session its settings file names. `records` are the application's own."""
    out: dict[str, Page] = {}
    for record in records:
        path = f"{app.slug}/{_page_of(record)}"
        out[path] = _page(record, app, apps, records, choices, table, runs, requests, retakes)
    opened = next((r for r in records if r.session == app.open), None)
    if opened is None:
        raise NotebookError(app.source, f"names no record ({app.application}/{app.open})")
    out[f"{app.slug}/{addresses.COVER}"] = out[f"{app.slug}/{_page_of(opened)}"]
    return out
