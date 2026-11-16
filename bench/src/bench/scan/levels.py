"""Who wrote each piece of text, so the scan applies the right level (Requirements 15.4-15.7, design 11.3).

- In a `lab/` folder: the files matched by the lab's `dr_kiro` globs are Dr. Kiro level, all others builder.
- In a session record (a folder with `log.jsonl`): the author recorded on each text field and blob.
- In a copy of a final spec (a folder with `source.json`): Dr. Kiro's three files, checked by hash.
- Anywhere else: a sidecar `<file>.authors.json` listing character ranges by author.
A file with no level source fails the scan.
"""

import hashlib
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bench.scan.terms import ScanError

LEVELS = ("builder", "dr-kiro")
AUTHOR_LEVEL = {"bench": "builder", "dr-kiro": "dr-kiro"}
SIDECAR_SUFFIX = ".authors.json"
_HEX64 = re.compile(r"[0-9a-f]{64}")
_HASH_KEYS = frozenset({"hash", "prev", "blob"})


@dataclass(frozen=True)
class Piece:
    """A piece of text at one level, starting at `line` of `where`. With `one_line`, every match in the piece
    is reported at `line` (a JSON string on one log line); otherwise newlines in the piece count."""

    text: str
    level: str
    where: str
    line: int
    one_line: bool = False

    def line_of(self, offset: int) -> int:
        return self.line if self.one_line else self.line + self.text.count("\n", 0, offset)


def sidecar_pieces(path: Path, text: str) -> list[Piece]:
    sidecar = path.with_name(path.name + SIDECAR_SUFFIX)
    if not sidecar.is_file():
        raise ScanError(f"{path}: no level source (not in a lab folder, not a record, no {SIDECAR_SUFFIX})")
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ScanError(f"{sidecar}: not valid JSON ({error})") from error
    ranges = data.get("ranges") if isinstance(data, dict) else None
    if not isinstance(ranges, list) or not ranges:
        raise ScanError(f"{sidecar}: needs a non-empty list of ranges")
    pieces = []
    position = 0
    for item in ranges:
        if not isinstance(item, dict) or set(item) != {"start", "end", "author"}:
            raise ScanError(f"{sidecar}: each range needs exactly start, end and author")
        start, end, author = item["start"], item["end"], item["author"]
        if author not in AUTHOR_LEVEL:
            raise ScanError(f"{sidecar}: unknown author {author!r}")
        if start != position or not isinstance(end, int) or end <= start:
            raise ScanError(f"{sidecar}: ranges must cover the file in order without gaps")
        pieces.append(Piece(text[start:end], AUTHOR_LEVEL[author], str(path), text.count("\n", 0, start) + 1))
        position = end
    if position != len(text):
        raise ScanError(f"{sidecar}: ranges cover {position} of {len(text)} characters")
    return pieces


def _authored(value: Any) -> bool:
    return isinstance(value, dict) and set(value) == {"author", "text"} and isinstance(value["text"], str)


def entry_strings(value: Any, key: str | None = None) -> Iterator[tuple[str, str]]:
    """Every string in a record entry with its level. Authored fields carry their author; every other key and
    value was written by the bench. Hashes are skipped."""
    if _authored(value):
        author = value["author"]
        if author not in AUTHOR_LEVEL:
            raise ScanError(f"unknown author {author!r} in the record")
        yield value["text"], AUTHOR_LEVEL[author]
    elif isinstance(value, dict):
        if "blob" in value:
            return
        for k, v in value.items():
            yield k, "builder"
            yield from entry_strings(v, k)
    elif isinstance(value, list):
        for v in value:
            yield from entry_strings(v, key)
    elif isinstance(value, str):
        if key in _HASH_KEYS or _HEX64.fullmatch(value):
            return
        yield value, "builder"


TEXT_MEDIA_PREFIXES = ("text/",)
TEXT_MEDIA = frozenset({"application/json"})


def record_pieces(folder: Path) -> list[Piece]:
    """Every piece of text in a session record folder, with the recorded author's level."""
    log = folder / "log.jsonl"
    pieces: list[Piece] = []
    blobs: dict[str, tuple[str, str]] = {}
    for number, line in enumerate(log.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as error:
            raise ScanError(f"{log} line {number}: not JSON ({error})") from error
        for text, level in entry_strings(entry):
            pieces.append(Piece(text, level, str(log), number, one_line=True))
        for ref in _blob_refs(entry):
            author = ref.get("author")
            if author not in AUTHOR_LEVEL:
                raise ScanError(f"{log} line {number}: blob without a known author")
            media = ref.get("media", "")
            previous = blobs.get(ref["blob"])
            if previous is not None and previous[0] != author:
                # The same bytes recorded by two authors: scan at the stricter level.
                author = "bench"
            blobs[ref["blob"]] = (author, media)
    for digest, (author, media) in sorted(blobs.items()):
        path = folder / "blobs" / digest
        if not path.is_file():
            raise ScanError(f"{path}: referenced blob is missing")
        if media.startswith("image/"):
            continue  # pictures are checked for embedded text when they are recorded
        if not (media.startswith(TEXT_MEDIA_PREFIXES) or media in TEXT_MEDIA):
            raise ScanError(f"{path}: cannot scan media type {media!r}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise ScanError(f"{path}: text blob is not UTF-8") from error
        pieces.append(Piece(text, AUTHOR_LEVEL[author], str(path), 1))
    return pieces


COPY_SOURCE = "source.json"
COPY_FILES = ("requirements.md", "design.md", "tasks.md")


def copy_pieces(folder: Path) -> list[Piece]:
    """Every piece of text in a copy of a final spec (a folder with `source.json`, dr-kiro design 7.3).

    The three spec files are Dr. Kiro's text only while their bytes are the ones `source.json` names; the
    scan checks the SHA-256 and fails otherwise. `source.json` is the bench's text. Whether the hashes are the
    record's is checked by `bench-check-discovered`, not here."""
    source = folder / COPY_SOURCE
    try:
        text = source.read_text(encoding="utf-8")
        data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ScanError(f"{source}: not valid JSON ({error})") from error
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict) or set(files) != set(COPY_FILES):
        raise ScanError(f"{source}: files must name exactly {', '.join(COPY_FILES)}")
    names = sorted(p.name for p in folder.iterdir())
    extra = [n for n in names if n not in (*COPY_FILES, COPY_SOURCE)]
    if extra:
        raise ScanError(f"{folder / extra[0]}: not part of a spec copy, so it has no level source")
    # Hashes are skipped, as in a record; every other key and value is the bench's text.
    pieces = [Piece(t, level, str(source), 1, one_line=True) for t, level in entry_strings(data)]
    for name in COPY_FILES:
        path = folder / name
        if not path.is_file():
            raise ScanError(f"{path}: missing from the spec copy")
        data_bytes = path.read_bytes()
        if hashlib.sha256(data_bytes).hexdigest() != files[name]:
            raise ScanError(f"{path}: does not match its SHA-256 in {COPY_SOURCE}, so its author is unknown")
        try:
            content = data_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ScanError(f"{path}: not UTF-8 text; the scan cannot read it") from error
        pieces.append(Piece(content, "dr-kiro", str(path), 1))
    return pieces


def _blob_refs(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if "blob" in value:
            yield value
        else:
            for v in value.values():
                yield from _blob_refs(v)
    elif isinstance(value, list):
        for v in value:
            yield from _blob_refs(v)
