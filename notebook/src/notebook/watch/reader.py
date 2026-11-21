"""The watch reader (Requirement 23.5, design Component 13, N35, N37).

Reads the complete lines of `log.jsonl` in a record folder that the bench is still writing, from the byte
offset after the last accepted line. It checks each line as `bench.record.chain.read_entries` does, one
line at a time, because `verify` needs the whole folder. It takes no lock, never opens `.lock` or
`builder.log`, and writes nothing. The first line that fails a check stops it; nothing is skipped, guessed
or repaired.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bench.record.canonical import CanonicalError, canonical_json
from bench.record.chain import (
    BLOB_DIR,
    GENESIS,
    LOG_NAME,
    VerifyError,
    blob_refs,
    check_blob_ref,
    entry_hash,
    sha256_hex,
)

from notebook import text
from notebook.errors import NotebookError
from notebook.records import _BODY_KEYS

_ENTRY_KEYS = frozenset({"seq", "kind", "body", "prev", "hash"})


@dataclass(frozen=True)
class Stop:
    """Why the reader stopped: the line number (equal to the entry number) and a fixed problem text."""

    line: int
    problem: str

    def __str__(self) -> str:
        return f"line {self.line}: {self.problem}"


class Reader:
    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)
        self.offset = 0
        self.last_seq = 0
        self.last_hash = GENESIS
        self.stop: Stop | None = None
        self._blobs_seen: set[str] = set()

    def poll(self) -> list[dict[str, Any]]:
        """The entries accepted by this pass, in order. After a stop, nothing more is read."""
        if self.stop is not None:
            return []
        log = self.folder / LOG_NAME
        if not log.is_file():
            raise NotebookError(LOG_NAME, "the record has no log file")
        with log.open("rb") as handle:
            handle.seek(self.offset)
            data = handle.read()
        accepted: list[dict[str, Any]] = []
        # shortcut: a line is checked against the file as read now; a piece with no line end waits.
        for line in data.split(b"\n")[:-1]:
            number = self.last_seq + 1
            try:
                entry = self._accept(line)
            except _Refused as refused:
                self.stop = Stop(number, refused.problem)
                break
            accepted.append(entry)
            self.offset += len(line) + 1
            self.last_seq = entry["seq"]
            self.last_hash = entry["hash"]
        return accepted

    def _accept(self, line: bytes) -> dict[str, Any]:
        try:
            entry = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise _Refused(text.WATCH_NOT_JSON) from error
        if not isinstance(entry, dict) or set(entry) != _ENTRY_KEYS:
            raise _Refused(text.WATCH_BAD_FORMAT)
        try:
            canonical = canonical_json(entry)
        except CanonicalError as error:
            raise _Refused(text.WATCH_BAD_FORMAT) from error
        if canonical != line:
            raise _Refused(text.WATCH_BAD_FORMAT)
        kind, body = entry["kind"], entry["body"]
        if not isinstance(kind, str) or kind not in _BODY_KEYS:
            raise _Refused(text.WATCH_BAD_FORMAT)
        if not isinstance(body, dict) or set(body) != _expected_keys(kind, body):
            raise _Refused(text.WATCH_BAD_FORMAT)
        if type(entry["seq"]) is not int or entry["seq"] != self.last_seq + 1:
            raise _Refused(text.WATCH_OUT_OF_SEQUENCE)
        if entry["prev"] != self.last_hash:
            raise _Refused(text.WATCH_PREV_MISMATCH)
        without = {k: v for k, v in entry.items() if k != "hash"}
        if entry["hash"] != entry_hash(without):
            raise _Refused(text.WATCH_HASH_MISMATCH)
        for ref in blob_refs(body):
            try:
                check_blob_ref(ref, LOG_NAME)
            except VerifyError as error:
                raise _Refused(text.WATCH_BAD_FORMAT) from error
            self._check_blob(ref["blob"])
        return entry

    def _check_blob(self, digest: str) -> None:
        if digest in self._blobs_seen:
            return
        path = self.folder / BLOB_DIR / digest
        if not path.is_file():
            raise _Refused(text.WATCH_BLOB_MISSING)
        if sha256_hex(path.read_bytes()) != digest:
            raise _Refused(text.WATCH_BLOB_CHANGED)
        self._blobs_seen.add(digest)


def _expected_keys(kind: str, body: dict[str, Any]) -> frozenset[str]:
    """The key set `records.py` requires for this kind, with its optional keys: `discovered_table` and
    `variant` of a start entry, no `experiment` in an `end` snapshot."""
    keys = _BODY_KEYS[kind]
    if kind == "start":
        return keys | (body.keys() & {"discovered_table", "variant"})
    if kind == "snapshot" and body.get("for") == "end":
        return keys - {"experiment"}
    return keys


class _Refused(Exception):
    def __init__(self, problem: str) -> None:
        super().__init__(problem)
        self.problem = problem
