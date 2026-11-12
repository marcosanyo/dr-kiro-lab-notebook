"""Rendering core outcomes as MCP results (Requirement 17.3, design F4).

Message spans are joined in order, with no added words. A run returns one JSON text content and no image
content; each picture is replaced by the path the picture writer returns (F5).
"""

import json
from collections.abc import Callable
from typing import Any

from mcp_types import CallToolResult, TextContent

from bench.adapter import NotMeasured
from bench.core.outcome import BenchFailure, Outcome, Ran, Refused
from bench.core.session import Accepted, RunResult, TrialOutput

PictureWriter = Callable[[str, TrialOutput], str]


def _text(text: str, *, error: bool) -> CallToolResult:
    return CallToolResult(content=[TextContent(text=text)], is_error=error)


def run_json(result: RunResult, write_picture: PictureWriter) -> dict[str, Any]:
    trials = []
    for trial in result.trials:
        measurements: dict[str, Any] = {}
        not_measured: dict[str, Any] = {}
        for name, value in trial.measurements.items():
            if isinstance(value, NotMeasured):
                not_measured[name] = {"outcome": value.outcome, "reason": value.reason}
            else:
                measurements[name] = list(value) if isinstance(value, tuple) else value
        trials.append(
            {
                "trial": trial.trial,
                "measurements": measurements,
                "not_measured": not_measured,
                "picture": write_picture(result.experiment, trial),
            }
        )
    return {"experiment": result.experiment, "trials": trials, "budget_remaining": result.budget_remaining}


def render(outcome: Outcome, write_picture: PictureWriter) -> CallToolResult:
    if isinstance(outcome, Refused | BenchFailure):
        return _text(outcome.message.plain(), error=True)
    if not isinstance(outcome, Ran):
        raise TypeError(f"not a core outcome: {outcome!r}")
    result = outcome.result
    if isinstance(result, RunResult):
        return _text(json.dumps(run_json(result, write_picture)), error=False)
    if isinstance(result, Accepted):
        return _text(json.dumps({"budget_remaining": result.budget_remaining}), error=False)
    raise TypeError(f"the front end does not render {type(result).__name__}")
