"""Every folder and file the build reads, given explicitly, and the output-folder check (Req. 1.3, 1.4)."""

from dataclasses import dataclass
from pathlib import Path

from notebook.errors import NotebookError


@dataclass(frozen=True)
class Inputs:
    """The build's inputs, exactly as given on the command line. No field has a default."""

    sessions: Path
    requests: Path
    choices: Path
    layouts: Path
    words: Path
    scan_configs: tuple[Path, ...]
    stop_list: Path
    out: Path


def check_out(out: Path) -> None:
    """Refuse an output folder that exists and is not an empty folder (Requirement 1.4). Reads only `out`."""
    if not out.exists():
        return
    if not out.is_dir():
        raise NotebookError(str(out), "the output path is not a folder; give a new or empty folder")
    if any(out.iterdir()):
        raise NotebookError(str(out), "the output folder is not empty; give a new or empty folder")
