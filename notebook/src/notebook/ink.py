"""Ink, Segment, escaping, and joining segments into text and author ranges (design 8).

Every text of the site is a `Segment`: its unescaped text, its ink and its source (where the text comes from,
for scan findings). The ink follows the recorded author (Requirements 4.1, 4.2). `join` escapes every segment
that is not markup and returns the file text with its author ranges, the body of the `<file>.authors.json`
sidecar (Requirement 20.3).
"""

import html
import re
from dataclasses import dataclass
from enum import Enum

from notebook.errors import NotebookError


class Ink(Enum):
    DRKIRO = "k"
    PENCIL = "p"
    COMMENTARY = "c"
    STAMP = "s"
    MARKUP = "m"


# The sidecar format knows only these two authors; `bench` is scanned at the builder level (design N5).
SCAN_AUTHOR = {
    Ink.DRKIRO: "dr-kiro",
    Ink.PENCIL: "bench",
    Ink.COMMENTARY: "bench",
    Ink.STAMP: "bench",
    Ink.MARKUP: "bench",
}

# Recorded author -> ink of record text (Requirement 4.1).
_AUTHOR_INK = {"dr-kiro": Ink.DRKIRO, "bench": Ink.PENCIL}

# C0 control characters that HTML cannot show as written; tab, line feed and carriage return are allowed (N6).
_FORBIDDEN_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


@dataclass(frozen=True)
class Segment:
    text: str
    ink: Ink
    source: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError(f"segment text must be a str, got {type(self.text).__name__}")
        if not isinstance(self.ink, Ink):
            raise TypeError(f"segment ink must be an Ink, got {self.ink!r}")
        if not self.source:
            raise ValueError("a segment needs a non-empty source")


@dataclass(frozen=True)
class Authored:
    """A text from the record with its recorded author and its place in the record."""

    text: str
    author: str
    source: str

    def segment(self) -> Segment:
        return Segment(self.text, ink_for_author(self.author, self.source), self.source)


def ink_for_author(author: str, source: str) -> Ink:
    """The ink of record text by its recorded author; an unknown author fails, naming the place (4.2)."""
    ink = _AUTHOR_INK.get(author)
    if ink is None:
        raise NotebookError(source, f"text has no known author (recorded author {author!r})")
    return ink


def markup(text: str, source: str = "notebook template") -> Segment:
    return Segment(text, Ink.MARKUP, source)


def commentary(text: str, source: str) -> Segment:
    return Segment(text, Ink.COMMENTARY, source)


def pencil(text: str, source: str) -> Segment:
    return Segment(text, Ink.PENCIL, source)


def stamp(text: str, source: str) -> Segment:
    return Segment(text, Ink.STAMP, source)


def escape(segment: Segment) -> str:
    """The form of a segment in the HTML: markup as written; any other text checked and escaped (N6)."""
    if segment.ink is Ink.MARKUP:
        return segment.text
    bad = _FORBIDDEN_CONTROL.search(segment.text)
    if bad is not None:
        raise NotebookError(
            segment.source,
            f"text holds the control character U+{ord(bad.group()):04X}, which HTML cannot show as written",
        )
    return html.escape(segment.text, quote=True).replace("\r", "&#13;")


def join(segments: list[Segment]) -> tuple[str, list[dict[str, int | str]]]:
    """The file text and its author ranges in code points: contiguous from 0 to the end of the text, adjacent
    ranges of the same author merged (Requirement 20.3)."""
    parts: list[str] = []
    ranges: list[dict[str, int | str]] = []
    position = 0
    for segment in segments:
        piece = escape(segment)
        if not piece:
            continue
        author = SCAN_AUTHOR[segment.ink]
        end = position + len(piece)
        if ranges and ranges[-1]["author"] == author:
            ranges[-1]["end"] = end
        else:
            ranges.append({"start": position, "end": end, "author": author})
        parts.append(piece)
        position = end
    return "".join(parts), ranges
