"""Hypothesis blocks in Dr. Kiro's `requirements.md` (Requirements 6.1-6.3, 6.6-6.8, design 5.1).

A hypothesis starts at a level-3 heading `### H<n>` (optionally `: title`) and runs to the next level-1
to level-3 heading outside a code fence. Its frozen part is the heading line, the statement, and the
fenced block with the info string `prediction` that follows the statement, fences included, with line
endings normalised to `\\n`. Text after the closing fence is free (notes and results) and is never part
of the frozen part.
"""

import math
import re
import tomllib
from dataclasses import dataclass

from bench.adapter import Declaration, FunctionKnob, NumberKnob
from bench.core import ids
from bench.core.outcome import BenchText, Message, Quote, RefusalError, Span
from bench.specfiles.ears import ears_shape

LABELS = ("inside", "new-combination", "outside", "not-comparable")
PREDICTION_KEYS = frozenset({"id", "measurement", "range", "label", "when"})

_HEADING = re.compile(r"(#{1,6})\s+(.*?)\s*#*\s*")
_HYPOTHESIS_HEADING = re.compile(r"###\s+(H[1-9][0-9]*)(?::\s*(.*?))?\s*")
_FENCE = re.compile(r"(`{3,}|~{3,})\s*([^\s`]*)\s*.*")


class SpecRefusal(RefusalError):
    """A lab spec file does not meet a lab rule."""


