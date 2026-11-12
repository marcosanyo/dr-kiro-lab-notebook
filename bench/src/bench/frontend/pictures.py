"""Picture files in the lab (Requirements 17.13-17.16, design F5).

Each picture is written as `pictures/<experiment id>-<trial id>.<ext>` before the result is returned, and
its path relative to the lab is returned in place of the image.
"""

from pathlib import Path

from bench.core.session import TrialOutput

FOLDER = "pictures"
EXTENSIONS = {"image/png": "png", "image/gif": "gif", "image/webp": "webp"}


class PictureWriteError(Exception):
    """A picture file could not be written. `detail` is the system error, for the builder-side log."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class PictureWriter:
    def __init__(self, lab: Path) -> None:
        self.lab = Path(lab)

    def __call__(self, experiment: str, trial: TrialOutput) -> str:
        relative = f"{FOLDER}/{experiment}-{trial.trial}.{EXTENSIONS[trial.picture.kind]}"
        target = self.lab / relative
        try:
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(trial.picture.data)
        except OSError as error:
            raise PictureWriteError(f"writing {target}: {error}") from error
        return relative
