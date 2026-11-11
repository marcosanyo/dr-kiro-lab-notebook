"""Tokeniser shared by the derived terms and the scanned text (design 11.2).

Text is split into lowercase tokens at every character that is not a letter or digit, at camelCase
boundaries, and between letters and digits. So `quindle_arm`, `quindleArm`, `quindle-arm` and `Quindle Arm`
all give `quindle`, `arm`, and `gadget_07` and `gadget07` both give `gadget`, `07`.
"""

import bisect
import re
from dataclasses import dataclass

_WORD = re.compile(r"[^\W_]+")
_PART = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+|[^\W\d_A-Za-z]+")


@dataclass(frozen=True)
class Token:
    text: str  # lowercase
    start: int
    end: int


def tokenize(text: str) -> list[Token]:
    tokens = []
    for word in _WORD.finditer(text):
        for part in _PART.finditer(word.group()):
            start = word.start() + part.start()
            tokens.append(Token(part.group().lower(), start, start + len(part.group())))
    return tokens


def term_tokens(name: str) -> tuple[str, ...]:
    return tuple(t.text for t in tokenize(name))


class Lines:
    """Maps character offsets to 1-based line numbers."""

    def __init__(self, text: str) -> None:
        self._starts = [0] + [m.end() for m in re.finditer("\n", text)]

    def line(self, offset: int) -> int:
        return bisect.bisect_right(self._starts, offset)
