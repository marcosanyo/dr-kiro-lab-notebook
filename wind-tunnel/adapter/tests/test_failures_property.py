"""wind-tunnel task 9.2: Property 9, failure mapping.

**Validates: Requirements 8.1, 8.4, 8.5, 8.8**
"""

from bench.adapter import TrialFailure
from hypothesis import given, settings
from hypothesis import strategies as st

from wind_tunnel.failures import PUBLIC_REASONS, FailureKind, trial_failure

CAUSES = [
    "solver exited with a non-zero status",
    "solver diverged: floating point exception",
    "solver stopped before the end time",
    "geometry error: self-intersecting outline",
    "mesh error: negative cell volume",
    "mesh error: no cells generated",
    "non-finite value in the force file",
    "non-finite value in the sampled field",
    "timeout after the wall-clock limit",
    "not settled: the force signal still drifts",
]

# A fixed list of solver words that must never reach the public reason.
SOLVER_WORDS = [
    "openfoam",
    "foam",
    "simplefoam",
    "pimplefoam",
    "icofoam",
    "gmsh",
    "blockmesh",
    "snappyhexmesh",
    "solver",
    "mesh",
    "fvschemes",
    "fvsolution",
    "controldict",
    "residual",
    "courant",
    "docker",
    "kepsilon",
    "komega",
    "turbulence",
    "boundary",
    "patch",
    "nan",
    "inf",
    "diverge",
    "log",
    "stderr",
    "traceback",
    "exception",
    "/",
    "\\",
    ".py",
    ".msh",
    ".geo",
]

knob_values = st.fixed_dictionaries(
    {
        "aspect": st.floats(0.5, 3.0),
        "corner": st.floats(0.0, 1.0),
        "splitter": st.floats(0.0, 3.0),
        "angle": st.floats(0.0, 15.0),
    }
)
kinds = st.sampled_from(list(FailureKind))
causes = st.one_of(st.sampled_from(CAUSES), st.text(min_size=1, max_size=40))
folders = st.text(min_size=1, max_size=30)
tails = st.text(max_size=60)


@settings(max_examples=200, deadline=None)
@given(kind=kinds, cause=causes, knobs=knob_values, folder=folders, tail=tails)
def test_failure_has_a_fixed_reason_free_of_inputs_and_solver_words(kind, cause, knobs, folder, tail):
    failure = trial_failure(kind, cause, knobs, folder, tail)
    assert isinstance(failure, TrialFailure)
    assert failure.public_reason in set(PUBLIC_REASONS.values())
    assert len(set(PUBLIC_REASONS.values())) == 3
    assert failure.public_reason == PUBLIC_REASONS[kind]
    lowered = failure.public_reason.lower()
    for word in SOLVER_WORDS:
        assert word not in lowered
    assert cause in failure.detail


@settings(max_examples=200, deadline=None)
@given(
    kind=kinds,
    first=st.tuples(causes, knob_values, folders, tails),
    second=st.tuples(causes, knob_values, folders, tails),
)
def test_same_kind_gives_the_same_reason_whatever_the_inputs(kind, first, second):
    a = trial_failure(kind, first[0], first[1], first[2], first[3])
    b = trial_failure(kind, second[0], second[1], second[2], second[3])
    assert a.public_reason == b.public_reason


@settings(max_examples=100, deadline=None)
@given(cause=st.sampled_from(CAUSES), knobs=knob_values)
def test_timeout_is_a_failure_not_a_missing_measurement(cause, knobs):
    failure = trial_failure(FailureKind.TIMEOUT, cause, knobs, "folder", "tail")
    assert isinstance(failure, TrialFailure)
    assert failure.public_reason == PUBLIC_REASONS[FailureKind.TIMEOUT]
