"""Earlier runs of one request (design 3.12; Requirements 7.4, 7.8, 14.6).

A run id is `<request>-<setup>-<n>`. The run records and run files of one application sit in
`<records>/<application>/`, where `<records>` is the records folder of the run: `sessions/build-from-spec`
for production runs (`RECORDS`), and a folder under `apps.REHEARSAL_ROOT` for a rehearsal.

The earlier runs that the run script compares a new run with are only the counted ones, read from `RECORDS`
(`counted_runs_of_request`, K32). Rehearsal records are never read as earlier runs.

A run record is the sealed folder named by its run id. Its run file is `<run id>.run.json`, and the author
sidecar of that run file is `<run id>.run.json.authors.json`.

Nothing here reads a run file's content. The callers read the files they need with `runfile.read_run_file`.
"""

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NamedTuple

from bench.scan.levels import SIDECAR_SUFFIX

from build_from_spec.apps import PRODUCTION_RECORDS

# The run id of design 3.12. The request id is matched first and the setup and number at the end, so the
# request id is unambiguous even when it contains hyphens.
RUN_ID = re.compile(r"(?P<request>[a-z0-9-]+)-(?P<setup>spec|none|record)-(?P<n>[1-9][0-9]*)")
RECORDS = PRODUCTION_RECORDS  # the production records folder, relative to the root
RUN_FILE_SUFFIX = ".run.json"


class RunsError(Exception):
    """The runs of an application do not add up: a folder, file or name is not of the expected kind, or a run
    record and its run file are not paired. The message names the path."""


class RunId(NamedTuple):
    request: str
    setup: str
    number: int


def run_id_parts(run_id: str) -> RunId:
    """The request id, setup and number of a run id. Refuse, naming the id, when it is not of the form."""
    found = RUN_ID.fullmatch(run_id)
    if found is None:
        raise RunsError(f"{run_id!r} is not a run id of the form <request>-<spec|none|record>-<n>")
    return RunId(found.group("request"), found.group("setup"), int(found.group("n")))


def records_folder(records: Path, application: str) -> Path:
    """`<records>/<application>/`."""
    return Path(records) / application


def application_folders(records: Path) -> list[str]:
    """The application folders under the records folder, sorted. Refuse any file there, naming it."""
    base = Path(records)
    if not base.is_dir():
        return []
    names = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            raise RunsError(f"{child}: only application folders belong in {base}")
        names.append(child.name)
    return names


def run_records(records: Path, application: str) -> dict[str, Path]:
    """The run record folders of an application, by run id. Refuse any folder whose name is not a run id."""
    folder = records_folder(records, application)
    if not folder.is_dir():
        return {}
    found = {}
    for child in sorted(folder.iterdir()):
        if child.is_dir():
            if RUN_ID.fullmatch(child.name) is None:
                raise RunsError(f"{child}: a run record folder is named by its run id")
            found[child.name] = child
    return found


def run_files(records: Path, application: str) -> dict[str, Path]:
    """The run files of an application, by run id. Refuse any other file, except a sidecar of a run file."""
    folder = records_folder(records, application)
    if not folder.is_dir():
        return {}
    found: dict[str, Path] = {}
    sidecars = []
    for child in sorted(folder.iterdir()):
        if child.is_dir():
            continue
        if child.name.endswith(SIDECAR_SUFFIX):
            sidecars.append(child)
            continue
        if not child.name.endswith(RUN_FILE_SUFFIX):
            raise RunsError(f"{child}: not a run file, a run record or the sidecar of a run file")
        run_id = child.name[: -len(RUN_FILE_SUFFIX)]
        if RUN_ID.fullmatch(run_id) is None:
            raise RunsError(f"{child}: a run file is named by its run id")
        found[run_id] = child
    run_file_names = {path.name for path in found.values()}
    for sidecar in sidecars:
        if sidecar.name[: -len(SIDECAR_SUFFIX)] not in run_file_names:
            raise RunsError(f"{sidecar}: a sidecar with no run file beside it")
    return found


def paired_runs(records: Path, application: str) -> dict[str, Path]:
    """The run files of an application, by run id, once every run record and run file is paired (Requirement
    7.8). Refuse, naming the run record that has no run file, or the run file that has no run record."""
    found_records = run_records(records, application)
    files = run_files(records, application)
    for run_id, folder in found_records.items():
        if run_id not in files:
            expected = records_folder(records, application) / f"{run_id}{RUN_FILE_SUFFIX}"
            raise RunsError(
                f"{folder}: the run record has no run file {expected}; "
                "the run file is written once the run is sealed"
            )
    for run_id, path in files.items():
        if run_id not in found_records:
            raise RunsError(f"{path}: the run file has no run record of the same run id")
    return files


def runs_of_request(records: Path, application: str, request_id: str) -> dict[str, Path]:
    """The paired run files of one request in one application, by run id."""
    return {
        run_id: path
        for run_id, path in paired_runs(records, application).items()
        if run_id_parts(run_id).request == request_id
    }


def counted_runs_of_request(root: Path, application: str, request_id: str) -> dict[str, Path]:
    """The paired run files of one request that count: those under the production records folder `RECORDS`,
    whatever the records folder of the run being started (K32). A rehearsal run is compared with neither a
    rehearsal run nor a counted run, so this is the only source of earlier runs for the run script."""
    return runs_of_request(Path(root) / RECORDS, application, request_id)


def _flat(run: Mapping[str, Any]) -> dict[str, object]:
    """The values that must match across the runs of one request, by their flat name (Requirement 14.6)."""
    flat: dict[str, object] = {
        "seed": run["seed"],
        "request.id": run["request"]["id"],
        "request.commit": run["request"]["commit"],
        "request.sha256": run["request"]["sha256"],
        "source.application": run["source"]["application"],
        "source.session": run["source"]["session"],
        "source.seal": run["source"]["seal"],
        "kiro.version": run["kiro"]["version"],
        "kiro.model": run["kiro"]["model"],
        "kiro.effort": run["kiro"]["effort"],
    }
    for where, digest in run["files"].items():
        flat[f"files[{where}]"] = digest
    for name, digest in run["tools"].items():
        flat[f"tools[{name}]"] = digest
    return flat


def differences(
    first_label: str, first: Mapping[str, Any], second_label: str, second: Mapping[str, Any]
) -> list[str]:
    """Each field in which two runs of one request differ, as a line that names both and both values.

    The same test serves two checks: the run script compares a planned run data file with the earlier run
    files before it starts (Requirement 7.4), and `bfs-check-runs` compares run files with each other
    (Requirement 14.6). Both files have the same fields, so the function reads both the same way. The fields
    are the seed, the request file's commit and SHA-256, the source session and its seal, the Kiro CLI
    version, model and effort, every file outside `given/` and every tool description. A field that is absent
    on one side is a difference."""
    left, right = _flat(first), _flat(second)
    lines = []
    for name in sorted(set(left) | set(right)):
        if left.get(name, "(absent)") != right.get(name, "(absent)"):
            lines.append(
                f"{first_label} and {second_label} differ in {name}: "
                f"{left.get(name, '(absent)')!r} vs {right.get(name, '(absent)')!r}"
            )
    return lines
