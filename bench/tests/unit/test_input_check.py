"""The adapter's optional input check (Requirement 19, design B1-B3)."""

import pytest

from bench.adapter import INPUT_REFUSAL_MAX, ResultError, check_input_refusal, input_refusal
from bench.core.outcome import BenchFailure, Ran, Refused
from bench.core.session import ADAPTER_BROKE_CONTRACT, ADAPTER_RAISED, WITHHELD
from bench.fake.adapter import FakeAdapter
from labkit import Lab, exp_file, hyp_block

MESSAGE = "gain 2.0 is not available; pick a smaller gain"


class Guarded(FakeAdapter):
    """The fake application with an input check that refuses the gains in `refused`. Records what it saw."""

    def __init__(self, refused: tuple[float, ...] = (), answer: object = MESSAGE) -> None:
        super().__init__()
        self.refused = refused
        self.answer = answer
        self.checked: list[float] = []
        self.ran: list[float] = []

    def check_inputs(self, inputs):  # type: ignore[no-untyped-def]
        gain = inputs["gain"]
        self.checked.append(gain)
        return self.answer if gain in self.refused else None

    def run_trial(self, inputs, seed):  # type: ignore[no-untyped-def]
        self.ran.append(inputs["gain"])
        return super().run_trial(inputs, seed)


def start(lab: Lab, adapter: FakeAdapter):  # type: ignore[no-untyped-def]
    session = lab.start(adapter=adapter)
    lab.add(hyp_block("H1", "WHEN amp rises, THE distance SHALL rise.", {"id": "P1", "range": [0.4, 0.6],
                      "when": {"amp": 0.5, "gain": 1.0}}))  # fmt: skip
    assert isinstance(session.register("H1"), Ran)
    return session


def run(lab: Lab, session, rows):  # type: ignore[no-untyped-def]
    return session.run(lab.experiment("e.py", exp_file("H1", rows)))


def test_a_refused_trial_refuses_the_whole_experiment_and_costs_nothing(lab: Lab) -> None:
    adapter = Guarded(refused=(2.0,))
    session = start(lab, adapter)
    before = len(session.store.entries)
    outcome = run(lab, session, [[0.5, 1.0], [0.5, 2.0], [0.25, 1.0]])
    assert isinstance(outcome, Refused)
    assert outcome.message.plain() == f"trial 2 of this experiment cannot run: {MESSAGE}"
    assert adapter.ran == [] and adapter.checked == [1.0, 2.0]  # stops at the first refusing trial
    assert session.state.remaining == 12 and session.state.trials_run == 0 and session.state.sealed is None
    new = session.store.entries[before:]
    assert [e["kind"] for e in new] == ["refusal"]
    assert new[0]["body"]["action"] == "run"
    assert (
        f"input check refused trial 2 of 'experiments/e.py': {MESSAGE}"
        in (session.store.folder / "builder.log").read_text()
    )
    # The values are not marked as tried: the same first row runs once the refused one is gone.
    assert isinstance(run(lab, session, [[0.5, 1.0], [0.25, 1.0]]), Ran)
    assert adapter.ran == [1.0, 1.0]


def test_the_check_sees_every_planned_trial_of_a_sweep(lab: Lab) -> None:
    adapter = Guarded(refused=(2.0,))
    session = start(lab, adapter)
    rows = [[a, 2.0] for a in (0.1, 0.2, 0.3, 0.4, 0.6, 0.9)]
    outcome = session.run(lab.experiment("s.py", exp_file("H1", rows, mode="sweep", sweep=["amp"])))
    assert isinstance(outcome, Refused) and outcome.message.plain().startswith("trial 1 of ")
    assert adapter.ran == [] and session.state.remaining == 12


def test_an_adapter_without_the_method_refuses_nothing(lab: Lab) -> None:
    assert not hasattr(FakeAdapter(), "check_inputs")
    assert input_refusal(FakeAdapter(), {"drive": (0.0,), "gain": 1.0}) is None
    session = start(lab, FakeAdapter())
    assert isinstance(run(lab, session, [[0.5, 1.0]]), Ran)


def test_a_check_that_returns_none_refuses_nothing(lab: Lab) -> None:
    adapter = Guarded()
    session = start(lab, adapter)
    assert isinstance(run(lab, session, [[0.5, 1.0], [0.5, 2.0]]), Ran)
    assert adapter.checked == [1.0, 2.0] and adapter.ran == [1.0, 2.0]


def test_a_check_that_raises_is_a_bench_failure(lab: Lab) -> None:
    class Raising(Guarded):
        def check_inputs(self, inputs):  # type: ignore[no-untyped-def]
            raise RuntimeError("the check broke")

    session = start(lab, Raising())
    outcome = run(lab, session, [[0.5, 1.0]])
    assert isinstance(outcome, BenchFailure) and ADAPTER_RAISED in outcome.message.plain()
    assert "RuntimeError: the check broke" in (session.last_failure_detail or "")
    assert "the check broke" not in outcome.message.plain()
    assert session.state.sealed == "stopped" and session.state.trials_run == 0


@pytest.mark.parametrize(
    "answer", ["", " leading", "trailing ", "two\nlines", "tab\there", "x" * 401, 7, ["a"]]
)
def test_a_bad_message_is_a_bench_failure(lab: Lab, answer: object) -> None:
    session = start(lab, Guarded(refused=(2.0,), answer=answer))
    outcome = run(lab, session, [[0.5, 2.0]])
    assert isinstance(outcome, BenchFailure) and ADAPTER_BROKE_CONTRACT in outcome.message.plain()
    assert session.state.sealed == "stopped" and session.state.trials_run == 0


def test_the_limit_is_exact() -> None:
    assert check_input_refusal("x" * INPUT_REFUSAL_MAX) == "x" * INPUT_REFUSAL_MAX
    with pytest.raises(ResultError):
        check_input_refusal("x" * (INPUT_REFUSAL_MAX + 1))


def test_a_message_with_a_derived_term_is_a_bench_failure_and_not_shown(lab: Lab) -> None:
    session = start(lab, Guarded(refused=(2.0,), answer="the zorblat cannot take this"))
    outcome = run(lab, session, [[0.5, 2.0]])
    assert isinstance(outcome, BenchFailure) and outcome.message.plain() == WITHHELD
    assert "zorblat" not in outcome.message.plain()
    assert session.state.sealed == "stopped"
