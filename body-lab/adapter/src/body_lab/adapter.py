"""BodyAdapter: the body as a bench application (body-lab Requirements 1-5, design 5).

The declaration tells Dr. Kiro only the numbered channels, the timing, the measurements and how they are made,
the picture kind, the budget and the goal. The wiring stays inside `sim.py`.
"""

import mujoco
from bench.adapter import (
    ComputedInputs,
    Declaration,
    FunctionKnob,
    Picture,
    TrialFailure,
    TrialResult,
)

from body_lab import sim
from body_lab.measure import Measurer, PoseMeasurer
from body_lab.picture import FrameRecorder, frame_times
from body_lab.settings import Settings

BUDGET = 40
GOAL = "Move the body as far as possible in the direction it faces at the start: maximise x."


class BodyAdapter:
    def __init__(self, settings: Settings | None = None, measurer: Measurer | None = None) -> None:
        self.settings = settings or Settings()
        self.measurer = measurer or PoseMeasurer(self.settings)
        self.body = sim.build(self.settings)
        wiring = sim.load_wiring()
        steps = round(wiring.trial_seconds * wiring.control_hz)
        self.sample_times = tuple(k / wiring.control_hz for k in range(steps))
        knobs = tuple(
            FunctionKnob(f"c{i}", -1.0, 1.0, self.sample_times, wiring.trial_seconds)
            for i in range(len(wiring.channels))
        )
        n_series = round(wiring.trial_seconds / self.settings.series_step_s)
        self.series_times = tuple(k * self.settings.series_step_s for k in range(n_series + 1))
        self._declaration = Declaration(
            knobs=knobs,
            measurements=self.measurer.measurements(),
            picture="image/png",
            budget=BUDGET,
            fake=False,
            goal=GOAL,
            measured_by=self.measurer.measured_by(),
        )

    def declaration(self) -> Declaration:
        return self._declaration

    def builder_versions(self) -> dict[str, str]:
        """Builder-side only: library versions the bench records outside the sealed record."""
        return {"mujoco": mujoco.__version__}

    def run_trial(self, inputs: ComputedInputs, seed: int) -> TrialResult | TrialFailure:
        commands = {}
        for knob in self._declaration.knobs:
            value = inputs[knob.name]
            if not isinstance(value, tuple) or len(value) != len(self.sample_times):
                raise TypeError(f"knob {knob.name} needs one value per sample time")
            commands[knob.name] = value
        recorder = FrameRecorder(self.body, self.settings)
        try:
            times = frame_times(self.settings)
            poses = sim.run(self.body, self.settings, commands, self.series_times, times, recorder)
            picture = recorder.png()
        finally:
            recorder.close()
        return TrialResult(self.measurer.measure(poses), Picture("image/png", picture))
