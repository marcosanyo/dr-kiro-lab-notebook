"""The commentary word list check (Requirement 5.5, design "Data Models", N17). Task 6.4.

The list file holds one lowercase word per line; `#` starts a comment that runs to the end of the line; blank
lines are ignored. A commentary string fails when one of its word tokens (runs of letters, lowercased) equals
a listed word, or equals a listed word followed by one of the suffixes `s`, `es`, `ed` or `ing`. A token that
only contains a listed word as a part (for example inside a longer word) does not match.

Only the builder's commentary is checked. Dr. Kiro's text is shown as written (Requirement 4.3).
"""

import re
from dataclasses import dataclass
from pathlib import Path

from notebook.errors import NotebookError

SUFFIXES = ("", "s", "es", "ed", "ing")

_WORD = re.compile(r"[a-z]+")
# A run of letters in any script: word characters without digits and the underscore.
_TOKEN = re.compile(r"[^\W\d_]+")


@dataclass(frozen=True)
class WordList:
    """The listed words, and every form the check refuses mapped to the listed word it comes from."""

    source: str
    words: tuple[str, ...]
    forms: dict[str, str]

    def matches(self, text: str) -> list[tuple[str, str]]:
        """Every token of `text` that the list refuses, as (token, listed word), in text order."""
        found: list[tuple[str, str]] = []
        for match in _TOKEN.finditer(text):
            token = match.group(0).lower()
            word = self.forms.get(token)
            if word is not None:
                found.append((token, word))
        return found

    def check(self, text: str, where: str) -> None:
        """Fail, naming `where` and every refused token, when `text` holds a listed word."""
        found = self.matches(text)
        if found:
            listed = ", ".join(f'"{token}" (listed word "{word}")' for token, word in found)
            raise NotebookError(where, f"commentary uses a word from {self.source}: {listed}")


def parse(text: str, source: str) -> WordList:
    """Read the list file's text. `source` names the file in errors."""
    words: list[str] = []
    seen: dict[str, int] = {}
    for number, raw in enumerate(text.split("\n"), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if _WORD.fullmatch(line) is None:
            raise NotebookError(
                f"{source} line {number}",
                f"{line!r} is not one lowercase word of the letters a-z",
            )
        if line in seen:
            raise NotebookError(f"{source} line {number}", f'"{line}" is already listed on line {seen[line]}')
        seen[line] = number
        words.append(line)
    if not words:
        raise NotebookError(source, "the word list holds no word")
    forms: dict[str, str] = {}
    for word in words:
        for suffix in SUFFIXES:
            # A form reached from two listed words (for example "limps" from "limp" + "s" and from a listed
            # "limps") keeps the first listed word, in file order; either way the form is refused.
            forms.setdefault(word + suffix, word)
    return WordList(source=source, words=tuple(words), forms=forms)


def load(path: Path) -> WordList:
    """Read the list file at `path`."""
    if not path.is_file():
        raise NotebookError(str(path), "the commentary word list does not exist")
    return parse(path.read_text(encoding="utf-8"), str(path))
