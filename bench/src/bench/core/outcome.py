"""The three outcomes of a bench action, and messages made of authored spans (Requirements 1.1, 15.8).

Every span records who wrote it, so the blind scan can apply the right level: the bench's own wording is
scanned at the builder level, and text quoted from Dr. Kiro's files at the Dr. Kiro level.
"""

from dataclasses import dataclass
from typing import Any, Literal

Author = Literal["bench", "dr-kiro"]


@dataclass(frozen=True)
class BenchText:
    """Text written by the bench."""

    text: str

    @property
    def author(self) -> Author:
        return "bench"


@dataclass(frozen=True)
class Quote:
    """Text copied from one of Dr. Kiro's files, with the file (as named inside the lab) and line."""

    text: str
    file: str
    line: int

    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError(f"quote line must be 1 or more, got {self.line}")
        if not self.file:
            raise ValueError("quote file must not be empty")

    @property
    def author(self) -> Author:
        return "dr-kiro"


Span = BenchText | Quote


@dataclass(frozen=True)
class Message:
    """A message as a sequence of authored spans. The front end renders spans and adds no text."""

    spans: tuple[Span, ...]

    def __post_init__(self) -> None:
        if not self.spans:
            raise ValueError("a message needs at least one span")
        for span in self.spans:
            if not isinstance(span, BenchText | Quote):
                raise TypeError(f"message span must be BenchText or Quote, got {type(span).__name__}")

    def plain(self) -> str:
        """The message as one string, for logs and tests."""
        return "".join(span.text for span in self.spans)


def message(*parts: str | Span) -> Message:
    """Build a message. Plain strings are the bench's own wording."""
    return Message(tuple(BenchText(p) if isinstance(p, str) else p for p in parts))


class RefusalError(Exception):
    """Raised inside the bench when a lab rule refuses an action. The session turns it into `Refused`."""

    def __init__(self, message: Message) -> None:
        super().__init__(message.plain())
        self.message = message


@dataclass(frozen=True)
class Ran:
    """The action ran. `result` is what the action returns."""

    result: Any


@dataclass(frozen=True)
class Refused:
    """The action was refused by a lab rule. Dr. Kiro can fix it."""

    message: Message


@dataclass(frozen=True)
class BenchFailure:
    """The bench or the adapter failed. The session stops."""

    message: Message


Outcome = Ran | Refused | BenchFailure
