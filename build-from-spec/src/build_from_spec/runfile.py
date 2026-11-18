"""Run data file, run file and author sidecar (design 3.11, 3.13, 4.3-4.5).

Requirements 11.11, 14.2, 14.4 and 16.5 are the reason for these formats.

The run data file is the builder's text, written at preparation and after each turn. The run file is derived
from a sealed run record (task 13.4). Both are JSON with `indent=2`, sorted keys, UTF-8 and a final newline.
Readers refuse a missing or an extra field, and a value outside its allowed set.

The author sidecar gives every character of a run file one author: the JSON string tokens of the relied-on ids
are the reader's text (`dr-kiro`), everything else is the bench's (`bench`).
"""

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from build_from_spec.apps import stop_not_implemented
from build_from_spec.folder import SETUPS, SPEC_FILES
from build_from_spec.turns import KINDS

FORMAT = 1
RESULTS = ("pass", "fail", "no-trial", "not-counted")
ENDS = ("ended", "stopped")
PROBLEMS = ("no-h1", "no-line", "bad-syntax", "unknown-id", "late")
# A relied-on id list is null for these problems (Requirement 14.2).
NULL_IDS_PROBLEMS = ("no-h1", "no-line", "bad-syntax")
# The run id of design 3.12. It is checked before any path is built from it; `runs.py` reads the same pattern.
RUN_ID = re.compile(r"(?P<request>[a-z0-9-]+)-(?P<setup>spec|none|record)-(?P<n>[1-9][0-9]*)")
TRIAL = re.compile(r"T[0-9]+")
SHA256 = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}")
RUN_DATA_SUFFIX = ".run-data.json"
RUN_FILE_SUFFIX = ".run.json"

REQUEST_FIELDS = ("id", "commit", "sha256")
SOURCE_FIELDS = ("application", "session", "seal")
KIRO_FIELDS = ("version", "model", "effort")
PROMPT_FIELDS = ("kind", "sha256", "time", "exit", "entries_before", "entries_after")
RECORD_FIELDS = ("seal", "end")
RELIED_FIELDS = ("ids", "problem")
LAST_FIELDS = ("trial", "phase")
RUN_DATA_FIELDS = (
    "format",
    "run",
    "setup",
    "request",
    "source",
    "seed",
    "adapter",
    "kiro",
    "files",
    "tools",
    "given",
    "prompts",
)
RUN_FILE_FIELDS = (
    "format",
    "run",
    "setup",
    "request",
    "source",
    "record",
    "seed",
    "kiro",
    "files",
    "tools",
    "given",
    "relied_on",
    "result",
    "first_in_range",
    "last_trial",
    "prompts",
    "continue_lines",
)


class RunFileError(Exception):
    """A run data file, run file or sidecar that breaks its format. The message names the file and field."""


def dump_text(data: Mapping[str, Any]) -> str:
    """The one serialisation of both files: `indent=2`, sorted keys, characters as written, final newline."""
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _fields(value: object, names: tuple[str, ...], where: str) -> dict[str, Any]:
    """An object with exactly `names` as its keys (Requirement 14.2: no missing and no extra field)."""
    if not isinstance(value, dict):
        raise RunFileError(f"{where}: expected an object")
    missing = [name for name in names if name not in value]
    extra = [name for name in value if name not in names]
    problems = []
    if missing:
        problems.append(f"missing {', '.join(missing)}")
    if extra:
        problems.append(f"unexpected {', '.join(extra)}")
    if problems:
        raise RunFileError(f"{where}: {'; '.join(problems)}")
    return value


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or value == "":
        raise RunFileError(f"{where}: expected a non-empty text")
    return value


