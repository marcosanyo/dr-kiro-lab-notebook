"""Run data file, run file and author sidecar (design 3.11, 3.13, 4.3-4.5).

Requirements 11.11, 14.2, 14.4 and 16.5 are the reason for these formats.

The run data file is the builder's text, written at preparation and after each turn. The run file is derived
from a sealed run record (task 13.4). Both are JSON with `indent=2`, sorted keys, UTF-8 and a final newline.
Readers refuse a missing or an extra field, and a value outside its allowed set.

The author sidecar gives every character of a run file one author: the JSON string tokens of the relied-on ids
are the reader's text (`dr-kiro`), everything else is the bench's (`bench`).
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from bench.record.chain import VerifyError, verify
from bench.scan.levels import SIDECAR_SUFFIX
from bench.scan.scan import Scanner
from bench.scan.terms import ScanError

from build_from_spec.apps import (
    APPS,
    App,
    AppError,
    app_for,
    check_records,
    request_folder,
    require_repository_root,
)
from build_from_spec.folder import SETUPS, SPEC_FILES
from build_from_spec.judge import JudgeError, judge_record
from build_from_spec.relied import ReliedError, allowed_ids
from build_from_spec.request import STOP_LIST, RequestError, parse_request
from build_from_spec.runs import RUN_FILE_SUFFIX, RUN_ID
from build_from_spec.turns import KINDS

FORMAT = 1
RESULTS = ("pass", "fail", "no-trial", "not-counted")
ENDS = ("ended", "stopped")
PROBLEMS = ("no-h1", "no-line", "bad-syntax", "unknown-id", "late")
# A relied-on id list is null for these problems (Requirement 14.2).
NULL_IDS_PROBLEMS = ("no-h1", "no-line", "bad-syntax")
TRIAL = re.compile(r"T[0-9]+")
SHA256 = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}")
RUN_DATA_SUFFIX = ".run-data.json"
# What the reader could not use from the setup (Kiro decision K30). Set from the setup, checked against it.
RECORD_LIMIT = (
    "The pictures in the raw record could not be opened with Kiro CLI's file reading; "
    "the record reader used the record's text and experiment files only."
)


def limits_for(setup: str) -> list[str]:
    """The limits of a run with this setup: the picture limit for `record`, none for the others (K30)."""
    return [RECORD_LIMIT] if setup == "record" else []


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
# The named variant the run was made on (lab-bench Requirement 23, body-lab Requirement 7). Present only
# when the run named one, so run data and run files written without a variant stay valid.
VARIANT_FIELD = "variant"
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
    "limits",
)


class RunFileError(Exception):
    """A run data file, run file or sidecar that breaks its format. The message names the file and field."""


def dump_text(data: Mapping[str, Any]) -> str:
    """The one serialisation of both files: `indent=2`, sorted keys, characters as written, final newline."""
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _optional_fields(value: object, names: tuple[str, ...], where: str) -> dict[str, Any]:
    """Like `_fields`, and also the optional variant field when the object has it."""
    present = names + ((VARIANT_FIELD,) if isinstance(value, dict) and VARIANT_FIELD in value else ())
    return _fields(value, present, where)


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
    if found is None:
        raise RunFileError(
            f"{where}.run: {run!r} is not a run id of the form <request>-<spec|none|record>-<n>"
        )
    if found.group("setup") != setup:
        raise RunFileError(f"{where}.setup: {setup!r} is not the setup of run {run!r}")
    if found.group("request") != request["id"]:
        raise RunFileError(f"{where}.request.id: {request['id']!r} is not the request of run {run!r}")
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
    checked = _optional_fields(data, RUN_DATA_FIELDS, where)
    _check_common(checked, where)
    _text(checked["adapter"], f"{where}.adapter")
    if VARIANT_FIELD in checked:
        _text(checked[VARIANT_FIELD], f"{where}.{VARIANT_FIELD}")
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
    checked = _optional_fields(data, RUN_FILE_FIELDS, where)
    _check_common(checked, where)
    if VARIANT_FIELD in checked:
        _text(checked[VARIANT_FIELD], f"{where}.{VARIANT_FIELD}")
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
    limits = checked["limits"]
    if not isinstance(limits, list) or any(not isinstance(item, str) for item in limits):
        raise RunFileError(f"{where}.limits: expected a list of texts")
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


RUN_DATA = Path("bench-run") / "build-from-spec"


def _valid_run_id(run_id: str) -> str:
    """Refuse a run id that is not of the form of design 3.12, before any path is built from it."""
    if RUN_ID.fullmatch(run_id) is None:
        raise RunFileError(f"{run_id!r} is not a run id of the form <request>-<spec|none|record>-<n>")
    return run_id


def _sealed(folder: Path) -> list[dict[str, Any]]:
    """The entries of a sealed record. Refuse, naming the folder, when it is not sealed or does not verify."""
    try:
        return verify(folder, sealed=True)
    except VerifyError as error:
        raise RunFileError(f"{folder}: the record is not sealed or does not verify ({error})") from error


def committed_request(root: Path, commit: str, request_id: str, folder: Path) -> bytes:
    """The request file as it is at `commit` (Requirement 14.3), read from git, not the working tree.

    `folder` is the request folder of the application, relative to the root (apps.request_folder)."""
    path = (folder / f"{request_id}.toml").as_posix()
    shown = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{path}"], capture_output=True, check=False
    )
    if shown.returncode != 0:
        problem = shown.stderr.decode("utf-8", errors="replace").strip()
        raise RunFileError(f"{path} at commit {commit} cannot be read from git: {problem}")
    return shown.stdout


def write_run_file(
    run_id: str,
    apps: Mapping[str, App],
    stop_list: Path,
    root: Path,
    records: Path,
) -> Path:
    """Write the run file and its author sidecar of a sealed run record (design 3.11; Requirements 14.1,
    14.5, 16.2). Return the run file's path.

    An existing run file is refused: a run file is never rewritten by this command (K34).

    `root` is the repository root, and every path is derived from it (design B24). `records` is the records
    folder of the run (`--sessions`). The source records sit in its parent, one folder per application, so a
    production source is in `sessions/` and a rehearsal source is beside its rehearsal records.

    Nothing is written before every check passes. The two files are written under temporary names first. The
    blind scan covers the run
    record and the temporary run file. A finding removes the temporary files and stops, so the run record and
    the run file stay as they were. The sidecar is renamed before the run file, so a run file never exists
    without its sidecar.

    Run ids are not checked for uniqueness here: that is the run script's check (Requirement 7.1).
    This function refuses only an existing run file, as design 3.11 says."""
    root = Path(root)
    run_id = _valid_run_id(run_id)
    data = read_run_data(root / RUN_DATA / f"{run_id}{RUN_DATA_SUFFIX}")
    if data["run"] != run_id:
        raise RunFileError(f"{run_id}: the run data file names run {data['run']!r}")
    app = app_for(data["source"]["application"], apps)
    check_records(app, records, root)
    application = app.name
    run_file = records / application / f"{run_id}{RUN_FILE_SUFFIX}"
    sidecar = run_file.with_name(run_file.name + SIDECAR_SUFFIX)
    if run_file.exists():
        raise RunFileError(f"{run_file}: already exists; a run file is never overwritten")
    folder = records / application / run_id
    if not folder.is_dir():
        raise RunFileError(f"{folder}: no run record; the run file is written once the run is sealed")
    seal = _sealed(folder)[-1]["hash"]

    source = data["source"]
    session = source["session"]
    if "/" in session or session in (".", ".."):
        raise RunFileError(f"{session!r}: not the name of a session")
    source_folder = records.parent / source["application"] / session
    source_seal = _sealed(source_folder)[-1]["hash"]
    if source_seal != source["seal"]:
        raise RunFileError(
            f"{source_folder}: its seal is {source_seal}, the run data file has {source['seal']}"
        )

    request = data["request"]
    request_bytes = committed_request(root, request["commit"], request["id"], request_folder(app))
    request_hash = hashlib.sha256(request_bytes).hexdigest()
    if request_hash != request["sha256"]:
        raise RunFileError(
            f"{request['id']}.toml at commit {request['commit']} has SHA-256 {request_hash}, "
            f"the run data file has {request['sha256']}"
        )
    with tempfile.TemporaryDirectory() as directory:
        copy = Path(directory) / f"{request['id']}.toml"
        copy.write_bytes(request_bytes)
        parsed = parse_request(copy, apps)
    if parsed.application != application:
        raise RunFileError(
            f"{request['id']}: the request is for {parsed.application}, the source is {application}"
        )

    judged = judge_record(folder, parsed, allowed_ids(data["setup"], source_folder))
    prompts = data["prompts"]
    run_file_data = {
        "format": FORMAT,
        "run": run_id,
        "setup": data["setup"],
        "request": request,
        "source": source,
        "record": {"seal": seal, "end": judged.end},
        "seed": data["seed"],
        "kiro": data["kiro"],
        "files": data["files"],
        "tools": data["tools"],
        "given": data["given"],
        "relied_on": {
            "ids": None if judged.relied.ids is None else list(judged.relied.ids),
            "problem": judged.relied.problem,
        },
        "result": judged.result,
        "first_in_range": judged.first_in_range,
        "last_trial": None
        if judged.last_trial is None
        else {"trial": judged.last_trial, "phase": judged.last_phase},
        "prompts": prompts,
        "continue_lines": sum(1 for prompt in prompts if prompt["kind"] == "continue"),
        "limits": limits_for(data["setup"]),
    }
    if VARIANT_FIELD in data:
        run_file_data[VARIANT_FIELD] = data[VARIANT_FIELD]
    text, sidecar_text = run_file_texts(run_file_data)
    scanner = Scanner.from_config([root / app.scan_sources for app in apps.values()], stop_list)

    temporary = run_file.with_name(f".{run_id}{RUN_FILE_SUFFIX}.tmp")
    temporary_sidecar = temporary.with_name(temporary.name + SIDECAR_SUFFIX)
    try:
        temporary.write_text(text, encoding="utf-8", newline="")
        temporary_sidecar.write_text(sidecar_text, encoding="utf-8", newline="")
        findings = scanner.scan_record(folder)
        findings += [replace(f, file=str(run_file)) for f in scanner.scan_file(temporary)]
        if findings:
            listed = "\n".join(str(finding) for finding in findings)
            raise RunFileError(f"the blind scan finds items; no run file was written:\n{listed}")
        os.replace(temporary_sidecar, sidecar)
        os.replace(temporary, run_file)
    finally:
        temporary.unlink(missing_ok=True)
        temporary_sidecar.unlink(missing_ok=True)
    return run_file


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="bfs-run-file", description="Write the run file of a sealed run record."
    )
    parser.add_argument("run_id", help="the run id, <request>-<spec|none|record>-<n>")
    parser.add_argument(
        "--sessions",
        required=True,
        help="the records folder of the run, relative to the repository root: sessions/build-from-spec "
        "for a production run",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        require_repository_root()
        root = Path.cwd()
        written = write_run_file(args.run_id, APPS, root / STOP_LIST, root, root / args.sessions)
    except (AppError, JudgeError, ReliedError, RequestError, RunFileError, ScanError) as error:
        sys.exit(f"bfs-run-file: {error}")
    print(f"bfs-run-file: wrote {written}")
