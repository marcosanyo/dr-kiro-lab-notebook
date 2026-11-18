"""Request file: parse, print, and check it before commit (bfs-check-request, design 3.2).

A request says what the reader must do, in words, and gives the pass ranges that decide it.
The file is TOML with
`id`, `application`, `words` and one or more `[[pass]]` tables. Nothing here runs the reader.
"""

import argparse
import functools
import importlib
import json
import math
import re
import sys
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from bench.record.chain import VerifyError, verify
from bench.scan.scan import Finding, Scanner

from build_from_spec.apps import APPS, App, AppError, app_for, require_repository_root
from build_from_spec.judge import counted_trials

STOP_LIST = Path(".kiro/blind-scan/stop-list.txt")
TOP_FIELDS = ("id", "application", "words", "pass")
PASS_FIELDS = ("measurement", "range")
ID_PATTERN = re.compile(r"[a-z0-9-]+")


@dataclass(frozen=True)
class PassRange:
    measurement: str
    low: float
    high: float


@dataclass(frozen=True)
class Request:
    id: str
    application: str
    words: str
    passes: tuple[PassRange, ...]


class RequestError(Exception):
    """A request file that breaks Requirement 2.2, or a source record that cannot be checked.
    The message names the file and the field or line."""


def _refusal(path: Path, where: str, problem: str) -> RequestError:
    return RequestError(f"{path}: {where}: {problem}")


