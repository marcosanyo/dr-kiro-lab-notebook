"""The `## Discovered spec` table at the end of Dr. Kiro's `design.md` (Requirement 12, design 5.2).

The status of each rule must agree with the record. The checks are pure functions over an `Evidence` summary
of the record, so they can be tested directly and from the session state machine.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from bench.core import ids
from bench.core.outcome import BenchText, Message, Quote, Span

COLUMNS = ("id", "rule", "scope", "experiments", "predictions", "status", "replaced by")
STATUSES = ("observed", "validated", "partly", "rejected")
HEADING = "## Discovered spec"
UNTRIED = frozenset({"new-combination", "outside"})

_ROW_ID = re.compile(r"R[1-9][0-9]*")
_FENCE = re.compile(r"(`{3,}|~{3,}).*")
_SEPARATOR_CELL = re.compile(r":?-{3,}:?")


@dataclass(frozen=True)
class Evidence:
    """What the record says: the experiments that ran, and each registered prediction's outcome kind and
    condition class."""

    experiments: frozenset[str]
    predictions: Mapping[str, tuple[str, str]]


@dataclass(frozen=True)
class Row:
    line: int
    id: str
    rule: str
    scope: str
    experiments: tuple[str, ...]
    predictions: tuple[str, ...]
    status: str
    replaced_by: str


@dataclass(frozen=True)
class Table:
    rows: tuple[Row, ...]


def _message(file: str, line: int, *parts: str | Span) -> Message:
    spans: list[Span] = [BenchText(f"{file} line {line}: ")]
    spans += [BenchText(p) if isinstance(p, str) else p for p in parts]
    return Message(tuple(spans))


def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", body)]


def _list(cell: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in cell.split(",")) if cell.strip() else ()


class TableError(Exception):
    def __init__(self, message: Message) -> None:
        super().__init__(message.plain())
        self.message = message


def parse_table(text: str, file: str) -> Table:
    """Find and parse the table. Raise TableError naming the line if it is missing or malformed (12.1)."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    level2: list[int] = []
    fence: str | None = None
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        match = _FENCE.fullmatch(stripped)
        if fence is not None:
            if match and match.group(1)[0] == fence[0] and stripped.strip("`~") == "":
                fence = None
            continue
        if match:
            fence = match.group(1)
            continue
        if re.fullmatch(r"##\s+.*", line.rstrip()) and not line.startswith("###"):
            level2.append(number)
    end = len(lines)
    if not level2 or lines[level2[-1] - 1].rstrip() != HEADING:
        where = level2[-1] if level2 else 1
        raise TableError(_message(file, where, f"design.md must end with a `{HEADING}` section"))
    start = level2[-1]
    table_lines = [n for n in range(start + 1, end + 1) if lines[n - 1].strip().startswith("|")]
    if not table_lines:
        raise TableError(_message(file, start, f"the `{HEADING}` section has no table"))
    first = table_lines[0]
    last = first
    while last + 1 <= end and lines[last].strip().startswith("|"):
        last += 1
    for n in range(last + 1, end + 1):
        if lines[n - 1].strip():
            raise TableError(
                _message(file, n, "nothing but white space may follow the discovered spec table")
            )
    header = [c.lower() for c in _cells(lines[first - 1])]
    if tuple(header) != COLUMNS:
        raise TableError(_message(file, first, "the table columns must be: " + " | ".join(COLUMNS)))
    if last < first + 1 or not all(_SEPARATOR_CELL.fullmatch(c) for c in _cells(lines[first])):
        raise TableError(
            _message(file, first + 1, "the header row must be followed by a |---| separator row")
        )
    rows: list[Row] = []
    for n in range(first + 2, last + 1):
        cells = _cells(lines[n - 1])
        if len(cells) != len(COLUMNS):
            raise TableError(
                _message(file, n, f"a row needs {len(COLUMNS)} cells, this one has {len(cells)}")
            )
        rid, rule, scope, experiments, predictions, status, replaced = cells
        rows.append(Row(n, rid, rule, scope, _list(experiments), _list(predictions), status, replaced))
    if not rows:
        raise TableError(_message(file, first, "the discovered spec table has no rules"))
    return Table(tuple(rows))


