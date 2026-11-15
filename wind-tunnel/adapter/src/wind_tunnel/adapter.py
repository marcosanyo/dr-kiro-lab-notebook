"""The wind-tunnel adapter and its run pipeline (wind-tunnel Requirements 3, 4, 8, 10; design 6).

`WindAdapter.run_trial` follows the flow of the design: validate the four inputs, outline, case, mesh, run,
parse, estimators, settle, picture. Every expected failure of a stage becomes a `TrialFailure` with one of
the two fixed public reasons; its detail (cause, knob values, case folder, log tail) is builder side only.
A run whose flow does not settle is not a failure: it is a result with the picture and `not_settled` for all
five measurements (Requirements 4.5 and 8.3, Decision 37).
Nothing is retried, repaired, clipped or defaulted, the trial seed is not used (10.2), and an exception that
is not one of the named failures of a stage is not caught.

One deviation from the order of the diagram, forced by the model: `render_case` needs an empty folder, so the
case is written before the mesh file is added to it. Both happen before the solver runs, inside the same
time limit.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping
from pathlib import Path

import numpy as np
from bench.adapter import (
    ComputedInputs,
    Declaration,
    NotMeasured,
    NumberKnob,
    Picture,
    TrialFailure,
    TrialResult,
)
from wind_tunnel_model.casegen import KNOB_NAMES, render_case
from wind_tunnel_model.estimators import EstimatorError, dynamic_pressure, measure
from wind_tunnel_model.geometry import GeometryError, outline
from wind_tunnel_model.input_rule import InputRuleError, corner_refusal
from wind_tunnel_model.mesh import GmshMesher, Mesher, MeshError
from wind_tunnel_model.settings import Settings, frame_times
from wind_tunnel_model.settle import settled
from wind_tunnel_model.solver_output import (
    SolverOutputError,
    parse_force_file,
    parse_vorticity_file,
)

from wind_tunnel import environment
from wind_tunnel.declaration import NOT_SETTLED, build_declaration
from wind_tunnel.failures import FailureKind, trial_failure
from wind_tunnel.picture import picture_sheet
from wind_tunnel.runner import (
    DockerRunner,
    Runner,
    RunOutput,
    SolverFailure,
    create_case_folder,
    empty_trash,
    move_to_trash,
    prune_case_folder,
)

CASE_BASE = environment.RECORD_PATH.parent
NOT_SHEDDING_REASON = "the lift does not oscillate: cl_amp is not above 0.01"
# One fixed line in Dr. Kiro's terms: no number of the settle rule, and no claim about a longer trial (4.5).
NOT_SETTLED_REASON = "the flow had not settled within the trial"
# A sample folder is matched to a frame time when the two differ by less than this (time units).
FRAME_TIME_TOLERANCE = 1e-6


class WindAdapter:
    """The wind tunnel as a bench application. The environment is checked when it is created (7.1, 7.3)."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        runner: Runner | None = None,
        mesher: Mesher | None = None,
        command: environment.CommandFunction = environment.run_command,
        lock_path: Path | str | None = None,
        record_path: Path | str | None = None,
        case_base: Path | str | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._settings = settings or Settings.load()
        environment.check(self._settings, command=command, lock_path=lock_path, record_path=record_path)
        if runner is None:
            lock = environment.load_lock(lock_path)
            runner = DockerRunner(f"{self._settings.image.name}@{lock.digest}")
        self._runner = runner
        self._mesher = mesher if mesher is not None else GmshMesher()
        self._case_base = Path(case_base) if case_base is not None else CASE_BASE
        self._clock = clock
        self._declaration = build_declaration(self._settings)

    def declaration(self) -> Declaration:
        return self._declaration

    def check_inputs(self, inputs: ComputedInputs) -> str | None:
        """The bench's optional input check (lab-bench Requirement 19), called for every trial of an
        experiment before any trial runs. A pure function of the inputs: the corner rule of the model, in
        Dr. Kiro's terms. The plate (`splitter`) and `angle` are never looked at."""
        return corner_refusal(float(inputs["aspect"]), float(inputs["corner"]), self._settings)

    def run_trial(self, inputs: ComputedInputs, seed: int) -> TrialResult | TrialFailure:
        """One trial. The seed is not used: the same inputs give the same result (10.2).

        The trash of the run before is deleted first, before the clock of the time limit starts (8.7). The
        limit then covers the mesh, the solver and everything after it up to and including the picture."""
        empty_trash(self._case_base)
        start = self._clock()
        deadline = start + self._settings.run.timeout_s
        knobs = self._validate(inputs)
        settings = self._settings

        try:
            body = outline(settings=settings, **knobs)
        except GeometryError as error:
            return self._failure_without_case(FailureKind.INCOMPLETE, f"geometry: {error}", knobs)

        case_dir = create_case_folder(self._case_base, seed)
        render_case(knobs, settings, case_dir)
        try:
            self._mesher.build(body, settings, case_dir)
        except MeshError as error:
            return self._failure_with_case(FailureKind.INCOMPLETE, f"mesh: {error}", knobs, case_dir, "")

        try:
            output = self._runner.run(case_dir, deadline)
        except SolverFailure as failure:
            return self._failure_with_case(failure.kind, failure.reason, knobs, case_dir, failure.detail)

        problem: tuple[FailureKind, str] | None = None
        outcome: TrialResult | None = None
        try:
            outcome = self._evaluate(output, settings)
        except SolverOutputError as error:
            problem = (FailureKind.INCOMPLETE, f"solver output: {error}")
        except EstimatorError as error:
            problem = (FailureKind.INCOMPLETE, f"estimators: {error}")
        # The limit also covers the work after the solver. A run that passes it anywhere in that part is a
        # time-out, whatever the part found (8.7).
        over = self._clock() - deadline
        if over >= 0:
            found = problem[1] if problem else "a result"
            return self._failure_with_case(
                FailureKind.TIMEOUT,
                f"the limit of {settings.run.timeout_s!r} s was over by {over!r} s when the work after the "
                f"solver ended (the part found: {found})",
                knobs,
                case_dir,
                "",
            )
        if problem is not None:
            return self._failure_with_case(*problem, knobs, case_dir, "")

        # A run that did not settle is a result, like a settled one: its folder goes to the trash too.
        move_to_trash(case_dir)
        return outcome

    def _validate(self, inputs: ComputedInputs) -> dict[str, float]:
        """Exactly the four names, finite numbers inside the ranges, a corner the rule accepts. Nothing is
        clipped or defaulted (3.4)."""
        if not isinstance(inputs, Mapping) or set(inputs) != set(KNOB_NAMES):
            found = sorted(inputs) if isinstance(inputs, Mapping) else type(inputs).__name__
            raise ValueError(f"inputs: expected exactly {sorted(KNOB_NAMES)}, found {found}")
        knobs: dict[str, float] = {}
        for knob in self._declaration.knobs:
            assert isinstance(knob, NumberKnob)
            value = inputs[knob.name]
            if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
                raise ValueError(f"inputs: {knob.name} must be a finite number, got {value!r}")
            if not knob.low <= value <= knob.high:
                raise ValueError(f"inputs: {knob.name}={value!r} is outside [{knob.low}, {knob.high}]")
            knobs[knob.name] = float(value)
        # A value the check refuses must never run, even when the bench check was not called (no fallback).
        refusal = corner_refusal(knobs["aspect"], knobs["corner"], self._settings)
        if refusal is not None:
            raise InputRuleError(f"inputs: {refusal}")
        return knobs

    def _failure_without_case(
        self, kind: FailureKind, cause: str, knobs: Mapping[str, float]
    ) -> TrialFailure:
        return trial_failure(kind, cause, knobs, "none made", "")

    def _failure_with_case(
        self, kind: FailureKind, cause: str, knobs: Mapping[str, float], case_dir: Path, detail: str
    ) -> TrialFailure:
        """A failed run keeps only its log, settings, mesh file and force file (10.6). A folder that cannot be
        pruned raises: the exception is not caught, so the session stops with the reason."""
        prune_case_folder(case_dir)
        return trial_failure(kind, cause, knobs, case_dir, detail)

    def _evaluate(self, output: RunOutput, settings: Settings) -> TrialResult:
        """Parse, measure, settle, draw. The picture sheet is drawn the same way whether the run settled or
        not. A run that did not settle gives `not_settled` for all five measurements (4.5, 8.3)."""
        force = parse_force_file(output.force_file)
        if force.t[-1] < settings.time.end - settings.time.max_delta_t:
            raise SolverOutputError(
                f"{output.force_file}: the force history ends at {force.t[-1]!r}, "
                f"before the end of the run at {settings.time.end!r}"
            )
        part = force.t >= settings.time.average_from
        t, fx, fy = force.t[part], force.fx[part], force.fy[part]
        measured = measure(t, fx, fy, settings.flow)
        q = dynamic_pressure(settings.flow)
        verdict = settled(t, fx / q, fy / q, measured.shedding, measured.strouhal)
        frames = self._frames(output, settings)
        sheet = picture_sheet(frames, settings.picture)
        picture = Picture(kind="image/png", data=sheet)
        if not verdict.ok:
            not_settled = NotMeasured(NOT_SETTLED, NOT_SETTLED_REASON)
            return TrialResult(
                values={m.name: not_settled for m in self._declaration.measurements}, picture=picture
            )
        strouhal: float | NotMeasured = (
            NotMeasured("not_shedding", NOT_SHEDDING_REASON)
            if measured.strouhal is None
            else float(measured.strouhal)
        )
        values = {
            "cd": float(measured.cd),
            "cl_mean": float(measured.cl_mean),
            "cl_amp": float(measured.cl_amp),
            "strouhal": strouhal,
            "shedding": float(measured.shedding),
        }
        return TrialResult(values=values, picture=picture)

    @staticmethod
    def _frames(output: RunOutput, settings: Settings) -> list[tuple[np.ndarray, np.ndarray]]:
        """The sampled vorticity of every frame, in time order; the sample folders must be the frame times."""
        times = frame_times(settings)
        files = output.sample_files
        if len(files) != len(times):
            raise SolverOutputError(f"expected {len(times)} sampled vorticity files, found {len(files)}")
        frames = []
        for path, expected in zip(files, times, strict=True):
            try:
                written = float(path.parent.name)
            except ValueError as error:
                raise SolverOutputError(f"{path}: the folder name is not a time") from error
            if abs(written - expected) >= FRAME_TIME_TOLERANCE:
                raise SolverOutputError(
                    f"{path}: written at {written!r}, expected the frame time {expected!r}"
                )
            frame = parse_vorticity_file(path, settings.picture)
            frames.append((frame.omega, frame.mask))
        return frames
