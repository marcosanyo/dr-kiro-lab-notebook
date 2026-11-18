"""Relied-on line (design 3.7, Requirement 10).

The reader's H1 names, as the first line of its prediction block, what it relies on before it runs anything:
`# relies on: none`, or `# relies on: ` and distinct ids. The line is a TOML comment, so the bench keeps it in
the frozen part and ignores it when it reads predictions.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bench.record.chain import BLOB_DIR, VerifyError, verify

PREFIX = "# relies on: "
PROBLEMS = ("no-h1", "no-line", "bad-syntax", "unknown-id", "late")

# The three files of the final spec that the reader is given under setup `spec`.
GIVEN_SPEC_FILES = ("requirements", "design", "tasks")
# The ids the reader is told it may name: rule rows, hypotheses and experiments (reader.md).
_SPEC_ID = re.compile(r"\b(?:R|H|E)[1-9][0-9]*\b")

_LINE_START = "# relies on"
_FENCES = ("```", "~~~")
_ID = r"[^,\s]+"
_IDS = re.compile(rf"{_ID}(?:, *{_ID})*")


class ReliedError(Exception):
    """The relied-on line cannot be checked: the source record or the setup cannot be read."""


@dataclass(frozen=True)
class Relied:
    ids: tuple[str, ...] | None  # as found; None when there is no line or it cannot be read
    problem: str | None  # None: the line is valid


def relied_line(frozen: str) -> str | None:
    """The line right after the first code fence after H1's heading, if it starts with `# relies on`."""
    lines = frozen.split("\n")
    fence = next((n for n in range(1, len(lines)) if lines[n].strip().startswith(_FENCES)), None)
    if fence is None or fence + 1 >= len(lines):
        return None
    candidate = lines[fence + 1]
    return candidate if candidate.startswith(_LINE_START) else None


def parse_ids(line: str) -> tuple[str, ...] | None:
    """The ids of a relied-on line, or None when the line breaks the syntax (Requirement 10.1)."""
    if not line.startswith(PREFIX):
        return None
    rest = line[len(PREFIX) :]
    if not _IDS.fullmatch(rest):
        return None
    ids = tuple(re.split(r", *", rest))
    if "none" in ids and len(ids) > 1:
        return None
    if len(set(ids)) != len(ids):
        return None
    return ids


def format_ids(ids: tuple[str, ...]) -> str:
    return PREFIX + ", ".join(ids)


def allowed_ids(setup: str, source: Path) -> frozenset[str]:
    """The ids the line may name, taken from the sealed source record only (Requirement 10.2, 10.5)."""
    if setup == "none":
        return frozenset({"none"})
    if setup not in ("spec", "record"):
        raise ReliedError(f"unknown setup {setup!r}; the setups are spec, none and record")
    try:
        entries = verify(source, sealed=True)
    except VerifyError as error:
        raise ReliedError(f"{source}: the source record does not verify: {error}") from error
    if setup == "record":
        ids = {"none"}
        for entry in entries:
            if entry["kind"] == "register":
                ids.add(entry["body"]["hypothesis"])
            elif entry["kind"] == "experiment":
                ids.add(entry["body"]["experiment"])
        return frozenset(ids)
    ended = [e for e in entries if e["kind"] == "snapshot" and e["body"].get("for") == "end"]
    if len(ended) != 1:
        raise ReliedError(f"{source}: the source has no end snapshot, so it has no final spec")
    files = ended[0]["body"]["files"]
    ids = {"none"}
    for name in GIVEN_SPEC_FILES:
        if name not in files:
            raise ReliedError(f"{source}: the end snapshot has no {name}.md of the final spec")
        text = (source / BLOB_DIR / files[name]["blob"]).read_text(encoding="utf-8")
        ids.update(_SPEC_ID.findall(text))
    return frozenset(ids)


def relied_on(entries: list[dict[str, Any]], frozen_h1: str | None, allowed: frozenset[str]) -> Relied:
    """Check the relied-on line of H1. The first problem found in PROBLEMS order decides; every problem makes
    the result `not-counted` (Requirement 15.2)."""
    registered = [e for e in entries if e["kind"] == "register" and e["body"]["hypothesis"] == "H1"]
    if not registered:
        return Relied(None, "no-h1")
    if frozen_h1 is None:
        raise ReliedError("H1 is registered but its frozen part was not given")
    line = relied_line(frozen_h1)
    if line is None:
        return Relied(None, "no-line")
    ids = parse_ids(line)
    if ids is None:
        return Relied(None, "bad-syntax")
    if any(identifier not in allowed for identifier in ids):
        return Relied(ids, "unknown-id")
    h1_seq = registered[0]["seq"]
    if any(e["kind"] == "experiment" and e["seq"] < h1_seq for e in entries):
        return Relied(ids, "late")
    return Relied(ids, None)
