"""Experiment file structure, mode limits and computed inputs (Requirements 4-5, 7.4, design 7.1).

`prepare` covers the checks the session runs before the verdict gate: header, whitelist, PHASE and MODE,
PARAMS, TRIALS, the knob functions, and the mode limits. `compute` evaluates every trial and checks every
computed input. Both raise LangRefusal; nothing is clipped or filled in.
"""

import ast
import math
import re
from dataclasses import dataclass

from bench.adapter import Declaration, FunctionKnob, NumberKnob
from bench.lang.check import (
    RESERVED_NAMES,
    STRUCTURE_NAMES,
    LangRefusal,
    Source,
    function_names,
    parse_and_check,
)
from bench.lang.evaluate import Interpreter, Value
from bench.record.canonical import canonical_json
from bench.record.chain import sha256_hex

PHASES = ("map", "rules", "test", "best")
MODES = ("compare", "sweep")
COMPARE_VARIANTS = (1, 3)
SWEEP_POINTS = 6
SWEEP_PARAMETERS = (1, 2)

_HEADER = re.compile(r"#\s*(H[1-9][0-9]*)(?::\s*(.*?))?\s*")


@dataclass
class Prepared:
    """An experiment file that passed the structural checks, ready to evaluate."""

    src: Source
    hypothesis: str
    title: str
    phase: str
    mode: str
    params: tuple[str, ...]
    sweep: tuple[str, ...]
    rows: tuple[tuple[float, ...], ...]
    interpreter: Interpreter
    declaration: Declaration
    tree: ast.Module


@dataclass(frozen=True)
class ComputedTrial:
    params: dict[str, float]
    inputs: dict[str, float | tuple[float, ...]]
    key: str


@dataclass(frozen=True)
class Experiment:
    hypothesis: str
    title: str
    phase: str
    mode: str
    params: tuple[str, ...]
    sweep: tuple[str, ...]
    trials: tuple[ComputedTrial, ...]
    steps: int


