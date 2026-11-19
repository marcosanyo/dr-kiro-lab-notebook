"""The ink legend, `legend.html` (Requirements 4.5, 15.2): the inks and the four status words, defined in
commentary ink, never in the stamp style. Every page's footer links it (`parts.page`).
"""

from bench.specfiles.discovered import STATUSES

from notebook import addresses, html, text
from notebook.errors import NotebookError
from notebook.ink import Segment
from notebook.pages import parts
from notebook.pages.parts import link, say_text

# The ink legend

_INKS = (
    ("INK_DRKIRO_NAME", "INK_DRKIRO_ABOUT", "k"),
    ("INK_PENCIL_NAME", "INK_PENCIL_ABOUT", "p"),
    ("INK_COMMENTARY_NAME", "INK_COMMENTARY_ABOUT", "c"),
    # The miss red has no swatch: it is used only on missed predictions (Requirement 6.4).
    ("MISS_RED_NAME", "MISS_RED_ABOUT", None),
)

_STATUS_WORDS = (
    ("STATUS_VALIDATED_WORD", "STATUS_VALIDATED"),
    ("STATUS_PARTLY_WORD", "STATUS_PARTLY"),
    ("STATUS_OBSERVED_WORD", "STATUS_OBSERVED"),
    ("STATUS_REJECTED_WORD", "STATUS_REJECTED"),
)


def legend() -> list[Segment]:
    """`legend.html`: the three inks and the miss red, each with a colour swatch that holds no text, and the
    four status words, defined in commentary ink (Requirements 4.5, 15.2)."""
    words = {getattr(text, word) for word, _ in _STATUS_WORDS}
    if words != set(STATUSES):
        raise NotebookError(
            text.SOURCE_FILE, f"the legend's status words {sorted(words)} are not the bench's"
        )
    inks: list[Segment] = []
    for name, about, swatch in _INKS:
        mark: list[Segment] = []
        if swatch is not None:
            mark = html.element("span", {"class": f"swatch swatch-{swatch}", "aria-hidden": "true"}, [])
        inks += html.element("dt", None, [*mark, *say_text(name)])
        inks += html.element("dd", None, say_text(about))
    statuses: list[Segment] = []
    for word, about in _STATUS_WORDS:
        statuses += html.element("dt", None, say_text(word))
        statuses += html.element("dd", None, say_text(about))
    body = [
        *html.element("p", None, link(addresses.COVER, say_text("BACK_TO_COVER"))),
        *html.element("h1", None, say_text("LEGEND_TITLE")),
        *html.element("p", None, say_text("LEGEND_INTRO")),
        *html.element("h2", None, say_text("LEGEND_INKS")),
        *html.element("dl", {"class": "legend"}, inks),
        *html.element("h2", None, say_text("LEGEND_STATUS")),
        *html.element("p", None, say_text("LEGEND_STATUS_INTRO")),
        *html.element("dl", {"class": "legend"}, statuses),
    ]
    return parts.page("LEGEND_TITLE", body)
