"""P25-P29: the adapter's input check (Requirement 19, design B4).

Feature: lab-bench, Property 25, Property 26, Property 27, Property 28 and Property 29."""

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from bench.adapter import INPUT_REFUSAL_MAX, ResultError, check_input_refusal
from bench.core.outcome import BenchFailure, Ran, Refused
from bench.core.session import ADAPTER_BROKE_CONTRACT, ADAPTER_RAISED, WITHHELD
from bench.fake.adapter import FakeAdapter
from labkit import Lab, examples, exp_file, hyp_block

MESSAGE = "that gain is not available; pick another"
AMPS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
GAINS = [0.5, 1.0, 1.5, 2.0, 2.25]
SWEEP_AMPS = [0.1, 0.2, 0.3, 0.4, 0.6, 0.9]


class Guarded(FakeAdapter):
    def __init__(self, refused: frozenset[float], answer: object = MESSAGE, raises: bool = False) -> None:
        super().__init__()
        self.refused = refused
        self.answer = answer
        self.raises = raises
        self.ran: list[tuple[float, ...]] = []

    def check_inputs(self, inputs):  # type: ignore[no-untyped-def]
        if self.raises:
            raise RuntimeError("check broke")
        return self.answer if inputs["gain"] in self.refused else None

    def run_trial(self, inputs, seed):  # type: ignore[no-untyped-def]
        self.ran.append(inputs["gain"])
        return super().run_trial(inputs, seed)


def planned(draw_rows: list[tuple[float, float]], sweep_gain: float | None) -> tuple[list[list[float]], str]:
    if sweep_gain is not None:
        return [[a, sweep_gain] for a in SWEEP_AMPS], "sweep"
    return [list(r) for r in draw_rows], "compare"


# Distinct rows (an exact repeat is refused earlier), 1 to 3 variants, or a sweep at one gain.
scenarios = st.tuples(
    st.lists(st.tuples(st.sampled_from(AMPS), st.sampled_from(GAINS)), min_size=1, max_size=3, unique=True),
    st.one_of(st.none(), st.sampled_from(GAINS)),
    st.frozensets(st.sampled_from(GAINS), max_size=3),
)


def in_session(adapter: Guarded, rows: list[list[float]], mode: str):  # type: ignore[no-untyped-def]
    with tempfile.TemporaryDirectory(prefix="bench-input-check-") as tmp:
        lab = Lab(Path(tmp))
        session = lab.start(adapter=adapter)
        lab.add(hyp_block("H1", "WHEN amp rises, THE distance SHALL rise.", {"id": "P1", "range": [0.4, 0.6],
                          "when": {"amp": 0.5, "gain": 1.0}}))  # fmt: skip
        assert isinstance(session.register("H1"), Ran)
        before = len(session.store.entries)
        sweep = ["amp"] if mode == "sweep" else None
        outcome = session.run(lab.experiment("e.py", exp_file("H1", rows, mode=mode, sweep=sweep)))
        kinds = [e["kind"] for e in session.store.entries[before:]]
        return outcome, session, kinds


@settings(max_examples=examples(100), deadline=None)
@given(scenarios)
def test_p25_p26_a_refusal_in_any_planned_trial_refuses_the_whole_experiment_first(scenario) -> None:  # type: ignore[no-untyped-def]
    """P25: a refusal uses no budget and writes no run record. P26: it is raised before any trial runs, for a
    refusing trial at any position, and the experiment runs when no trial is refused."""
    draw_rows, sweep_gain, refused = scenario
    rows, mode = planned(draw_rows, sweep_gain)
    adapter = Guarded(refused)
    outcome, session, kinds = in_session(adapter, rows, mode)
    first = next((i for i, r in enumerate(rows, start=1) if r[1] in refused), None)
    if first is None:
        assert isinstance(outcome, Ran)
        assert len(adapter.ran) == len(rows) and session.state.remaining == 12 - len(rows)
        return
    assert isinstance(outcome, Refused)
    assert outcome.message.plain() == f"trial {first} of this experiment cannot run: {MESSAGE}"
    assert adapter.ran == []  # P26: not one trial ran, also not the ones before the refusing trial
    assert kinds == ["refusal"]  # P25: only the refusal entry
    assert session.state.remaining == 12 and session.state.trials_run == 0 and session.state.sealed is None


@settings(max_examples=examples(100), deadline=None)
@given(scenarios)
def test_p27_an_adapter_without_the_method_refuses_nothing(scenario) -> None:  # type: ignore[no-untyped-def]
    draw_rows, sweep_gain, _ = scenario
    rows, mode = planned(draw_rows, sweep_gain)
    adapter = FakeAdapter()
    assert not hasattr(adapter, "check_inputs")
    outcome, session, _ = in_session(adapter, rows, mode)  # type: ignore[arg-type]
    assert isinstance(outcome, Ran) and session.state.remaining == 12 - len(rows)


@settings(max_examples=examples(100), deadline=None)
@given(st.sampled_from(["the zorblat", "zorblat", "a wobbet here", "quindle_arm"]), st.booleans())
def test_p29_a_message_with_a_derived_term_never_reaches_dr_kiro(term: str, at_start: bool) -> None:
    text = f"{term} refuses this" if at_start else f"this is refused by the {term}"
    adapter = Guarded(frozenset({2.0}), answer=text)
    outcome, session, _ = in_session(adapter, [[0.5, 2.0]], "compare")
    assert isinstance(outcome, BenchFailure) and outcome.message.plain() == WITHHELD
    assert session.state.sealed == "stopped" and adapter.ran == []


bad_texts = st.one_of(
    st.just(""),
    st.text(max_size=INPUT_REFUSAL_MAX + 5),
    st.integers(INPUT_REFUSAL_MAX - 1, INPUT_REFUSAL_MAX + 2).map(lambda n: "x" * n),
    st.sampled_from([" a", "a ", "a\nb", "a\tb", "\x00"]),
    st.one_of(st.integers(), st.lists(st.text(max_size=3), max_size=2), st.booleans()),
)


def message_ok(text: object) -> bool:
    return (
        isinstance(text, str)
        and text != ""
        and text.isprintable()
        and text == text.strip(" ")
        and len(text) <= INPUT_REFUSAL_MAX
    )


@settings(max_examples=examples(100), deadline=None)
@given(bad_texts)
def test_p28_the_message_check_accepts_exactly_the_valid_texts(text: object) -> None:
    if message_ok(text):
        assert check_input_refusal(text) == text
    else:
        try:
            check_input_refusal(text)
        except ResultError:
            pass
        else:
            raise AssertionError(f"accepted {text!r}")


@settings(max_examples=examples(100), deadline=None)
@given(bad_texts, st.booleans())
def test_p28_a_bad_message_or_a_raising_check_is_a_bench_failure(text: object, raises: bool) -> None:
    adapter = Guarded(frozenset({2.0}), answer=text, raises=raises)
    outcome, session, _ = in_session(adapter, [[0.5, 2.0]], "compare")
    if raises:
        assert isinstance(outcome, BenchFailure) and ADAPTER_RAISED in outcome.message.plain()
    elif message_ok(text):
        assert isinstance(outcome, Refused)
        return
    else:
        assert isinstance(outcome, BenchFailure) and ADAPTER_BROKE_CONTRACT in outcome.message.plain()
    assert session.state.sealed == "stopped" and adapter.ran == [] and session.state.trials_run == 0