def _number(value: Value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _clean(value: float) -> float:
    """The canonical float of a number: ints as floats, -0.0 as 0.0."""
    return float(value) + 0.0


def trial_key(inputs: dict[str, float | tuple[float, ...]]) -> str:
    """SHA-256 of the canonical JSON of the computed inputs (Requirement 7.4)."""
    return sha256_hex(canonical_json(inputs))


def _line_of(tree: ast.Module, name: str) -> int | None:
    for stmt in tree.body:
        target = stmt.targets[0] if isinstance(stmt, ast.Assign) else None
        if isinstance(target, ast.Name) and target.id == name:
            return stmt.lineno
    return None


def prepare(text: str, file: str, decl: Declaration, *, step_bound: int) -> Prepared:
    """Steps 4 and 5 of the run gate order (design 6.1). Raise LangRefusal on the first problem."""
    src = Source(file, text)
    first = src.lines[0] if src.lines else ""
    header = _HEADER.fullmatch(first)
    if header is None:
        raise src.refusal(1, "the first line must name the hypothesis, as `# H<n>: <title>`")
    tree = parse_and_check(src)
    interp = Interpreter(tree, src, step_bound)
    interp.run_module()
    g = interp.globals

    def need(name: str) -> Value:
        if name not in g:
            raise src.refusal(None, f"{name} is not set")
        return g[name]

    phase = need("PHASE")
    if phase not in PHASES:
        raise src.refusal(_line_of(tree, "PHASE"), f"PHASE must be one of {', '.join(PHASES)}")
    mode = need("MODE")
    if mode not in MODES:
        raise src.refusal(_line_of(tree, "MODE"), f"MODE must be one of {', '.join(MODES)}")

    params = tuple(need("PARAMS"))
    params_line = _line_of(tree, "PARAMS") or 1
    functions = function_names(tree)
    knobs = {k.name: k for k in decl.knobs}
    for p in params:
        if not p.isidentifier() or p in RESERVED_NAMES or p in STRUCTURE_NAMES or p == "t":
            raise src.refusal(params_line, "parameter ", src.name(p, params_line), " is not a valid name")
        if isinstance(knobs.get(p), FunctionKnob):
            raise src.refusal(params_line, f"{p} is a function-of-time knob; define it as def {p}(t, ...)")
        if p in functions:
            raise src.refusal(params_line, "parameter ", src.name(p, params_line), " is also a function")
    if len(set(params)) != len(params):
        raise src.refusal(params_line, "a parameter is listed twice in PARAMS")

    trials_line = _line_of(tree, "TRIALS")
    trials = need("TRIALS")
    if not isinstance(trials, list) or not all(isinstance(row, list) for row in trials):
        raise src.refusal(
            trials_line, "TRIALS must be a list of rows, one list of parameter values per trial"
        )
    rows: list[tuple[float, ...]] = []
    for number, row in enumerate(trials, start=1):
        if len(row) != len(params):
            raise src.refusal(
                trials_line, f"trial {number} has {len(row)} values, but PARAMS lists {len(params)}"
            )
        if not all(_number(v) and math.isfinite(v) for v in row):
            raise src.refusal(trials_line, f"trial {number}: every parameter value must be a finite number")
        rows.append(tuple(_clean(v) for v in row))

    _check_knob_functions(src, decl, params, functions, g)

    sweep: tuple[str, ...] = ()
    if mode == "compare":
        if "SWEEP" in g:
            raise src.refusal(_line_of(tree, "SWEEP"), "SWEEP is only used in sweep mode")
        low, high = COMPARE_VARIANTS
        if not low <= len(rows) <= high:
            raise src.refusal(
                trials_line, f"compare mode needs {low} to {high} variants, TRIALS has {len(rows)}"
            )
    else:
        sweep = tuple(need("SWEEP"))
        sweep_line = _line_of(tree, "SWEEP")
        low, high = SWEEP_PARAMETERS
        if not low <= len(sweep) <= high or len(set(sweep)) != len(sweep):
            raise src.refusal(sweep_line, f"SWEEP must name {low} or {high} different parameters")
        for name in sweep:
            if name not in params:
                raise src.refusal(
                    sweep_line, "SWEEP names ", src.name(name, sweep_line or 1), " not in PARAMS"
                )
        if len(rows) != SWEEP_POINTS:
            raise src.refusal(
                trials_line, f"sweep mode needs exactly {SWEEP_POINTS} points, TRIALS has {len(rows)}"
            )
        for i, p in enumerate(params):
            if p not in sweep and len({row[i] for row in rows}) != 1:
                raise src.refusal(
                    trials_line,
                    "parameter ",
                    src.name(p, trials_line or 1),
                    " is not swept, so it must have the same value in every point",
                )

    return Prepared(
        src=src,
        hypothesis=header.group(1),
        title=header.group(2) or "",
        phase=phase,
        mode=mode,
        params=params,
        sweep=sweep,
        rows=tuple(rows),
        interpreter=interp,
        declaration=decl,
        tree=tree,
    )


def _check_knob_functions(
    src: Source,
    decl: Declaration,
    params: tuple[str, ...],
    functions: dict[str, ast.FunctionDef],
    g: dict[str, Value],
) -> None:
    for knob in decl.knobs:
        fn = functions.get(knob.name)
        if knob.name in g:
            raise src.refusal(
                _line_of_global(src, knob.name),
                f"{knob.name} is a knob; set it in PARAMS or define it as a function",
            )
        if isinstance(knob, FunctionKnob):
            if fn is None:
                raise src.refusal(None, f"function-of-time knob {knob.name} needs def {knob.name}(t, ...)")
            args = [a.arg for a in fn.args.args]
            if not args or args[0] != "t":
                raise src.refusal(fn.lineno, f"the first parameter of {knob.name} must be t")
            rest = args[1:]
        else:
            if (fn is None) == (knob.name not in params):
                raise src.refusal(
                    fn.lineno if fn else None,
                    f"number knob {knob.name} must be either in PARAMS or a function, not both or neither",
                )
            if fn is None:
                continue
            rest = [a.arg for a in fn.args.args]
        for arg in rest:
            if arg not in params:
                raise src.refusal(
                    fn.lineno, f"{knob.name} takes ", src.name(arg, fn.lineno), ", which is not in PARAMS"
                )


def _line_of_global(src: Source, name: str) -> int | None:
    for number, line in enumerate(src.lines, start=1):
        if re.match(rf"{re.escape(name)}\s*=", line):
            return number
    return None


def _check_input(
    src: Source, knob: FunctionKnob | NumberKnob, value: Value, trial: int, at: float | None
) -> float:
    where = f"trial {trial}: {knob.name}" + (f" at t = {at!r} s" if at is not None else "")
    if not _number(value):
        raise src.refusal(None, f"{where} is not a number")
    if not math.isfinite(value):
        raise src.refusal(None, f"{where} is not finite ({value!r})")
    if not knob.low <= value <= knob.high:
        raise src.refusal(None, f"{where} is {value!r}, outside [{knob.low!r}, {knob.high!r}]")
    return _clean(value)


def compute(prepared: Prepared) -> Experiment:
    """Step 7 of the run gate order: evaluate every trial and check every computed input (4.4-4.7)."""
    src = prepared.src
    interp = prepared.interpreter
    functions = function_names(prepared.tree)
    trials: list[ComputedTrial] = []
    seen: dict[str, int] = {}
    for number, row in enumerate(prepared.rows, start=1):
        values = dict(zip(prepared.params, row, strict=True))
        inputs: dict[str, float | tuple[float, ...]] = {}
        for knob in prepared.declaration.knobs:
            fn = functions.get(knob.name)
            if isinstance(knob, FunctionKnob):
                if fn is None:
                    raise src.refusal(
                        None, f"function-of-time knob {knob.name} needs def {knob.name}(t, ...)"
                    )
                names = [a.arg for a in fn.args.args][1:]
                samples = []
                for at in knob.sample_times:
                    result = interp.call(knob.name, [float(at), *(values[n] for n in names)], fn)
                    samples.append(_check_input(src, knob, result, number, at))
                inputs[knob.name] = tuple(samples)
            elif fn is None:
                inputs[knob.name] = _check_input(src, knob, values[knob.name], number, None)
            else:
                names = [a.arg for a in fn.args.args]
                result = interp.call(knob.name, [values[n] for n in names], fn)
                inputs[knob.name] = _check_input(src, knob, result, number, None)
        key = trial_key(inputs)
        if key in seen:
            raise src.refusal(None, f"trial {number} has the same computed inputs as trial {seen[key]}")
        seen[key] = number
        trials.append(ComputedTrial(values, inputs, key))
    return Experiment(
        hypothesis=prepared.hypothesis,
        title=prepared.title,
        phase=prepared.phase,
        mode=prepared.mode,
        params=prepared.params,
        sweep=prepared.sweep,
        trials=tuple(trials),
        steps=interp.steps,
    )


def load(text: str, file: str, decl: Declaration, *, step_bound: int) -> Experiment:
    """Prepare and compute in one call."""
    return compute(prepare(text, file, decl, step_bound=step_bound))


__all__ = [
    "Experiment",
    "ComputedTrial",
    "LangRefusal",
    "Prepared",
    "compute",
    "load",
    "prepare",
    "trial_key",
]
