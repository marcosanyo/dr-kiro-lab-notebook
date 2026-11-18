"""The reduced record copy: a sealed record without its snapshot entries (design 3.6; Requirement 6).

The copy has the source's layout, `log.jsonl` and `blobs/<sha256>`, with the same file names. Its hash
chain does not verify, because its sequence numbers have gaps; `check_reduced` stands in for that check (6.3).
"""

from dataclasses import dataclass
from pathlib import Path

from bench.record.chain import BLOB_DIR, LOG_NAME, VerifyError, blob_refs, verify

SNAPSHOT = "snapshot"


class ReducedError(Exception):
    """A reduced copy cannot be written, or its source does not verify. The message says why."""


@dataclass(frozen=True)
class Removed:
    seq: int
    hash: str


@dataclass(frozen=True)
class Plan:
    """What the copy holds, derived from a sealed source record."""

    kept: tuple[tuple[int, bytes], ...]  # (seq, line bytes without the newline) of each kept entry, in order
    removed: tuple[Removed, ...]  # each removed snapshot entry, in log order (6.4)
    snapshot_lines: dict[bytes, int]  # line bytes of each removed entry -> its seq
    blobs: dict[str, bytes]  # sha256 -> bytes, for each blob a kept entry references

    def files(self) -> dict[str, bytes]:
        """The copy's files by path relative to the copy folder."""
        log = b"".join(line + b"\n" for _, line in self.kept)
        files = {LOG_NAME: log}
        for digest, data in sorted(self.blobs.items()):
            files[f"{BLOB_DIR}/{digest}"] = data
        return files


def plan(source: Path) -> Plan:
    """Read a sealed source record and decide what the copy keeps (6.1, 6.2). Fail, naming the source, when it
    does not verify."""
    source = Path(source)
    try:
        entries = verify(source, sealed=True)
    except VerifyError as error:
        raise ReducedError(f"{source} is not a sealed record that verifies: {error}") from error
    lines = (source / LOG_NAME).read_bytes().split(b"\n")[:-1]
    kept: list[tuple[int, bytes]] = []
    removed: list[Removed] = []
    snapshot_lines: dict[bytes, int] = {}
    referenced: set[str] = set()
    for line, entry in zip(lines, entries, strict=True):
        if entry["kind"] == SNAPSHOT:
            removed.append(Removed(entry["seq"], entry["hash"]))
            snapshot_lines[line] = entry["seq"]
            continue
        kept.append((entry["seq"], line))
        referenced.update(ref["blob"] for ref in blob_refs(entry["body"]))
    blobs = {digest: (source / BLOB_DIR / digest).read_bytes() for digest in sorted(referenced)}
    return Plan(tuple(kept), tuple(removed), snapshot_lines, blobs)


def reduce(source: Path, target: Path) -> tuple[Removed, ...]:
    """Write the reduced copy of `source` into `target`, which must not exist. Return the removed entries."""
    target = Path(target)
    if target.exists():
        raise ReducedError(f"{target} already exists; a reduced copy is written once")
    made = plan(source)
    (target / BLOB_DIR).mkdir(parents=True)
    for where, data in made.files().items():
        (target / where).write_bytes(data)
    return made.removed


def check_reduced(copy: Path, source: Path) -> list[str]:
    """Compare a reduced copy with its source (Requirement 6.3).

    Return one line per problem, naming the log line or the blob. An empty list means the copy
    matches. Only the first divergent log line is reported, because one removed line shifts every
    line after it."""
    copy = Path(copy)
    made = plan(source)
    problems: list[str] = []
    if not copy.is_dir():
        return [f"{copy}: not a folder"]

    allowed = {LOG_NAME, BLOB_DIR}
    for child in sorted(copy.iterdir()):
        if child.name not in allowed:
            problems.append(f"{child.name}: not part of a reduced copy")

    problems += _check_log(copy / LOG_NAME, made)
    problems += _check_blobs(copy / BLOB_DIR, made)
    return problems


def _check_log(log: Path, made: Plan) -> list[str]:
    if not log.is_file():
        return [f"{LOG_NAME}: missing"]
    data = log.read_bytes()
    if data and not data.endswith(b"\n"):
        return [f"{LOG_NAME}: the last line has no newline"]
    lines = data.split(b"\n")[:-1]
    expected = made.kept
    for index in range(max(len(lines), len(expected))):
        number = index + 1
        if index >= len(expected):
            line = lines[index]
            if line in made.snapshot_lines:
                return [
                    f"{LOG_NAME} line {number}: snapshot entry seq {made.snapshot_lines[line]} is kept; "
                    "the copy must not hold snapshot entries"
                ]
            return [f"{LOG_NAME} line {number}: extra line, not an entry of the source"]
        seq, want = expected[index]
        if index >= len(lines):
            return [f"{LOG_NAME} line {number}: source entry seq {seq} is missing"]
        if lines[index] != want:
            if lines[index] in made.snapshot_lines:
                snapshot = made.snapshot_lines[lines[index]]
                return [
                    f"{LOG_NAME} line {number}: snapshot entry seq {snapshot} is kept; "
                    "the copy must not hold snapshot entries"
                ]
            return [f"{LOG_NAME} line {number}: differs from source entry seq {seq}"]
    return []


def _check_blobs(blob_dir: Path, made: Plan) -> list[str]:
    present: dict[str, bytes] = {}
    problems: list[str] = []
    if blob_dir.exists():
        if not blob_dir.is_dir():
            return [f"{BLOB_DIR}: not a folder"]
        for blob in sorted(blob_dir.iterdir()):
            if not blob.is_file():
                problems.append(f"{BLOB_DIR}/{blob.name}: not a file")
            else:
                present[blob.name] = blob.read_bytes()
    expected = made.blobs
    for name in sorted(set(present) - set(expected)):
        problems.append(f"{BLOB_DIR}/{name}: not referenced by a kept entry")
    for name, data in sorted(expected.items()):
        if name not in present:
            problems.append(f"{BLOB_DIR}/{name}: missing")
        elif present[name] != data:
            problems.append(f"{BLOB_DIR}/{name}: differs from the source blob")
    return problems
