"""Session state, derived only from the record (design 6.4).

`apply` is the one place where an entry changes the state. Live actions append an entry and then apply it;
`Session.open` replays the log through the same function, so the replayed state equals the live state.
"""

from dataclasses import dataclass, field
from typing import Any

from bench.conditions import NOT_RUN, PredictionOutcome, TriedTrial


@dataclass
class PredictionState:
    id: str
    measurement: str
    low: float
    high: float
    label: str
    condition_class: str
    when: dict[str, float]


@dataclass
class HypothesisState:
    id: str
    frozen_blob: str
    predictions: dict[str, PredictionState]


@dataclass
class ExperimentState:
    id: str
    hypothesis: str
    trials: list[str] = field(default_factory=list)
    verdict: str | None = None


@dataclass
class State:
    budget: int = 0
    remaining: int = 0
    fake: bool = False
    hypotheses: dict[str, HypothesisState] = field(default_factory=dict)
    outcomes: dict[str, PredictionOutcome] = field(default_factory=dict)
    experiments: dict[str, ExperimentState] = field(default_factory=dict)
    pending: str | None = None
    tried: list[TriedTrial] = field(default_factory=list)
    keys: dict[str, str] = field(default_factory=dict)  # trial key -> experiment id
    trials_run: int = 0
    refusals: int = 0
    snapshots: int = 0
    sealed: str | None = None  # "ended" | "stopped"


def _params(items: list[dict[str, Any]]) -> dict[str, float]:
    return {item["name"]["text"]: item["value"] for item in items}


def apply(state: State, entry: dict[str, Any]) -> None:
    kind = entry["kind"]
    body = entry["body"]
    if kind == "start":
        state.budget = body["budget"]
        state.remaining = body["budget"]
        state.fake = body["declaration"]["fake"]
    elif kind == "register":
        predictions = {
            p["id"]: PredictionState(
                p["id"],
                p["measurement"],
                p["range"][0],
                p["range"][1],
                p["label"],
                p["class"],
                _params(p["when"]),
            )
            for p in body["predictions"]
        }
        state.hypotheses[body["hypothesis"]] = HypothesisState(
            body["hypothesis"], body["frozen"]["blob"], predictions
        )
        for pid in predictions:
            state.outcomes[pid] = NOT_RUN
    elif kind == "experiment":
        state.experiments[body["experiment"]] = ExperimentState(body["experiment"], body["hypothesis"])
        state.pending = body["experiment"]
    elif kind == "trial":
        experiment = state.experiments[body["experiment"]]
        experiment.trials.append(body["trial"])
        state.tried.append(TriedTrial(body["experiment"], body["trial"], _params(body["params"])))
        state.keys[body["key"]] = body["experiment"]
        state.trials_run += 1
        state.remaining -= 1
    elif kind == "outcome":
        state.outcomes[body["prediction"]] = PredictionOutcome(
            body["outcome"], body["experiment"], body["trial"], body["value"], body["not_measured"]
        )
    elif kind == "verdict":
        state.experiments[body["experiment"]].verdict = body["verdict"]
        state.pending = None
    elif kind == "refusal":
        state.refusals += 1
    elif kind == "snapshot":
        state.snapshots += 1
    elif kind == "seal":
        state.sealed = body["end"]
    elif kind in ("flag", "failure"):
        pass
    else:
        raise ValueError(f"unknown entry kind {kind!r}")