def normalise(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


@dataclass(frozen=True)
class Prediction:
    local_id: str
    global_id: str
    measurement: str
    low: float
    high: float
    label: str
    when: dict[str, float]
    line: int


@dataclass(frozen=True)
class Hypothesis:
    id: str
    title: str
    statement: str
    frozen: str
    predictions: tuple[Prediction, ...]
    line: int


@dataclass(frozen=True)
class _Block:
    """The raw lines of one hypothesis block (1-based line numbers in the file)."""

    id: str
    title: str
    start: int  # heading line
    end: int  # last line of the block
    lines: tuple[str, ...]  # all lines of the file


def _blocks(text: str) -> list[_Block]:
    lines = tuple(normalise(text).split("\n"))
    found: list[tuple[str, str, int]] = []
    heading_lines: list[int] = []
    fence: str | None = None
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        fence_match = _FENCE.fullmatch(stripped)
        if fence is not None:
            if (
                fence_match
                and fence_match.group(1)[0] == fence[0]
                and len(fence_match.group(1)) >= len(fence)
            ) and not fence_match.group(2):
                fence = None
            continue
        if fence_match:
            fence = fence_match.group(1)
            continue
        heading = _HEADING.fullmatch(line)
        if heading and len(heading.group(1)) <= 3:
            heading_lines.append(number)
            hyp = _HYPOTHESIS_HEADING.fullmatch(line.rstrip())
            if hyp:
                found.append((hyp.group(1), hyp.group(2) or "", number))
    blocks = []
    for hid, title, start in found:
        later = [n for n in heading_lines if n > start]
        end = (later[0] - 1) if later else len(lines)
        blocks.append(_Block(hid, title, start, end, lines))
    return blocks


@dataclass(frozen=True)
class _Located:
    block: _Block
    statement: str
    fence_open: int
    fence_close: int

    @property
    def frozen(self) -> str:
        return "\n".join(self.block.lines[self.block.start - 1 : self.fence_close]) + "\n"


def _locate(block: _Block, file: str) -> _Located:
    """Find the statement and the prediction block. Raise SpecRefusal if there is no closed block."""
    lines = block.lines
    open_line: int | None = None
    for number in range(block.start + 1, block.end + 1):
        match = _FENCE.fullmatch(lines[number - 1].strip())
        if match:
            if match.group(2) == "prediction":
                open_line = number
            break
    if open_line is None:
        raise SpecRefusal(
            Message(
                (
                    BenchText(f"{file} line {block.start}: hypothesis "),
                    Quote(block.id, file, block.start),
                    BenchText(" has no ```prediction block directly after its statement"),
                )
            )
        )
    fence = _FENCE.fullmatch(lines[open_line - 1].strip())
    marker = fence.group(1) if fence else "```"
    for number in range(open_line + 1, block.end + 1):
        close = _FENCE.fullmatch(lines[number - 1].strip())
        if (
            close
            and close.group(1)[0] == marker[0]
            and len(close.group(1)) >= len(marker)
            and not close.group(2)
        ):
            statement = "\n".join(lines[block.start : open_line - 1]).strip()
            return _Located(block, statement, open_line, number)
    raise SpecRefusal(
        Message(
            (
                BenchText(f"{file} line {open_line}: the prediction block of "),
                Quote(block.id, file, block.start),
                BenchText(" is not closed before the next heading"),
            )
        )
    )


def frozen_parts(text: str) -> dict[str, list[str | None]]:
    """Every hypothesis id in the file with the frozen part of each block that has that id. A block without a
    closed prediction block has None. Used for the frozen check (6.6)."""
    out: dict[str, list[str | None]] = {}
    for block in _blocks(text):
        try:
            frozen: str | None = _locate(block, "requirements.md").frozen
        except SpecRefusal:
            frozen = None
        out.setdefault(block.id, []).append(frozen)
    return out


def frozen_status(text: str, hypothesis_id: str, recorded: str) -> str | None:
    """None if the frozen part in the file equals the recorded copy, else a short reason in bench words."""
    parts = frozen_parts(text).get(hypothesis_id, [])
    if not parts:
        return "is missing"
    if len(parts) > 1:
        return "appears more than once"
    if parts[0] != recorded:
        return "differs from the registered version"
    return None


def _refuse(file: str, line: int, *parts: str | Span) -> SpecRefusal:
    spans: list[Span] = [BenchText(f"{file} line {line}: ")]
    spans += [BenchText(p) if isinstance(p, str) else p for p in parts]
    return SpecRefusal(Message(tuple(spans)))


def _is_number(value: object) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _prediction_line(lines: tuple[str, ...], first: int, last: int, local_id: str, index: int) -> int:
    pattern = re.compile(rf"""\s*id\s*=\s*["']{re.escape(local_id)}["']\s*(#.*)?""")
    for number in range(first, last + 1):
        if pattern.fullmatch(lines[number - 1]):
            return number
    tables = [n for n in range(first, last + 1) if lines[n - 1].strip() == "[[prediction]]"]
    return tables[index] if index < len(tables) else first


def parse_hypothesis(text: str, hypothesis_id: str, decl: Declaration, file: str) -> Hypothesis:
    """Read one hypothesis for registration. Raise SpecRefusal naming the line and the problem (6.2, 6.3)."""
    blocks = [b for b in _blocks(text) if b.id == hypothesis_id]
    if not blocks:
        raise SpecRefusal(
            Message(
                (
                    BenchText("hypothesis "),
                    Quote(hypothesis_id, file, 1),
                    BenchText(f" is not in {file}; it needs a heading `### {hypothesis_id}: <title>`"),
                )
            )
        )
    if len(blocks) > 1:
        lines = ", ".join(str(b.start) for b in blocks)
        raise _refuse(
            file,
            blocks[1].start,
            "hypothesis ",
            Quote(hypothesis_id, file, blocks[1].start),
            f" has more than one heading (lines {lines})",
        )
    located = _locate(blocks[0], file)
    block = blocks[0]
    if ears_shape(located.statement) is None:
        raise _refuse(
            file,
            block.start + 1,
            "the statement must be one EARS sentence, such as "
            "`WHEN <condition>, THE <system> SHALL <response>.` with the keywords in capitals",
        )
    toml_lines = block.lines[located.fence_open : located.fence_close - 1]
    try:
        data = tomllib.loads("\n".join(toml_lines))
    except tomllib.TOMLDecodeError as error:
        raise _refuse(
            file,
            located.fence_open,
            "the prediction block is not valid TOML: ",
            Quote(str(error), file, located.fence_open),
        ) from error
    if set(data) != {"prediction"} or not isinstance(data["prediction"], list) or not data["prediction"]:
        raise _refuse(
            file, located.fence_open, "the prediction block must hold one or more [[prediction]] tables"
        )
    knobs = {k.name: k for k in decl.knobs}
    measurements = {m.name: m for m in decl.measurements}
    predictions: list[Prediction] = []
    seen: set[str] = set()
    for index, raw in enumerate(data["prediction"]):
        local = raw.get("id") if isinstance(raw, dict) else None
        line = (
            _prediction_line(block.lines, located.fence_open + 1, located.fence_close - 1, local, index)
            if isinstance(local, str)
            else located.fence_open
        )
        where = f"prediction {index + 1}"
        if not isinstance(raw, dict) or set(raw) != PREDICTION_KEYS:
            raise _refuse(
                file, line, f"{where} must have exactly the keys id, measurement, range, label and when"
            )
        if not isinstance(local, str) or not ids.is_local_prediction_id(local):
            raise _refuse(file, line, f'{where}: id must be P<n>, such as "P1"')
        if local in seen:
            raise _refuse(file, line, "prediction ", Quote(local, file, line), " is listed twice")
        seen.add(local)
        name = raw["measurement"]
        if not isinstance(name, str) or name not in measurements:
            shown = name if isinstance(name, str) else repr(name)
            raise _refuse(
                file,
                line,
                "measurement ",
                Quote(shown, file, line),
                " is not one of the declared measurements",
            )
        if measurements[name].kind != "scalar":
            raise _refuse(file, line, f"{name} is a series; predictions are on scalar measurements only")
        bounds = raw["range"]
        if not (
            isinstance(bounds, list)
            and len(bounds) == 2
            and all(_is_number(b) and math.isfinite(b) for b in bounds)
        ):
            raise _refuse(file, line, f"{local}: range must be [low, high] with two finite numbers")
        low, high = float(bounds[0]) + 0.0, float(bounds[1]) + 0.0
        if not low < high:
            raise _refuse(file, line, f"{local}: range is empty or reversed; low must be below high")
        label = raw["label"]
        if label not in LABELS:
            raise _refuse(file, line, f"{local}: label must be one of {', '.join(LABELS)}")
        when = raw["when"]
        if not isinstance(when, dict) or not when:
            raise _refuse(file, line, f"{local}: [prediction.when] must give at least one parameter value")
        conditions: dict[str, float] = {}
        for key, value in when.items():
            if not key.isidentifier():
                raise _refuse(
                    file, line, f"{local}: parameter ", Quote(key, file, line), " is not a valid name"
                )
            if isinstance(knobs.get(key), FunctionKnob):
                raise _refuse(file, line, f"{local}: {key} is a function-of-time knob, not a parameter")
            if not (_is_number(value) and math.isfinite(value)):
                raise _refuse(
                    file, line, f"{local}: parameter ", Quote(key, file, line), " needs a finite number"
                )
            knob = knobs.get(key)
            if isinstance(knob, NumberKnob) and not knob.low <= value <= knob.high:
                raise _refuse(
                    file, line, f"{local}: {key} = {value!r} is outside [{knob.low!r}, {knob.high!r}]"
                )
            conditions[key] = float(value) + 0.0
        predictions.append(
            Prediction(
                local, ids.prediction_id(hypothesis_id, local), name, low, high, label, conditions, line
            )
        )
    return Hypothesis(
        id=hypothesis_id,
        title=block.title,
        statement=" ".join(located.statement.split()),
        frozen=located.frozen,
        predictions=tuple(predictions),
        line=block.start,
    )