def check_row(row: Row, evidence: Evidence, row_ids: frozenset[str], file: str) -> list[Message]:
    """Every problem with one row (12.2-12.4)."""
    problems: list[Message] = []

    def problem(*parts: str | Span) -> None:
        problems.append(
            _message(file, row.line, "row ", Quote(row.id or "(no id)", file, row.line), ": ", *parts)
        )

    if not _ROW_ID.fullmatch(row.id):
        problem("the id must be R<n>, such as R1")
    for column, value in (("rule", row.rule), ("scope", row.scope), ("status", row.status)):
        if not value:
            problem(f"the {column} cell is empty")
    if not row.experiments:
        problem("the experiments cell is empty; a rule cites at least one experiment")
    for eid in row.experiments:
        valid = re.fullmatch(r"E[1-9][0-9]*", eid) is not None
        if not valid or eid not in evidence.experiments:
            problem("experiment ", Quote(eid, file, row.line), " is not in the record")
    cited: list[tuple[str, str]] = []
    for pid in row.predictions:
        try:
            ids.parse_prediction_id(pid)
        except ValueError:
            problem("prediction ", Quote(pid, file, row.line), " is not an id like H1.P1")
            continue
        if pid not in evidence.predictions:
            problem("prediction ", Quote(pid, file, row.line), " is not in the record")
            continue
        cited.append(evidence.predictions[pid])
    if row.status and row.status not in STATUSES:
        problem("status must be one of " + ", ".join(STATUSES))
    if row.status != "rejected" and row.replaced_by:
        problem("only a rejected rule names a replacement in `replaced by`")
    if problems:
        return problems

    kinds = [kind for kind, _ in cited]
    hits = kinds.count("hit")
    misses = kinds.count("miss")
    untried_hits = sum(1 for kind, cls in cited if kind == "hit" and cls in UNTRIED)
    summary = _summary(row, evidence, file)
    if row.status == "observed":
        # Under-claiming is fine: hits of any class, not-run and not-checkable predictions are allowed.
        if misses:
            problem("an observed rule cannot cite a missed prediction (", summary, ")")
    elif row.status == "validated":
        if not cited:
            problem("a validated rule cites at least one prediction")
        elif hits != len(cited):
            problem("every prediction a validated rule cites must be a hit (", summary, ")")
        elif untried_hits == 0:
            problem(
                "a validated rule needs at least one hit that is a new combination or outside the tried "
                "range (",
                summary,
                ")",
            )
    elif row.status == "partly":
        if not (hits and misses):
            problem("a partly rule cites at least one hit and at least one miss (", summary, ")")
    elif row.status == "rejected":
        if not misses:
            problem("a rejected rule cites at least one miss (", summary, ")")
        if not row.replaced_by:
            problem("a rejected rule names the id of the rule that replaces it in `replaced by`")
        elif row.replaced_by == row.id or row.replaced_by not in row_ids:
            problem(
                "`replaced by` names ", Quote(row.replaced_by, file, row.line), ", which is not another row"
            )
    return problems


def _summary(row: Row, evidence: Evidence, file: str) -> Span:
    """The cited outcomes and condition classes. Prediction ids are Dr. Kiro's, so this is a quote."""
    parts = [f"{pid}: {'/'.join(evidence.predictions[pid])}" for pid in row.predictions]
    return Quote("; ".join(parts) if parts else "no predictions cited", file, row.line)


def check_table(text: str, evidence: Evidence, file: str) -> list[Message]:
    """Every problem with the table in `design.md`. An empty list means ending the session is accepted."""
    try:
        table = parse_table(text, file)
    except TableError as error:
        return [error.message]
    problems: list[Message] = []
    seen: set[str] = set()
    for row in table.rows:
        if row.id in seen:
            problems.append(
                _message(file, row.line, "row id ", Quote(row.id, file, row.line), " is used twice")
            )
        seen.add(row.id)
    row_ids = frozenset(seen)
    for row in table.rows:
        problems += check_row(row, evidence, row_ids, file)
    return problems
