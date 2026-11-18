"""The application table: the wrapped adapter, its scan sources and its reader budget (design 3.1).

This is the only place a reader budget is written (Requirements 4.3, 4.7, 8.6). Paths are relative to the
repository root, and every command runs from there (design B24).

An application marked `rehearsal` exists only for the rehearsal (build-from-spec/rehearsal/RUN.md). Its runs,
its requests and its records must sit in the rehearsal folders, and a real application's runs must not.
"""

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class App:
    name: str  # the application name in records and request files
    adapter: str  # module:factory of the application's adapter
    scan_sources: str  # its scan_sources.toml, relative to the repository root
    budget: int  # the reader budget in trials
    rehearsal: bool  # True for the rehearsal application only (see check_records and request_folder)


REQUESTS = Path("build-from-spec") / "requests"
PRODUCTION_RECORDS = Path("sessions") / "build-from-spec"  # the only records folder bfs-check-runs reads
REHEARSAL_REQUESTS = Path("build-from-spec") / "rehearsal" / "requests"
REHEARSAL_ROOT = Path("bench-run") / "build-from-spec" / "rehearsal"  # the rehearsal's records and sources

APPS = {
    "body-lab": App(
        "body-lab", "body_lab.adapter:BodyAdapter", "body-lab/adapter/scan_sources.toml", 12, False
    ),
    "fake": App("fake", "bench.fake.adapter:FakeAdapter", "bench/src/bench/fake/scan_sources.toml", 12, True),
}


class AppError(Exception):
    """An application with no reader budget, a command run outside the repository root, or a run whose
    application and records folder do not belong together."""


def app_for(name: str, apps: dict[str, App]) -> App:
    """Return the table entry of `name`, or refuse, naming the application (Requirements 4.7, 8.6)."""
    if name not in apps:
        raise AppError(f"no reader budget is decided for {name}")
    return apps[name]


def request_folder(app: App) -> Path:
    """The folder of the request files of an application, relative to the repository root."""
    return REHEARSAL_REQUESTS if app.rehearsal else REQUESTS


def check_records(app: App, records: Path, root: Path) -> None:
    """Refuse a records folder that does not belong to the application.

    The rehearsal application records only under REHEARSAL_ROOT. A real application records only in
    PRODUCTION_RECORDS, the folder that bfs-check-runs reads, and never in the rehearsal folder."""
    root = Path(root)
    records = Path(records).resolve()
    inside = records.is_relative_to((root / REHEARSAL_ROOT).resolve())
    if app.rehearsal and not inside:
        raise AppError(
            f"{app.name} is the rehearsal application; its records go under {REHEARSAL_ROOT}, "
            f"not under {records}"
        )
    if inside and not app.rehearsal:
        raise AppError(f"{app.name} runs do not go under {REHEARSAL_ROOT}; that folder is for the rehearsal")
    if not app.rehearsal and records != (root / PRODUCTION_RECORDS).resolve():
        raise AppError(
            f"{app.name} runs go under {PRODUCTION_RECORDS}; bfs-check-runs reads no other folder: {records}"
        )


def require_repository_root() -> None:
    """Stop unless the current folder is the repository root, the folder that holds `.git` (design B24)."""
    if not (Path.cwd() / ".git").exists():
        raise AppError(
            "run this command from the repository root (the folder with .git); "
            f"the current folder is {Path.cwd()}"
        )


def stop_not_implemented(command: str) -> None:
    """The stub every command starts with until its task is done: refuse to run, with a non-zero exit."""
    try:
        require_repository_root()
    except AppError as error:
        sys.exit(f"{command}: {error}")
    sys.exit(f"{command}: not implemented yet")
