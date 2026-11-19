"""The reader's requests (`build-from-spec/requests/<id>.toml`), read for the notebook.

A request is the committed file the reader's runs answer: its sentence (`words`), the application it is
about and the pass ranges that decide a run. A run file records the SHA-256 of the request file it was run
against; this module reads the file the run names and refuses it when its bytes have another hash, so the
sentence the notebook shows is the sentence the runs were given. Only these files are read; the spec
documents are not.
"""

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path

from notebook.errors import NotebookError
from notebook.readerruns import Run

_KEYS = frozenset({"id", "application", "words", "pass"})
_PASS_KEYS = frozenset({"measurement", "range"})


@dataclass(frozen=True)
class Pass:
    measurement: str
    low: float
    high: float


@dataclass(frozen=True)
class Request:
    id: str
    application: str
    words: str
    passes: tuple[Pass, ...]
    where: str  # the file, for messages and as the source of the shown text


def _number(value: object, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise NotebookError(where, "a pass range holds a value that is not a number")
    return float(value)


def load(folder: Path, runs: list[Run]) -> dict[str, Request]:
    """The request of every request id named by `runs`, by id. `folder` is the requests folder."""
    out: dict[str, Request] = {}
    for run in runs:
        if run.request_id in out:
            continue
        path = Path(folder) / f"{run.request_id}.toml"
        where = str(path)
        if not path.is_file():
            raise NotebookError(where, f"the request of run {run.name} is not a file")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != run.request_sha256:
            raise NotebookError(
                where,
                f"its SHA-256 is {digest}; run {run.name} was given the request with {run.request_sha256}",
            )
        try:
            table = tomllib.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            raise NotebookError(where, f"the request file cannot be read ({error})") from error
        if set(table) != _KEYS:
            raise NotebookError(where, f"the request file does not have exactly the keys {sorted(_KEYS)}")
        if table["id"] != run.request_id:
            raise NotebookError(where, f"its id is {table['id']!r}, not {run.request_id!r}")
        if not isinstance(table["words"], str) or not table["words"].strip():
            raise NotebookError(where, "words is not a text")
        if not isinstance(table["application"], str):
            raise NotebookError(where, "application is not a text")
        passes = []
        for i, item in enumerate(table["pass"], start=1):
            if not isinstance(item, dict) or set(item) != _PASS_KEYS:
                raise NotebookError(where, f"pass {i} does not have exactly the keys {sorted(_PASS_KEYS)}")
            bounds = item["range"]
            if not isinstance(bounds, list) or len(bounds) != 2:
                raise NotebookError(where, f"pass {i} range is not two numbers")
            passes.append(
                Pass(str(item["measurement"]), _number(bounds[0], where), _number(bounds[1], where))
            )
        out[run.request_id] = Request(table["id"], table["application"], table["words"], tuple(passes), where)
    return out
