"""Site: every file of the site by its path, with the author ranges of each text file; the sidecars; and
the one write, into a staging folder renamed onto the output folder (design 12, N4, N28).

The site is flat (design N28): every page is at the root, pictures are in `p/` and the stylesheet and the
script in `a/`. A path is added once; a second file with the same path, or with a path that differs only by
case, is refused, naming both owners. A text file reserves its sidecar path `<file>.authors.json`.

Writing never deletes a file. It creates `<parent>/.<out-name>.staging` (refused if it exists), writes every
file in sorted path order, and renames the staging folder onto the output folder with one `os.replace`. A
write that fails stops the build, naming the staging folder, which is left in place; the next build refuses
while it exists (Requirement 2.7).
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from bench.scan.levels import SIDECAR_SUFFIX

from notebook import addresses
from notebook.errors import NotebookError
from notebook.ink import Segment
from notebook.inputs import check_out

# The suffixes of the text files that get a sidecar (Requirement 20.3).
TEXT_SUFFIXES = (".html", ".css", ".js")
# The only folders of the site (design N28).
FOLDERS = (addresses.PICTURE_DIR, addresses.ASSET_DIR)

Ranges = list[dict[str, int | str]]


@dataclass(frozen=True)
class _Entry:
    owner: str
    segments: tuple[Segment, ...] | None  # a text file, before the scan joins it
    data: bytes | None  # a binary file, copied as given


def _check_path(path: str, owner: str) -> None:
    parts = path.split("/")
    bad = (
        not path
        or path.startswith("/")
        or "\\" in path
        or any(p in ("", ".", "..") for p in parts)
        or len(parts) > 2
        or (len(parts) == 2 and parts[0] not in FOLDERS)
    )
    if bad:
        raise NotebookError(
            owner, f"{path!r} is not a site path: a page is at the site root, other files only in p/ or a/"
        )


def staging_folder(out: Path) -> Path:
    """`<parent>/.<out-name>.staging`, a sibling of the output folder, so the rename stays on one disk."""
    return out.parent / f".{out.name}.staging"


def check_target(out: Path) -> None:
    """The output folder is absent or empty (Requirement 1.4), its parent is a folder, and no staging folder
    is left from an earlier build. Run before anything is read."""
    check_out(out)
    if not out.parent.is_dir():
        raise NotebookError(str(out), f"the output folder's parent {out.parent} is not a folder")
    staging = staging_folder(out)
    if staging.exists() or staging.is_symlink():
        raise NotebookError(
            str(staging),
            "a staging folder from an earlier build is in place; look at it and remove it by hand",
        )


class Site:
    """The files of the site, by path relative to the site root."""

    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}
        # lower-case path -> (path, owner), so no two paths are equal or differ only by case
        self._taken: dict[str, tuple[str, str]] = {}

    def _reserve(self, path: str, owner: str) -> None:
        _check_path(path, owner)
        taken = self._taken.get(path.lower())
        if taken is not None:
            other, first = taken
            raise NotebookError(
                owner,
                f"the site path {path!r} is already taken by {other!r} of {first}; two files cannot share it",
            )
        self._taken[path.lower()] = (path, owner)

    def add_text(self, path: str, segments: list[Segment], owner: str) -> None:
        """A page, the stylesheet or the script, as segments; it gets a sidecar."""
        if not path.endswith(TEXT_SUFFIXES):
            raise NotebookError(
                owner, f"{path!r} is not a text file of the site ({', '.join(TEXT_SUFFIXES)})"
            )
        self._reserve(path, owner)
        self._reserve(path + SIDECAR_SUFFIX, owner)
        self._entries[path] = _Entry(owner, tuple(segments), None)

    def add_bytes(self, path: str, data: bytes, owner: str) -> None:
        """A picture, copied byte for byte (Requirement 7.7)."""
        if path.endswith(TEXT_SUFFIXES) or path.endswith(SIDECAR_SUFFIX):
            raise NotebookError(owner, f"{path!r} is a text file name; text files are added as segments")
        self._reserve(path, owner)
        self._entries[path] = _Entry(owner, None, bytes(data))

    def texts(self) -> dict[str, list[Segment]]:
        """Every text file's segments, for the scan."""
        return {p: list(e.segments) for p, e in sorted(self._entries.items()) if e.segments is not None}

    def files(self, joined: dict[str, tuple[str, Ranges]]) -> dict[str, bytes]:
        """Every file's bytes, sidecars included, in sorted path order. `joined` is the scan's result: each
        text file's joined text and author ranges (`scan.check`)."""
        texts = set(self.texts())
        if set(joined) != texts:
            raise NotebookError(
                "site",
                f"the scanned files {sorted(joined)} are not the text files of the site {sorted(texts)}",
            )
        out: dict[str, bytes] = {}
        for path, entry in self._entries.items():
            if entry.data is not None:
                out[path] = entry.data
                continue
            written, ranges = joined[path]
            if not ranges:
                raise NotebookError(entry.owner, f"{path} is empty, so its sidecar would have no range")
            out[path] = written.encode("utf-8")
            out[path + SIDECAR_SUFFIX] = sidecar(ranges)
        return dict(sorted(out.items()))


def sidecar(ranges: Ranges) -> bytes:
    """The `<file>.authors.json` body the bench's scan reads (`bench.scan.levels.sidecar_pieces`)."""
    body = json.dumps({"ranges": ranges}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return (body + "\n").encode("utf-8")


def write(files: dict[str, bytes], out: Path) -> None:
    """Write `files` into a fresh staging folder in sorted path order, then rename it onto `out`."""
    check_target(out)
    staging = staging_folder(out)
    try:
        staging.mkdir()
        for path in sorted(files):
            target = staging / path
            target.parent.mkdir(exist_ok=True)
            with open(target, "xb") as handle:
                handle.write(files[path])
        os.replace(staging, out)
    except OSError as error:
        raise NotebookError(
            str(staging), f"writing the site failed ({error}); the staging folder is left in place"
        ) from error
