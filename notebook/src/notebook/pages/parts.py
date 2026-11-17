"""Shared page parts: stamp, sticky note, tab, legend link (design 9). Task 7.5.

Every part returns a list of segments. Commentary comes only from `text.py` (`say`); record text keeps the ink
of its recorded author. Ids put in an `href` or `id` attribute are checked against the bench patterns first
(`html.check_id`).
"""

from bench.specfiles.discovered import STATUSES

from notebook import html, text
from notebook.ink import Segment, commentary


def say(name: str) -> Segment:
    """The commentary string `name` of `text.py`, as a segment whose source names it."""
    return commentary(getattr(text, name), text.source(name))


def say_text(name: str) -> list[Segment]:
    """The commentary string `name` in its ink."""
    return html.text(say(name))


def anchor(kind: str, ident: str, source: str, children: list[Segment], prefix: str = "") -> list[Segment]:
    """A link to `#<prefix><id>` on the same page; the id is checked as a bench id of `kind`."""
    return html.element("a", {"href": f"#{prefix}{html.check_id(kind, ident, source)}"}, children)


def row_link(row_id: str, source: str, children: list[Segment]) -> list[Segment]:
    """A link to a row of the table on the same page (`#row-<id>`)."""
    return anchor("row", row_id, source, children, prefix="row-")


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
    return html.element("div", {"class": "sticky sticky-stamp" if stamped else "sticky"}, children)


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


def legend_link(root: str) -> list[Segment]:
    """The footer link to the ink legend; `root` is the relative path from the page to the site root, such
    as `""` or `"../../"` (Requirement 4.5)."""
    if root not in ("", "../", "../../"):
        raise ValueError(f"not a relative path to the site root: {root!r}")
    link = html.element("a", {"href": f"{root}legend.html"}, say_text("LEGEND_LINK"))
    return html.element("footer", {"class": "footer"}, link)
