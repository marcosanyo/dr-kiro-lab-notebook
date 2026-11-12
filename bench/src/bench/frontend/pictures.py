"""Picture files in the lab (Requirements 17.13-17.16, design F5).

Each picture is written as `pictures/<experiment id>-<trial id>.<ext>` before the result is returned: first
to a temporary name in the same folder, then flushed, synced and renamed, so a half-written picture never
appears. Its path relative to the lab is returned in place of the image. The record keeps the adapter's
bytes; the lab's file is a copy that the bench never reads back.
"""

import os
from pathlib import Path

from bench.core.session import TrialOutput

FOLDER = "pictures"
EXTENSIONS = {"image/png": "png", "image/gif": "gif", "image/webp": "webp"}
# Fixed bench wording for a picture that cannot be written; the system error goes to builder.log only.
NOT_DELIVERED = "a picture could not be delivered"


class PictureWriteError(Exception):
    """A picture file could not be written. `detail` is the system error, for the builder-side log."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class PictureWriter:
    def __init__(self, lab: Path) -> None:
        self.lab = Path(lab)

    def __call__(self, experiment: str, trial: TrialOutput) -> str:
        name = f"{experiment}-{trial.trial}.{EXTENSIONS[trial.picture.kind]}"
        folder = self.lab / FOLDER
        target = folder / name
        temporary = folder / f".{name}.tmp"
        try:
            folder.mkdir(exist_ok=True)
            with open(temporary, "wb") as out:
                out.write(trial.picture.data)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, target)
        except OSError as error:
            raise PictureWriteError(f"writing {target}: {error}") from error
        return f"{FOLDER}/{name}"
