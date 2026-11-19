"""The shelf: the top of every notebook page (notebook-shelf design 3).
Above the opened notebook sit the small heading, the big handwritten title, the description of the lab that
is open, the line that says what each ink is, the two round tabs that switch the lab, and the cover cards of
that lab's sessions side by side. The open card has a green frame. The first page (`index.html`) is the page
of the session the cover file names for the first lab.
"""

from notebook import addresses, html, layouts, progress
from notebook.choices import Choices, Cover, Lab
from notebook.errors import NotebookError
from notebook.ink import Segment, commentary, markup, pencil
from notebook.pages import book, parts, photo
from notebook.pages.parts import link, say_text
from notebook.readerrequest import Request
from notebook.readerruns import Run
from notebook.records import RecordModel

Page = tuple[list[Segment], tuple[photo.PictureFile, ...]]


def _el(tag: str, cls: str | None, children: list[Segment], **attrs: str) -> list[Segment]:
    return html.element(tag, ({"class": cls} if cls else {}) | attrs, children)


def _page_of(record: RecordModel) -> str:
    return addresses.session(record.application, record.session, f"{record.name}/log.jsonl line 1")


def _masthead(lab: Lab) -> list[Segment]:
    legend = [
        *_el("span", "key key-k", say_text("KEY_GREEN")),
        *_el("span", "key key-c", say_text("KEY_ORANGE")),
        *_el("span", "key key-p", say_text("KEY_PENCIL")),
    ]
    return _el(
        "header",
        "masthead",
        [
            *_el("p", "kicker", say_text("KICKER")),
            *_el("h1", "big-title", say_text("MASTHEAD_TITLE")),
            *_el("p", "lab-about", html.text(commentary(lab.about, lab.source))),
            *_el("p", "ink-key", legend),
        ],
    )


def _tabs(cover: Cover, current: Lab, by_key: dict[tuple[str, str], RecordModel]) -> list[Segment]:
    tabs: list[Segment] = []
    for lab in cover.labs:
        target = _page_of(by_key[(lab.application, lab.open)])
        attrs = {"href": target, "class": "case-tab is-on" if lab is current else "case-tab"}
        if lab is current:
            attrs["aria-current"] = "page"
        tabs += html.element("a", attrs, html.text(commentary(lab.case, lab.source)))
    return _el("nav", "cases", tabs, **{"aria-label": "labs"})


def _card(record: RecordModel, chosen: Choices, lab: Lab, is_open: bool) -> list[Segment]:
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
        *html.text(pencil(f"{counts.hit}/{counts.total}", source)),
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
    lab: Lab, current: RecordModel, records: list[RecordModel], choices: dict[tuple[str, str], Choices]
) -> list[Segment]:
    cards = [
        s
        for r in records
        if r.application == lab.application
        for s in _card(r, choices[(r.application, r.session)], lab, r is current)
    ]
    return _el("section", "shelf", cards)


def _page(
    record: RecordModel,
    records: list[RecordModel],
    choices: dict[tuple[str, str], Choices],
    cover: Cover,
    table: dict[str, layouts.Layout],
    runs: list[Run],
    requests: dict[str, Request],
) -> Page:
    by_key = {(r.application, r.session): r for r in records}
    lab = next(lab for lab in cover.labs if lab.application == record.application)
    chosen = choices[(record.application, record.session)]
    layout = layouts.layout_for(table, record.application, record.name)
    inside, files = book.body(record, layout, chosen, lab, runs, requests)
    opened = _el("article", "book", inside, id="book")
    top = [
        *_masthead(lab),
        *_tabs(cover, lab, by_key),
        *_shelf(lab, record, records, choices),
        *opened,
    ]
    return parts.page("SHELF_TITLE", top), tuple(files)


def pages(
    records: list[RecordModel],
    choices: dict[tuple[str, str], Choices],
    cover: Cover,
    table: dict[str, layouts.Layout],
    runs: list[Run],
    requests: dict[str, Request],
) -> dict[str, Page]:
    """Every notebook page: one per session, and `index.html`, the page of the first lab's open session."""
    out: dict[str, Page] = {}
    for record in records:
        out[_page_of(record)] = _page(record, records, choices, cover, table, runs, requests)
    first = cover.labs[0]
    opened = next(r for r in records if (r.application, r.session) == (first.application, first.open))
    if addresses.COVER in out:
        raise NotebookError(addresses.COVER, "a session page cannot be named index.html")
    out[addresses.COVER] = out[_page_of(opened)]
    return out


__all__ = ["pages", "link", "markup"]
