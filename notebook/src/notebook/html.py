"""Element helpers over segments, as plain string templates (design 8).

Pages are lists of segments. Tags and attributes are markup segments written here; text goes in element
content only. Dr. Kiro's text is never put in an attribute (Requirement 4.3). Ids put in addresses and
attributes are checked against the bench's id patterns first (design 8, N9).
"""

import html
import re

from bench.core import ids
from bench.specfiles import discovered

from notebook.errors import NotebookError
from notebook.ink import Ink, Segment, markup

_NAME = re.compile(r"[a-z][a-z0-9-]*")

# The bench's patterns for each kind of id (`bench.core.ids` and the row pattern of `discovered.py`).
_ID_CHECKS = {
    "experiment": lambda text: _parses(ids.parse_experiment_id, text),
    "trial": lambda text: _parses(ids.parse_trial_id, text),
    "hypothesis": ids.is_hypothesis_id,
    "prediction": lambda text: _parses(ids.parse_prediction_id, text),
    "row": lambda text: discovered._ROW_ID.fullmatch(text) is not None,
}


def _parses(parse, text: str) -> bool:
    try:
        parse(text)
    except ValueError:
        return False
    return True


def check_id(kind: str, text: str, source: str) -> str:
    """`text` if it is a bench id of `kind`; otherwise the build fails, naming the source."""
    check = _ID_CHECKS.get(kind)
    if check is None:
        raise ValueError(f"unknown id kind {kind!r}")
    if not isinstance(text, str) or not check(text):
        raise NotebookError(source, f"{text!r} is not a valid {kind} id, so it cannot be used in an address")
    return text


def _attributes(attrs: dict[str, str]) -> str:
    out = []
    for name, value in attrs.items():
        if not _NAME.fullmatch(name):
            raise ValueError(f"not a valid attribute name: {name!r}")
        if not isinstance(value, str):
            raise TypeError(f"attribute {name} must be a str, got {type(value).__name__}")
        out.append(f' {name}="{html.escape(value, quote=True)}"')
    return "".join(out)


def element(tag: str, attrs: dict[str, str] | None, children: list[Segment]) -> list[Segment]:
    """`<tag attrs>children</tag>` as segments. Attribute values are template strings or checked ids."""
    if not _NAME.fullmatch(tag):
        raise ValueError(f"not a valid tag name: {tag!r}")
    return [markup(f"<{tag}{_attributes(attrs or {})}>"), *children, markup(f"</{tag}>")]


def void(tag: str, attrs: dict[str, str] | None = None) -> list[Segment]:
    """An element without content, such as `<img>`."""
    if not _NAME.fullmatch(tag):
        raise ValueError(f"not a valid tag name: {tag!r}")
    return [markup(f"<{tag}{_attributes(attrs or {})}>")]


def text(segment: Segment, block: bool = False) -> list[Segment]:
    """A text segment in its ink: `<span class="ink-<k>">` inline, `<div class="ink-<k> block-<k>">` for a
    block (`.block-k` in the visual steering). `.ink-k` keeps line breaks (`white-space: pre-wrap`), so Dr.
    Kiro's text shows as written. A `<pre>` is not used: HTML drops a line feed right after `<pre>`, which
    would change the text."""
    if segment.ink is Ink.MARKUP:
        raise ValueError("markup is not text")
    if block:
        k = segment.ink.value
        return element("div", {"class": f"ink-{k} block-{k}"}, [segment])
    return element("span", {"class": f"ink-{segment.ink.value}"}, [segment])
