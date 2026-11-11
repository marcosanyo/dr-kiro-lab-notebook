"""SHA-256 hash chain over the session record, verification, and the `bench-verify` command
(Requirements 13.3, 13.4, design 9.1).

Entry: {"seq": n, "kind": ..., "body": {...}, "prev": <hash>, "hash": <hash>}.
hash = SHA-256(prev + canonical JSON of the entry without "hash"). The first prev is 64 zeros.
Blobs are referenced inside entry bodies as {"blob": <sha256>, "author": ..., "media": ...}, so the chain
covers every file.
"""

import hashlib
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from bench.record.canonical import CanonicalError, canonical_json

GENESIS = "0" * 64
LOG_NAME = "log.jsonl"
BLOB_DIR = "blobs"
# Files that exist only in the bench state folder, never in a sealed record.
STATE_ONLY_FILES = frozenset({"builder.log", ".lock"})

ENTRY_KINDS = frozenset(
    {
        "start",
        "register",
        "refusal",
        "experiment",
        "trial",
        "outcome",
        "verdict",
        "flag",
        "snapshot",
        "failure",
        "seal",
    }
)
AUTHORS = frozenset({"bench", "dr-kiro"})
_HEX64 = re.compile(r"[0-9a-f]{64}")


class VerifyError(ValueError):
    """The record does not verify. `where` names the first entry or file that does not match."""

    def __init__(self, where: str, problem: str) -> None:
        super().__init__(f"{where}: {problem}")
        self.where = where
        self.problem = problem


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def entry_hash(entry_without_hash: dict[str, Any]) -> str:
    prev = entry_without_hash["prev"]
    return sha256_hex(prev.encode("ascii") + canonical_json(entry_without_hash))


def blob_refs(value: Any) -> Iterator[dict[str, Any]]:
    """Every blob reference inside an entry body."""
    if isinstance(value, dict):
        if "blob" in value:
            yield value
        else:
            for v in value.values():
                yield from blob_refs(v)
    elif isinstance(value, list):
        for v in value:
            yield from blob_refs(v)


def check_blob_ref(ref: dict[str, Any], where: str) -> None:
    if set(ref) != {"blob", "author", "media"}:
        raise VerifyError(where, f"blob reference has keys {sorted(ref)}")
    if not isinstance(ref["blob"], str) or not _HEX64.fullmatch(ref["blob"]):
        raise VerifyError(where, "blob reference is not a SHA-256 hex digest")
    if ref["author"] not in AUTHORS:
        raise VerifyError(where, f"blob reference has unknown author {ref['author']!r}")
    if not isinstance(ref["media"], str) or not ref["media"]:
        raise VerifyError(where, "blob reference has no media type")


def read_entries(folder: Path) -> list[dict[str, Any]]:
    """Read and verify the chain of `log.jsonl`. Raise VerifyError at the first line that does not match."""
    log = folder / LOG_NAME
    if not log.is_file():
        raise VerifyError(LOG_NAME, "missing")
    data = log.read_bytes()
    if data and not data.endswith(b"\n"):
        lines = data.split(b"\n")
        raise VerifyError(f"{LOG_NAME} line {len(lines)}", "does not end with a newline")
    entries: list[dict[str, Any]] = []
    prev = GENESIS
    for number, line in enumerate(data.split(b"\n")[:-1], start=1):
        where = f"{LOG_NAME} line {number}"
        try:
            entry = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise VerifyError(where, f"not JSON ({error})") from error
        if not isinstance(entry, dict) or set(entry) != {"seq", "kind", "body", "prev", "hash"}:
            raise VerifyError(where, "entry does not have exactly seq, kind, body, prev, hash")
        try:
            canonical = canonical_json(entry)
        except CanonicalError as error:
            raise VerifyError(where, str(error)) from error
        if canonical != line:
            raise VerifyError(where, "entry is not in canonical form")
        if entry["seq"] != number:
            raise VerifyError(where, f"seq is {entry['seq']!r}, expected {number}")
        if entry["kind"] not in ENTRY_KINDS:
            raise VerifyError(where, f"unknown entry kind {entry['kind']!r}")
        if not isinstance(entry["body"], dict):
            raise VerifyError(where, "body is not an object")
        if entry["prev"] != prev:
            raise VerifyError(where, "prev does not match the hash of the entry before")
        without = {k: v for k, v in entry.items() if k != "hash"}
        if entry["hash"] != entry_hash(without):
            raise VerifyError(where, "hash does not match the entry")
        for ref in blob_refs(entry["body"]):
            check_blob_ref(ref, where)
        entries.append(entry)
        prev = entry["hash"]
    return entries


def verify(folder: Path, *, sealed: bool) -> list[dict[str, Any]]:
    """Verify a session folder. With `sealed`, it must be a sealed record: only the log and blobs, ending
    with exactly one seal entry. Return the entries. Raise VerifyError naming the first mismatch."""
    folder = Path(folder)
    if not folder.is_dir():
        raise VerifyError(str(folder), "not a folder")
    allowed_top = {LOG_NAME, BLOB_DIR} | (set() if sealed else set(STATE_ONLY_FILES))
    for child in sorted(folder.iterdir()):
        if child.name not in allowed_top:
            raise VerifyError(child.name, "unexpected file in the session folder")
    entries = read_entries(folder)
    seals = [e["seq"] for e in entries if e["kind"] == "seal"]
    if sealed:
        if not entries or entries[-1]["kind"] != "seal":
            raise VerifyError(LOG_NAME, "record is not sealed: the last entry is not a seal")
        if len(seals) != 1:
            raise VerifyError(LOG_NAME, f"record has {len(seals)} seal entries")
    elif seals and seals != [entries[-1]["seq"]]:
        raise VerifyError(LOG_NAME, "entries follow the seal")
    referenced = {ref["blob"] for e in entries for ref in blob_refs(e["body"])}
    blob_dir = folder / BLOB_DIR
    present: set[str] = set()
    if blob_dir.exists():
        if not blob_dir.is_dir():
            raise VerifyError(BLOB_DIR, "not a folder")
        for blob in sorted(blob_dir.iterdir()):
            where = f"{BLOB_DIR}/{blob.name}"
            if not blob.is_file():
                raise VerifyError(where, "not a file")
            if blob.name not in referenced:
                raise VerifyError(where, "not referenced by any entry")
            if sha256_hex(blob.read_bytes()) != blob.name:
                raise VerifyError(where, "content does not match its hash")
            present.add(blob.name)
    for missing in sorted(referenced - present):
        raise VerifyError(f"{BLOB_DIR}/{missing}", "referenced but missing")
    return entries


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: bench-verify <sealed session folder>", file=sys.stderr)
        return 2
    folder = Path(args[0])
    try:
        entries = verify(folder, sealed=True)
    except VerifyError as error:
        print(f"{folder}: {error}", file=sys.stderr)
        return 1
    blobs = {ref["blob"] for e in entries for ref in blob_refs(e["body"])}
    print(f"{folder}: verified, {len(entries)} entries, {len(blobs)} blobs")
    return 0
