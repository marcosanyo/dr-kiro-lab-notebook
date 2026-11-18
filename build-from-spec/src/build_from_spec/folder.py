"""The reader's working folder (design 3.5; Requirements 4.1, 4.2, 4.5, 7.2, 7.3, 7.5, 7.6, 7.7).

Everything outside `given/` depends on the request only, so the setups of one request differ only in
`given/` (Requirement 4.2). This module writes the folder and hashes it; the run script chooses the folder's
place under `bench-run/build-from-spec/<run-id>/`.
"""

import hashlib
from dataclasses import dataclass, replace
from importlib import resources
from pathlib import Path

from bench.frontend.describe import descriptions
from bench.frontend.labhooks import install as install_hooks
from bench.record.chain import BLOB_DIR
from bench.record.spec_copy import final_spec
from bench.scan.scan import Finding, Scanner

from build_from_spec.reduced import Removed, check_reduced, plan
from build_from_spec.request import Request
from build_from_spec.wrap import ReaderAdapter

SETUPS = ("spec", "none", "record")
DISCOVERED_TABLE = "not-required"  # every reader run (design 4.2, Requirement 12)
GIVEN = "given"
RECORD = "record"  # the reduced record copy inside given/ (Requirement 6.1)
EXPERIMENTS = "experiments"
REQUEST = "request.md"
SPEC_FILES = ("requirements.md", "design.md", "tasks.md")
FILES = resources.files("build_from_spec") / "files"
METHOD = resources.files("bench.drkiro") / "files" / "method.md"
METHOD_TARGET = ".kiro/steering/method.md"
LAB_SPEC = ".kiro/specs/lab/"
BUILDER_FILES = {
    "reader.json": ".kiro/agents/reader.json",
    "reader-prompt.md": ".kiro/agents/reader-prompt.md",
    "reader.md": ".kiro/steering/reader.md",
    "requirements.md": ".kiro/specs/lab/requirements.md",
    "design.md": ".kiro/specs/lab/design.md",
    "tasks.md": ".kiro/specs/lab/tasks.md",
}


class FolderError(Exception):
    """A working folder that cannot be written, hashed or scanned. The message names what is wrong."""


@dataclass(frozen=True)
class GivenFiles:
    files: dict[str, bytes]  # names relative to given/
    removed: tuple[
        Removed, ...
    ] = ()  # record setup: the snapshot entries left out of the copy (Requirement 6.4)
    copy_source: Path | None = None  # record setup: the sealed record the copy is checked against (6.3)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def builder_files(request: Request) -> dict[str, bytes]:
    """Every file outside `given/` that the builder writes, by path in the folder. The hooks are not here:
    `labhooks.install` writes them (design 3.5)."""
    files = {target: (FILES / source).read_bytes() for source, target in BUILDER_FILES.items()}
    files[METHOD_TARGET] = METHOD.read_bytes()
    files[REQUEST] = request.words.encode("utf-8")
    return files


def given_files(setup: str, source: Path) -> GivenFiles:
    """The contents of `given/` for a setup. `spec` gives the final spec, `none` nothing, `record` the reduced
    copy of the source record in `given/record/` (Requirement 4.1). Fail for an unknown setup."""
    if setup == "spec":
        return GivenFiles(dict(final_spec(source).files))
    if setup == "none":
        return GivenFiles({})
    if setup == "record":
        made = plan(source)
        files = {f"{RECORD}/{name}": data for name, data in made.files().items()}
        return GivenFiles(files, made.removed, Path(source))
    raise FolderError(f"unknown setup {setup!r}; the setups are {', '.join(SETUPS)}")


def write_folder(folder: Path, request: Request, given: GivenFiles) -> None:
    """Write a fresh working folder. Refuse a folder that already exists (Requirement 7.1).

    For the record setup, run the copy check (Requirement 6.6) before anything can start: refuse, naming
    each line or blob that differs. The folder is kept, so the user can see what was written."""
    folder = Path(folder)
    if folder.exists():
        raise FolderError(f"{folder} already exists; a run starts in a fresh folder")
    folder.mkdir(parents=True)
    for name, data in builder_files(request).items():
        _write(folder / name, data)
    install_hooks(folder)
    (folder / EXPERIMENTS).mkdir()
    (folder / GIVEN).mkdir()
    for name, data in given.files.items():
        _write(folder / GIVEN / name, data)
    if given.copy_source is not None:
        copy = folder / GIVEN / RECORD
        (copy / BLOB_DIR).mkdir(parents=True, exist_ok=True)  # the source always has a blobs folder
        problems = check_reduced(copy, given.copy_source)
        if problems:
            raise FolderError(
                f"the reduced record copy in {copy} does not match {given.copy_source}: "
                + "; ".join(problems)
            )


def _files(folder: Path) -> list[tuple[str, Path]]:
    """Every file under `folder` as (relative POSIX path, path), sorted by the relative path."""
    found = [(p.relative_to(folder).as_posix(), p) for p in folder.rglob("*") if p.is_file()]
    return sorted(found)


def file_hashes(folder: Path) -> dict[str, str]:
    """SHA-256 of every file outside `given/`, by relative POSIX path (Requirement 7.3)."""
    folder = Path(folder)
    return {
        where: _digest(path.read_bytes()) for where, path in _files(folder) if where.split("/")[0] != GIVEN
    }


def tool_hashes(adapter: ReaderAdapter) -> dict[str, str]:
    """SHA-256 of each bench tool description the reader receives, by tool name (Requirement 7.3)."""
    texts = descriptions(adapter.declaration(), DISCOVERED_TABLE)
    return {name: _digest(text.encode("utf-8")) for name, text in texts.items()}


def _level(where: str, data: bytes) -> str:
    """The blind-scan level of one file of the working folder (Requirement 7.6)."""
    parts = where.split("/")
    if parts[0] == GIVEN:
        if len(parts) == 2 and parts[1] in SPEC_FILES:
            return "dr-kiro"
        raise FolderError(f"{where}: given/ holds only the spec files of the setup, not this file")
    if where.startswith(LAB_SPEC) and where[len(LAB_SPEC) :] in SPEC_FILES:
        # A template not yet changed is the builder's text, as in the lab scan (dr-kiro design 6).
        template = (FILES / where[len(LAB_SPEC) :]).read_bytes()
        return "builder" if data == template else "dr-kiro"
    if parts[0] == EXPERIMENTS:
        return "dr-kiro"
    return "builder"


def scan_folder(scanner: Scanner, folder: Path) -> list[Finding]:
    """The blind scan of the working folder, each file at its level. Findings name the file relative to the
    folder (Requirement 7.5, 7.6). The reduced record copy is scanned by its record, each text at the level of
    its recorded author (7.6); its findings name `given/record/` files."""
    folder = Path(folder)
    findings: list[Finding] = []
    record = folder / GIVEN / RECORD
    for where, path in _files(folder):
        if where.startswith(f"{GIVEN}/{RECORD}/"):
            continue
        data = path.read_bytes()
        findings += scanner.scan_text(data.decode("utf-8"), _level(where, data), where)
    if record.is_dir():
        for finding in scanner.scan_record(record):
            where = Path(finding.file).relative_to(record).as_posix()
            findings.append(replace(finding, file=f"{GIVEN}/{RECORD}/{where}"))
    return findings