def _integer(value: object, where: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise RunFileError(f"{where}: expected an integer of at least {minimum}")
    return value


def _pattern(value: object, pattern: re.Pattern[str], where: str, what: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise RunFileError(f"{where}: expected {what}")
    return value


def _one_of(value: object, options: tuple[str, ...], where: str) -> str:
    if value not in options:
        raise RunFileError(f"{where}: {value!r} is not one of {', '.join(options)}")
    return str(value)


def _sha(value: object, where: str) -> str:
    return _pattern(value, SHA256, where, "a SHA-256 in lowercase hex")


def _hashes(value: object, where: str) -> dict[str, str]:
    """An object of relative paths to SHA-256 values. Each path is inside the working folder (design 4.4)."""
    if not isinstance(value, dict):
        raise RunFileError(f"{where}: expected an object")
    for name, digest in value.items():
        if not isinstance(name, str) or name == "" or name.startswith("/") or ".." in name.split("/"):
            raise RunFileError(f"{where}: {name!r} is not a path inside the working folder")
        _sha(digest, f"{where}.{name}")
    return value


def _given(value: object, setup: str, where: str) -> dict[str, Any]:
    """What the setup gave the reader, in the shape of design 4.4 for that setup."""
    if setup == "none":
        if value != {}:
            raise RunFileError(f"{where}: setup none gives nothing, so it is an empty object")
        return {}
    if setup == "spec":
        spec = _fields(_fields(value, ("spec",), where)["spec"], SPEC_FILES, f"{where}.spec")
        for name in SPEC_FILES:
            _sha(spec[name], f"{where}.spec.{name}")
        return {"spec": spec}
    record = _fields(_fields(value, ("record",), where)["record"], ("removed",), f"{where}.record")
    if not isinstance(record["removed"], list):
        raise RunFileError(f"{where}.record.removed: expected a list")
    for index, item in enumerate(record["removed"]):
        here = f"{where}.record.removed[{index}]"
        item = _fields(item, ("seq", "hash"), here)
        _integer(item["seq"], f"{here}.seq")
        _sha(item["hash"], f"{here}.hash")
    return {"record": record}


def _check_prompts(value: object, where: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise RunFileError(f"{where}: expected a list of turns")
    for index, item in enumerate(value):
        here = f"{where}[{index}]"
        prompt = _fields(item, PROMPT_FIELDS, here)
        _one_of(prompt["kind"], KINDS, f"{here}.kind")
        _sha(prompt["sha256"], f"{here}.sha256")
        _text(prompt["time"], f"{here}.time")
        _integer(prompt["exit"], f"{here}.exit")
        _integer(prompt["entries_before"], f"{here}.entries_before")
        _integer(prompt["entries_after"], f"{here}.entries_after")
    return value


def _check_common(data: dict[str, Any], where: str) -> str:
    """The fields both files share. Returns the setup."""
    if _integer(data["format"], f"{where}.format") != FORMAT:
        raise RunFileError(f"{where}.format: only format {FORMAT} is read")
    run = _text(data["run"], f"{where}.run")
    setup = _one_of(data["setup"], SETUPS, f"{where}.setup")
    request = _fields(data["request"], REQUEST_FIELDS, f"{where}.request")
    _text(request["id"], f"{where}.request.id")
    _pattern(request["commit"], COMMIT, f"{where}.request.commit", "a git commit hash in lowercase hex")
    _sha(request["sha256"], f"{where}.request.sha256")
    found = RUN_ID.fullmatch(run)
    if found is None or found.group("setup") != setup or found.group("request") != request["id"]:
        raise RunFileError(f"{where}.run: {run!r} is not the run id of its request and setup")
    source = _fields(data["source"], SOURCE_FIELDS, f"{where}.source")
    _text(source["application"], f"{where}.source.application")
    _text(source["session"], f"{where}.source.session")
    _sha(source["seal"], f"{where}.source.seal")
    _integer(data["seed"], f"{where}.seed")
    kiro = _fields(data["kiro"], KIRO_FIELDS, f"{where}.kiro")
    for name in KIRO_FIELDS:
        _text(kiro[name], f"{where}.kiro.{name}")
    _hashes(data["files"], f"{where}.files")
    _hashes(data["tools"], f"{where}.tools")
    _given(data["given"], setup, f"{where}.given")
    return setup


def check_run_data(data: object, where: str = "run data file") -> dict[str, Any]:
    """Check a run data file (design 4.3). Return it unchanged when it is valid."""
    checked = _fields(data, RUN_DATA_FIELDS, where)
    _check_common(checked, where)
    _text(checked["adapter"], f"{where}.adapter")
    _check_prompts(checked["prompts"], f"{where}.prompts")
    return checked


def _check_relied(value: object, where: str) -> None:
    relied = _fields(value, RELIED_FIELDS, where)
    problem = relied["problem"]
    if problem is not None:
        _one_of(problem, PROBLEMS, f"{where}.problem")
    if problem in NULL_IDS_PROBLEMS:
        if relied["ids"] is not None:
            raise RunFileError(f"{where}.ids: null when the problem is {problem}")
        return
    if not isinstance(relied["ids"], list) or relied["ids"] == []:
        raise RunFileError(f"{where}.ids: expected a non-empty list of ids")
    for index, identifier in enumerate(relied["ids"]):
        _text(identifier, f"{where}.ids[{index}]")


def check_run_file(data: object, where: str = "run file") -> dict[str, Any]:
    """Check a run file (design 4.4). Return it unchanged when it is valid."""
    checked = _fields(data, RUN_FILE_FIELDS, where)
    _check_common(checked, where)
    record = _fields(checked["record"], RECORD_FIELDS, f"{where}.record")
    _sha(record["seal"], f"{where}.record.seal")
    _one_of(record["end"], ENDS, f"{where}.record.end")
    _check_relied(checked["relied_on"], f"{where}.relied_on")
    _one_of(checked["result"], RESULTS, f"{where}.result")
    first = checked["first_in_range"]
    if first is not None:
        _pattern(first, TRIAL, f"{where}.first_in_range", "a trial id or null")
    last = checked["last_trial"]
    if last is not None:
        last = _fields(last, LAST_FIELDS, f"{where}.last_trial")
        _pattern(last["trial"], TRIAL, f"{where}.last_trial.trial", "a trial id")
        _text(last["phase"], f"{where}.last_trial.phase")
    prompts = _check_prompts(checked["prompts"], f"{where}.prompts")
    continues = sum(1 for prompt in prompts if prompt["kind"] == "continue")
    if _integer(checked["continue_lines"], f"{where}.continue_lines") != continues:
        raise RunFileError(
            f"{where}.continue_lines: {checked['continue_lines']} but {continues} continue turns"
        )
    return checked


def _load(path: Path) -> object:
    if not path.is_file():
        raise RunFileError(f"{path}: not found")
    try:
        return json.loads(path.read_bytes().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RunFileError(f"{path}: not valid JSON in UTF-8 ({error})") from error


def read_run_data(path: Path) -> dict[str, Any]:
    """Read and check a run data file. Refuse, naming the file, when it is missing or malformed."""
    return check_run_data(_load(Path(path)), str(path))


def write_run_data(path: Path, data: Mapping[str, Any]) -> None:
    """Check and write a run data file. It is rewritten after each turn, so an existing file is replaced."""
    path = Path(path)
    checked = check_run_data(dict(data), str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_text(checked), encoding="utf-8", newline="")


def read_run_file(path: Path) -> dict[str, Any]:
    """Read and check a run file. Refuse, naming the file, when it is missing or malformed."""
    return check_run_file(_load(Path(path)), str(path))


def _relied_pieces(data: dict[str, Any], ids: list[str]) -> list[tuple[str, str]]:
    """The run file text as (text, author) pieces: each relied-on id token is `dr-kiro`, the rest `bench`.

    The ids are written as placeholders first. The placeholder prefix is chosen so that it does not occur in
    the rest of the file, so each placeholder is found once. The id tokens replace the placeholders."""
    problem = data["relied_on"]["problem"]
    rest = dump_text({**data, "relied_on": {"ids": [], "problem": problem}})
    number = 0
    while f"relied-id-{number}" in rest:
        number += 1
    placeholders = [f"relied-id-{number}:{index}" for index in range(len(ids))]
    text = dump_text({**data, "relied_on": {"ids": placeholders, "problem": problem}})
    pieces: list[tuple[str, str]] = []
    cursor = 0
    for identifier, placeholder in zip(ids, placeholders, strict=True):
        token = json.dumps(placeholder, ensure_ascii=False)
        if text.count(token) != 1:
            raise RunFileError(f"the placeholder of relied-on id {identifier!r} is not unique")
        start = text.index(token, cursor)
        pieces.append((text[cursor:start], "bench"))
        pieces.append((json.dumps(identifier, ensure_ascii=False), "dr-kiro"))
        cursor = start + len(token)
    pieces.append((text[cursor:], "bench"))
    return pieces


def run_file_texts(run_file: Mapping[str, Any]) -> tuple[str, str]:
    """The text of a run file, and of its author sidecar `<run file name>.authors.json` (design 3.13).

    The sidecar lists character ranges that cover the run file in order without gaps, in the format that
    `bench.scan.levels.sidecar_pieces` reads."""
    data = check_run_file(dict(run_file))
    ids = data["relied_on"]["ids"]
    pieces = [(dump_text(data), "bench")] if ids is None else _relied_pieces(data, ids)
    ranges = []
    offset = 0
    for piece, author in pieces:
        if piece:  # a range is never empty, so an empty piece is not listed
            ranges.append({"start": offset, "end": offset + len(piece), "author": author})
            offset += len(piece)
    text = "".join(piece for piece, _ in pieces)
    return text, dump_text({"ranges": ranges})


def main() -> None:
    stop_not_implemented("bfs-run-file")
