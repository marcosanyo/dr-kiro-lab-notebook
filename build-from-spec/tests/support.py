"""Generators and writers shared by the property tests (tests/properties/)."""

import json
import shutil
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, NamedTuple

from bench.record.chain import BLOB_DIR, LOG_NAME
from bench.record.store import Store
from hypothesis import strategies as st

from build_from_spec.relied import format_ids
from build_from_spec.request import PassRange, Request

SCALARS = ("x", "y", "heading")  # the scalar measurements of body-lab (its declaration)

request_ids = st.from_regex(r"\A[a-z0-9-]{1,40}\Z", fullmatch=True)
request_words = st.text(min_size=1, max_size=200).filter(lambda text: text.strip() != "")


@st.composite
def requests(draw) -> Request:
    """A valid request for body-lab: distinct scalar measurements, finite bounds with low < high."""
    names = draw(st.lists(st.sampled_from(SCALARS), min_size=1, max_size=3, unique=True))
    passes = []
    for name in names:
        # high is drawn above low, so no draw is thrown away (a filter here made hypothesis give up).
        low = draw(st.floats(min_value=-1e6, max_value=1e6, exclude_max=True, allow_nan=False))
        high = draw(st.floats(min_value=low, max_value=1e6, exclude_min=True, allow_nan=False))
        passes.append(PassRange(name, low, high))
    return Request(draw(request_ids), "body-lab", draw(request_words), tuple(passes))


def literal(text: str) -> str:
    """A TOML basic string for text: JSON escapes are TOML escapes, and DEL is written as an escape."""
    return json.dumps(text, ensure_ascii=False).replace("\x7f", "\\u007f")


def base_spec(request: Request) -> dict:
    """The request as TOML literals, in the fields and order of a request file. Mutations edit this dict."""
    return {
        "id": literal(request.id),
        "application": literal(request.application),
        "words": literal(request.words),
        "pass": [
            {"measurement": literal(p.measurement), "range": f"[{p.low!r}, {p.high!r}]"}
            for p in request.passes
        ],
    }


def render(spec: dict) -> str:
    """Write a spec dict as request-file text. Keys missing from the dict are missing from the file."""
    lines = [f"{key} = {value}" for key, value in spec.items() if key != "pass"]
    for table in spec.get("pass", []):
        lines += ["", "[[pass]]"] + [f"{key} = {value}" for key, value in table.items()]
    return "\n".join(lines) + "\n"


# A relied-on id: any run of characters other than a comma or whitespace, and not `none` (which stands alone).
relied_ids = st.from_regex(r"\A[^,\s]{1,12}\Z", fullmatch=True).filter(
    lambda identifier: identifier != "none"
)


@st.composite
def relied_id_tuples(draw) -> tuple[str, ...]:
    """Either `("none",)` or distinct ids that do not include `none`."""
    if draw(st.booleans()):
        return ("none",)
    return tuple(draw(st.lists(relied_ids, min_size=1, max_size=6, unique=True)))


# ---- Run records for the result program (judge.py, properties 4-6) ----

ALLOWED_IDS = frozenset({"none", "R1", "R2"})  # what a source of setup `spec` would allow here
PHASES = ("map", "best", "probe")
CATEGORIES = ("no-h1", "no-line", "bad-syntax", "unknown-id", "late", "valid")
VALID_LINES = (format_ids(("none",)), format_ids(("R1",)), format_ids(("R1", "R2")))
BAD_LINES = ("# relies on: none, R1", "# relies on: R1,,R2", "# relies on: R1, R1", "# relies on:R1")
# The problem that the result program must report for each way of building H1 (Requirement 10.4).
EXPECTED_PROBLEM = {
    "no-h1": "no-h1",
    "no-line": "no-line",
    "bad-syntax": "bad-syntax",
    "unknown-id": "unknown-id",
    "late": "late",
    "valid": None,
}
LOST = {"not_measured": "lost", "reason": "the body did not settle"}


class Case(NamedTuple):
    """A run record in memory, with what the generator built it from (the oracle's inputs)."""

    request: Request
    entries: list[dict[str, Any]]
    frozen: str
    category: str  # a key of EXPECTED_PROBLEM: how H1 was built
    counted: tuple[str, ...]  # the trial ids whose experiment has a counting snapshot, in order
    values: dict[str, dict[str, Any]]  # trial id -> the measurements as recorded


def h1_frozen(first_line: str | None) -> str:
    """H1's frozen part: a prediction block whose first line is `first_line`, or has no such line."""
    block = f"{first_line}\n" if first_line is not None else ""
    return f"### H1: about\n\nWHEN a, THE b SHALL c.\n\n```prediction\n{block}[[prediction]]\n```\n"


