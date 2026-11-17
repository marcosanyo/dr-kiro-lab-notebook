"""The application table: the wrapped adapter, its scan sources and its reader budget (design 3.1).

This is the only place a reader budget is written (Requirements 4.3, 4.7, 8.6). Paths are relative to the
repository root, and every command runs from there (design B24).
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


APPS = {
    "body-lab": App("body-lab", "body_lab.adapter:BodyAdapter", "body-lab/adapter/scan_sources.toml", 12),
}


class AppError(Exception):
    """An application with no reader budget, or a command run outside the repository root."""


def app_for(name: str, apps: dict[str, App]) -> App:
    """Return the table entry of `name`, or refuse, naming the application (Requirements 4.7, 8.6)."""
    if name not in apps:
        raise AppError(f"no reader budget is decided for {name}")
    return apps[name]


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
