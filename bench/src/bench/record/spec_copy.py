"""Dr. Kiro's final spec files, taken from a sealed record, and readable copies of them in the repository
(dr-kiro Requirement 8, design 7.3; lab-bench Requirement 15.10).

The final spec of a session is the three files of its `"for": "end"` snapshot: what the bench checked when
Dr. Kiro ended the session. Only a record sealed as `ended` has one. `final_spec` reads it from a verified
record; it is the one source for the copies in `discovered/` and for the reader of `build-from-spec`.

A copy is the folder `<discovered>/<application>/<session>/` with the three files, byte for byte, and
`source.json`, which names the record entries they come from and the SHA-256 of each file. The copy is for
people to read. The record stays the source: `check_copies` compares every copy with its record.

Commands:
    bench-export-spec <sealed session folder> <discovered folder>
    bench-check-discovered <sessions folder> <discovered folder>
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from bench.record.chain import BLOB_DIR, LOG_NAME, VerifyError, sha256_hex, verify

SPEC_KEYS = ("requirements", "design", "tasks")
SOURCE_NAME = "source.json"
COPY_FILES = tuple(f"{key}.md" for key in SPEC_KEYS)
# Files of the discovered folder itself, written by the builder (the README and its author sidecar).
DISCOVERED_FILES = frozenset({"README.md", "README.md.authors.json"})


class SpecCopyError(Exception):
    """The final spec cannot be read or a copy cannot be written. The message says why."""


@dataclass(frozen=True)
class FinalSpec:
    application: str
    session: str
    snapshot_seq: int
    snapshot_hash: str
    seal_hash: str
    files: dict[str, bytes]  # "requirements.md", "design.md", "tasks.md" -> bytes as recorded

    def source(self) -> bytes:
        """The bytes of `source.json` for this final spec."""
        data = {
            "application": self.application,
            "session": self.session,
            "snapshot": {"seq": self.snapshot_seq, "hash": self.snapshot_hash},
            "seal": self.seal_hash,
            "files": {name: sha256_hex(data) for name, data in self.files.items()},
        }
        return (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")


@dataclass(frozen=True)
class RecordEnd:
    """How a sealed record ended, and its final spec if it has one."""

    application: str
    session: str
    end: str  # "ended" | "stopped"
    final: FinalSpec | None


def read_end(record: Path) -> RecordEnd:
    """Verify a sealed record and read how it ended. A record sealed as `ended` before the bench recorded an
    end snapshot has `final` None."""
    record = Path(record)
    try:
        entries = verify(record, sealed=True)
    except VerifyError as error:
        raise SpecCopyError(f"{record}: the record does not verify ({error})") from error
    start, seal = entries[0], entries[-1]
    if start["kind"] != "start":
        raise SpecCopyError(f"{record}: the first entry is not the start of a session")
    application, session = start["body"]["application"], start["body"]["session"]
    if record.name != session:
        raise SpecCopyError(f"{record}: the folder name is not the session id {session!r}")
    end = seal["body"]["end"]
    snapshots = [e for e in entries if e["kind"] == "snapshot" and e["body"].get("for") == "end"]
    if end != "ended":
        if snapshots:
            raise SpecCopyError(f"{record}: a session sealed as {end!r} has an end snapshot")
        return RecordEnd(application, session, end, None)
    if not snapshots:
        return RecordEnd(application, session, end, None)
    if len(snapshots) != 1:
        raise SpecCopyError(f"{record}: the record has {len(snapshots)} end snapshots")
    (snapshot,) = snapshots
    refs = snapshot["body"]["files"]
    if set(refs) != set(SPEC_KEYS):
        raise SpecCopyError(f"{record}: the end snapshot holds {sorted(refs)}, not the three spec files")
    files = {}
    for key in SPEC_KEYS:
        ref = refs[key]
        if ref["author"] != "dr-kiro":
            raise SpecCopyError(f"{record}: the end snapshot's {key} file is not written by Dr. Kiro")
        files[f"{key}.md"] = (record / BLOB_DIR / ref["blob"]).read_bytes()
    final = FinalSpec(application, session, snapshot["seq"], snapshot["hash"], seal["hash"], files)
    return RecordEnd(application, session, end, final)


def final_spec(record: Path) -> FinalSpec:
    """The three spec files of a session sealed as `ended`, from its end snapshot. Fail, saying why, for any
    other record."""
    ended = read_end(record)
    if ended.end != "ended":
        raise SpecCopyError(f"session {ended.session} was {ended.end}, not ended; it has no final spec")
    if ended.final is None:
        raise SpecCopyError(
            f"session {ended.session} has no end snapshot (it was sealed before the bench recorded one); "
            "it has no final spec"
        )
    return ended.final


def copy_folder(discovered: Path, application: str, session: str) -> Path:
    return Path(discovered) / application / session


def write_copy(record: Path, discovered: Path) -> Path:
    """Write the copy of a record's final spec. Fail if the copy folder exists: a copy is made once, and made
    again by deleting it first."""
    final = final_spec(record)
    if not Path(discovered).is_dir():
        raise SpecCopyError(f"the discovered folder {discovered} does not exist")
    folder = copy_folder(discovered, final.application, final.session)
    if folder.exists():
        raise SpecCopyError(f"{folder} already exists; delete it to write the copy again")
    folder.mkdir(parents=True)
    for name, data in final.files.items():
        (folder / name).write_bytes(data)
    (folder / SOURCE_NAME).write_bytes(final.source())
    return folder


def _records(sessions: Path) -> list[Path]:
    """Every session record folder under `<sessions>/<application>/`."""
    found = []
    for application in sorted(p for p in Path(sessions).iterdir() if p.is_dir()):
        for folder in sorted(p for p in application.iterdir() if p.is_dir()):
            if not (folder / LOG_NAME).is_file():
                raise SpecCopyError(f"{folder}: not a session record (no {LOG_NAME})")
            found.append(folder)
    return found


def _compare(folder: Path, final: FinalSpec) -> list[str]:
    expected = dict(final.files)
    expected[SOURCE_NAME] = final.source()
    problems = []
    present = sorted(p.name for p in folder.iterdir())
    for name in present:
        if name not in expected:
            problems.append(f"{folder / name}: not part of the copy")
    for name, data in expected.items():
        path = folder / name
        if not path.is_file():
            problems.append(f"{path}: missing")
        elif path.read_bytes() != data:
            problems.append(f"{path}: differs from the record")
    return problems


def check_copies(sessions: Path, discovered: Path) -> tuple[list[str], list[str]]:
    """Compare the discovered folder with the sealed records. Return (report lines, problems).

    Every session sealed as `ended` with an end snapshot has a copy equal to its record. A session sealed as
    `stopped`, or as `ended` without an end snapshot, has no copy. Nothing else is in the discovered folder.
    """
    sessions, discovered = Path(sessions), Path(discovered)
    for name, folder in (("sessions", sessions), ("discovered", discovered)):
        if not folder.is_dir():
            raise SpecCopyError(f"the {name} folder {folder} does not exist")
    report: list[str] = []
    problems: list[str] = []
    known: set[tuple[str, str]] = set()
    for record in _records(sessions):
        ended = read_end(record)
        if record.parent.name != ended.application:
            raise SpecCopyError(f"{record}: the record is of application {ended.application!r}")
        known.add((ended.application, ended.session))
        folder = copy_folder(discovered, ended.application, ended.session)
        name = f"{ended.application}/{ended.session}"
        if ended.final is None:
            why = "stopped" if ended.end != "ended" else "ended without an end snapshot"
            if folder.exists():
                problems.append(f"{folder}: session {name} was {why}; it has no final spec to copy")
            else:
                report.append(f"{name}: {why}, no copy")
            continue
        if not folder.is_dir():
            problems.append(f"{folder}: missing; session {name} ended and its copy has not been written")
            continue
        found = _compare(folder, ended.final)
        problems += found
        if not found:
            report.append(f"{name}: copy matches the record")
    for child in sorted(discovered.iterdir()):
        if child.is_file() and child.name in DISCOVERED_FILES:
            continue
        if not child.is_dir():
            problems.append(f"{child}: not part of the discovered folder")
            continue
        for folder in sorted(child.iterdir()):
            if not folder.is_dir():
                problems.append(f"{folder}: not part of the discovered folder")
            elif (child.name, folder.name) not in known:
                problems.append(f"{folder}: no sealed session record has this name")
    return report, problems


def export_main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: bench-export-spec <sealed session folder> <discovered folder>", file=sys.stderr)
        return 2
    try:
        folder = write_copy(Path(args[0]), Path(args[1]))
    except (SpecCopyError, OSError) as error:
        print(f"bench-export-spec: {error}", file=sys.stderr)
        return 1
    print(f"bench-export-spec: wrote {folder}")
    return 0


def check_main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: bench-check-discovered <sessions folder> <discovered folder>", file=sys.stderr)
        return 2
    try:
        report, problems = check_copies(Path(args[0]), Path(args[1]))
    except (SpecCopyError, OSError) as error:
        print(f"bench-check-discovered: {error}", file=sys.stderr)
        return 2
    for line in report:
        print(line)
    for line in problems:
        print(line, file=sys.stderr)
    if problems:
        print(f"bench-check-discovered: {len(problems)} problem(s)", file=sys.stderr)
        return 1
    print("bench-check-discovered: every copy matches its record")
    return 0