def value_of(request: Request):
    """A recorded value of a scalar measurement: a number, often one of the request's bounds, or `lost`."""
    bounds = [bound for p in request.passes for bound in (p.low, p.high)]
    number = st.one_of(st.sampled_from(bounds), st.floats(min_value=-1e6, max_value=1e6, allow_nan=False))
    return st.one_of(number, number, st.just(LOST))


def in_range_by_oracle(measurements: dict[str, Any], request: Request) -> bool:
    """Requirements 2.3, 15.4, written apart from judge.py: every named value is a number inside its range."""
    for p in request.passes:
        value = measurements[p.measurement]
        if isinstance(value, dict) or not (p.low <= value <= p.high):
            return False
    return True


@st.composite
def judge_cases(draw, categories: tuple[str, ...] = CATEGORIES) -> Case:
    """A run record with H1 built in one of `categories`, and random experiments, trials, refusals,
    bench failures (an experiment without its counting snapshot), phases and end."""
    request = draw(requests())
    category = draw(st.sampled_from(categories))
    blocks: list[list[tuple[str, dict[str, Any]]]] = []
    counted: list[str] = []
    values: dict[str, dict[str, Any]] = {}
    number = 0
    for experiment in range(1, draw(st.integers(min_value=1, max_value=3)) + 1):
        trial_ids = []
        block: list[tuple[str, dict[str, Any]]] = []
        for _ in range(draw(st.integers(min_value=0, max_value=3))):
            number += 1
            tid = f"T{number}"
            measurements = {name: draw(value_of(request)) for name in SCALARS}
            values[tid] = measurements
            trial_ids.append(tid)
            block.append(
                ("trial", {"trial": tid, "experiment": f"E{experiment}", "measurements": measurements})
            )
        experiment_body = {
            "experiment": f"E{experiment}",
            "hypothesis": "H1",
            "phase": draw(st.sampled_from(PHASES)),
            "trials": trial_ids,
        }
        block = [("experiment", experiment_body), *block]  # the experiment entry comes before its trials
        if draw(st.booleans()):  # the run ran: its snapshot counts its trials
            block.append(("snapshot", {"for": "experiment", "experiment": f"E{experiment}", "files": {}}))
            counted += trial_ids
        if draw(st.booleans()):
            block.append(("refusal", {"action": "experiment", "given": {}, "message": "refused"}))
        blocks.append(block)

    if category == "valid":
        first_line: str | None = draw(st.sampled_from(VALID_LINES))
    elif category == "unknown-id":
        first_line = "# relies on: R9"
    elif category == "bad-syntax":
        first_line = draw(st.sampled_from(BAD_LINES))
    elif category == "no-line":
        first_line = None
    else:  # no-h1 and late: the line itself is valid, the order or the registration is wrong
        first_line = draw(st.sampled_from(VALID_LINES))
    register = ("register", {"hypothesis": "H1", "frozen": {"blob": "0" * 64}})
    flat = [entry for block in blocks for entry in block]
    if category == "no-h1":
        ordered = flat
    elif category == "late":  # H1 is registered after the first experiment entry (Requirement 10.4)
        ordered = blocks[0] + [register] + flat[len(blocks[0]) :]
    else:
        ordered = [register] + flat
    end = draw(st.sampled_from(("ended", "stopped")))
    ordered.append(("seal", {"end": end, "budget_remaining": 0, "reason": "ended"}))
    entries = [{"seq": n, "kind": kind, "body": body} for n, (kind, body) in enumerate(ordered)]
    return Case(request, entries, h1_frozen(first_line), category, tuple(counted), values)


# ---- Sealed records written by the bench's Store (reduced copy tests, properties 7 and 8) ----


def seal_record(folder: Path, build: Callable[[Store], Sequence[tuple[str, dict[str, Any]]]]) -> Path:
    """Write a sealed record at `folder`: the entries `build` appends, then one seal entry.

    `build` stores blobs with `Store.put_blob` and returns the (kind, body) pairs that reference
    them. As the bench does when it seals, only `log.jsonl` and `blobs/` are copied to `folder`;
    the state folder is removed."""
    staging = folder.parent / f".{folder.name}.state"
    store = Store.create(staging)
    try:
        for kind, body in build(store):
            store.append(kind, body)
        store.append("seal", {"end": "stopped", "budget_remaining": 0, "reason": "test"})
    finally:
        store.close()
    folder.mkdir()
    shutil.copy2(staging / LOG_NAME, folder / LOG_NAME)
    shutil.copytree(staging / BLOB_DIR, folder / BLOB_DIR)
    shutil.rmtree(staging)
    return folder