@functools.cache
def _scalar_names(adapter: str) -> frozenset[str]:
    """The scalar measurements of an application, from its adapter's declaration (Requirement 2.2)."""
    module_name, _, attribute = adapter.partition(":")
    factory = getattr(importlib.import_module(module_name), attribute)
    declaration = factory().declaration()
    return frozenset(m.name for m in declaration.measurements if m.kind == "scalar")


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def parse_request(path: Path, apps: Mapping[str, App]) -> Request:
    """Read and check a request file, in the order of Requirement 2.2. Refuse, naming the file
    and the field."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise _refusal(path, "file", f"not valid TOML: {error}") from error
    for field in TOP_FIELDS:
        if field not in data:
            raise _refusal(path, field, "missing field")
    for key in sorted(set(data) - set(TOP_FIELDS)):
        raise _refusal(path, key, "extra field at the top level")
    request_id, application, words = data["id"], data["application"], data["words"]
    for field, value in (("id", request_id), ("application", application), ("words", words)):
        if not isinstance(value, str):
            raise _refusal(path, field, "must be text")
    if not ID_PATTERN.fullmatch(request_id):
        raise _refusal(path, "id", f"{request_id!r} does not match [a-z0-9-]+")
    if request_id != path.stem:
        raise _refusal(path, "id", f"{request_id!r} differs from the file name {path.stem!r}")
    if application not in apps:
        raise _refusal(path, "application", f"no adapter is known to build-from-spec for {application!r}")
    if not words.strip():
        raise _refusal(path, "words", "is empty")
    tables = data["pass"]
    if not isinstance(tables, list) or not tables or not all(isinstance(t, dict) for t in tables):
        raise _refusal(path, "pass", "needs one or more [[pass]] tables")
    scalars = _scalar_names(apps[application].adapter)
    seen: set[str] = set()
    passes = []
    for number, table in enumerate(tables, start=1):
        where = f"pass[{number}]"
        for field in PASS_FIELDS:
            if field not in table:
                raise _refusal(path, f"{where}.{field}", "missing field")
        for key in sorted(set(table) - set(PASS_FIELDS)):
            raise _refusal(path, f"{where}.{key}", "extra field in a [[pass]] table")
        measurement, bounds = table["measurement"], table["range"]
        if not isinstance(measurement, str):
            raise _refusal(path, f"{where}.measurement", "must be text")
        if not isinstance(bounds, list) or len(bounds) != 2 or not all(_is_number(b) for b in bounds):
            raise _refusal(path, f"{where}.range", "must be [low, high] with two numbers")
        low, high = float(bounds[0]), float(bounds[1])
        if not (math.isfinite(low) and math.isfinite(high)):
            raise _refusal(path, f"{where}.range", "bounds must be finite")
        if not low < high:
            raise _refusal(path, f"{where}.range", f"low {low!r} must be strictly below high {high!r}")
        if measurement in seen:
            raise _refusal(path, f"{where}.measurement", f"{measurement!r} is named twice")
        if measurement not in scalars:
            names = ", ".join(sorted(scalars))
            raise _refusal(
                path,
                f"{where}.measurement",
                f"{measurement!r} is not a scalar measurement of {application}; its scalars are {names}",
            )
        seen.add(measurement)
        passes.append(PassRange(measurement, low, high))
    return Request(request_id, application, words, tuple(passes))


def _toml_string(text: str) -> str:
    """A TOML basic string. JSON escapes are valid TOML escapes, except that TOML also forbids a raw DEL."""
    return json.dumps(text, ensure_ascii=False).replace("\x7f", "\\u007f")


def print_request(request: Request) -> str:
    """The request as a request file (Requirement 2.4). Bounds are written with repr, which reads
    back exactly."""
    lines = [
        f"id = {_toml_string(request.id)}",
        f"application = {_toml_string(request.application)}",
        f"words = {_toml_string(request.words)}",
    ]
    for p in request.passes:
        lines += [
            "",
            "[[pass]]",
            f"measurement = {_toml_string(p.measurement)}",
            f"range = [{p.low!r}, {p.high!r}]",
        ]
    return "\n".join(lines) + "\n"


def inside(value: float, p: PassRange) -> bool:
    """Inclusive at both ends (Requirement 2.3)."""
    return p.low <= value <= p.high


def source_trials_inside(request: Request, record: Path) -> list[str]:
    """Ids, in log order, of the counted trials of a sealed source record that are inside every pass range
    (Requirement 3.5, Decision 19). A not-measured value is outside. A named measurement missing from a trial
    fails the check, because the bench never records such a trial."""
    try:
        entries = verify(record, sealed=True)
    except VerifyError as error:
        raise RequestError(f"{record}: the source record does not verify: {error}") from error
    found = []
    for body in counted_trials(entries):
        measured = body["measurements"]
        inside_all = True
        for p in request.passes:
            if p.measurement not in measured:
                raise RequestError(
                    f"{record}: trial {body['trial']} has no measurement {p.measurement!r} "
                    "named by the request"
                )
            value = measured[p.measurement]
            if isinstance(value, dict):  # a not-measured outcome
                inside_all = False
            elif _is_number(value):
                inside_all = inside_all and inside(float(value), p)
            else:
                raise RequestError(
                    f"{record}: trial {body['trial']} measurement {p.measurement!r} is not a scalar value"
                )
        if inside_all:
            found.append(body["trial"])
    return found


def _field_line(path: Path, lines: list[str], field: str) -> int:
    pattern = re.compile(rf"^\s*{field}\s*=")
    for number, line in enumerate(lines, start=1):
        if pattern.match(line):
            return number
    raise _refusal(path, field, "no line starts with this field")


def _blind_findings(path: Path, request: Request, app: App, stop_list: Path) -> list[Finding]:
    """The id and the words, scanned at the builder level (Requirement 3.1)."""
    scanner = Scanner.from_config([Path(app.scan_sources)], stop_list)
    lines = path.read_text(encoding="utf-8").splitlines()
    findings: list[Finding] = []
    for field in ("id", "words"):
        line = _field_line(path, lines, field)
        findings += scanner.scan_text(getattr(request, field), "builder", str(path), line)
    return findings


def _folder_refusal(path: Path, app: App) -> None:
    """The rehearsal's request folder is for the rehearsal application only, and that application's requests
    are only there (apps.request_folder). Refuse, naming the file, when the two do not match."""
    in_rehearsal = path.resolve().parent.parts[-2:] == ("rehearsal", "requests")
    if in_rehearsal and not app.rehearsal:
        raise _refusal(path, "application", f"the rehearsal request folder is not for {app.name}")
    if app.rehearsal and not in_rehearsal:
        raise _refusal(
            path,
            "application",
            f"{app.name} is the rehearsal application; its requests go in rehearsal/requests",
        )


def check_request(path: Path, source: Path, apps: Mapping[str, App], stop_list: Path) -> list[str]:
    """Every problem with a request, as printable lines. Empty when the check passes (Requirement 3.4).

    Format errors and the source check raise RequestError. The blind scan returns its findings. Nothing is
    written. The source is a required argument: no default (Requirement 3.5).
    """
    request = parse_request(path, apps)
    app = app_for(request.application, apps)
    _folder_refusal(path, app)
    lines = [str(f) for f in _blind_findings(path, request, app, stop_list)]
    for trial in source_trials_inside(request, source):
        lines.append(f"{path}: trial {trial} of {source} has every named measurement inside its pass range")
    return lines


def check_main(argv: list[str] | None = None) -> None:
    """bfs-check-request <request-file> --source <record>.

    Exit 0 with "no findings", or exit 1 with each finding.
    """
    parser = argparse.ArgumentParser(prog="bfs-check-request", description="Check a request before commit.")
    parser.add_argument("request", type=Path, help="the request file, build-from-spec/requests/<id>.toml")
    parser.add_argument("--source", type=Path, required=True, help="the sealed source session record")
    args = parser.parse_args(argv)
    try:
        require_repository_root()
        findings = check_request(args.request, args.source, APPS, Path(STOP_LIST))
    except (RequestError, AppError, VerifyError) as error:
        sys.exit(f"bfs-check-request: {error}")
    if findings:
        print("\n".join(findings))
        sys.exit(1)
    print("no findings")
