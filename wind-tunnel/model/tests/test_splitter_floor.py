"""The splitter floor (Requirement 6.11, Decision 45 and design Property 18).
Data: a positive splitter of 1e-9 and 1e-8 cannot be built as a shape, 3e-8 can; 1e-6 and 1e-4 were run to
convergence (aspect 1.75, corner 0.5, angle 5). The floor is the run value 1e-6.
"""

import pytest
from hypothesis import example, given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from wind_tunnel_model.geometry import outline
from wind_tunnel_model.input_rule import (
    corner_refusal,
    input_refusal,
    splitter_accepted,
    splitter_refusal,
)
from wind_tunnel_model.mesh import GmshMesher
from wind_tunnel_model.settings import Settings

SETTINGS = Settings.load()
FLOOR = 1e-6


@pytest.mark.parametrize("splitter", [0.0, 1e-6, 2e-6, 1e-4, 0.003, 3.0])
def test_zero_the_floor_and_larger_values_are_accepted(splitter):
    assert splitter_accepted(splitter, SETTINGS)
    assert splitter_refusal(splitter, SETTINGS) is None


@pytest.mark.parametrize("splitter", [1e-9, 1e-8, 3e-8, 9.99e-7, 5e-7])
def test_a_positive_value_below_the_floor_is_refused(splitter):
    assert not splitter_accepted(splitter, SETTINGS)
    assert splitter_refusal(splitter, SETTINGS) is not None


def test_message_text():
    assert (
        splitter_refusal(1e-9, SETTINGS)
        == "splitter 1e-09 is not accepted: splitter must be 0 or at least 1e-06"
    )
    assert splitter_refusal(9.99e-7, SETTINGS) == (
        "splitter 9.99e-07 is not accepted: splitter must be 0 or at least 1e-06"
    )


def test_message_has_no_word_of_the_solver_the_mesh_or_the_geometry_library():
    words = set(splitter_refusal(1e-9, SETTINGS).lower().replace(":", " ").split())
    for word in (
        "mesh",
        "solver",
        "gmsh",
        "geometry",
        "curve",
        "surface",
        "tolerance",
        "file",
        "build",
        "shape",
    ):
        assert word not in words


def test_every_refused_knob_is_named_with_the_corner_first():
    both = input_refusal(1.75, 0.01, 1e-9, SETTINGS)
    assert both == f"{corner_refusal(1.75, 0.01, SETTINGS)}; {splitter_refusal(1e-9, SETTINGS)}"
    assert input_refusal(1.75, 0.01, 0.5, SETTINGS) == corner_refusal(1.75, 0.01, SETTINGS)
    assert input_refusal(1.75, 0.5, 1e-9, SETTINGS) == splitter_refusal(1e-9, SETTINGS)
    assert input_refusal(1.75, 0.5, 0.5, SETTINGS) is None


# Feature: wind-tunnel, Property 18: Splitter floor
# **Validates: Requirements 3.3, 6.11**
splitters = st.one_of(
    st.sampled_from([0.0, 1e-9, 1e-8, 9.99e-7, 1e-6, 2e-6, 3.0]),
    st.floats(min_value=0.0, max_value=3.0),
    st.floats(min_value=0.0, max_value=1e-5),
)


@hyp_settings(max_examples=300, deadline=None)
@given(splitter=splitters)
def test_the_verdict_is_accept_iff_zero_or_at_least_the_floor(splitter):
    accepted = splitter == 0 or splitter >= FLOOR
    assert splitter_accepted(splitter, SETTINGS) is accepted
    assert (splitter_refusal(splitter, SETTINGS) is None) is accepted
    assert (input_refusal(1.0, 0.5, splitter, SETTINGS) is None) is accepted


@pytest.mark.needs_gmsh
@hyp_settings(max_examples=20, deadline=None)
@example(aspect=1.75, corner=0.5, splitter=1e-6, angle=5.0)
@given(
    aspect=st.floats(min_value=0.5, max_value=3.0),
    corner=st.sampled_from([0.0, 0.5, 1.0]),
    splitter=st.one_of(st.sampled_from([1e-6, 2e-6, 3.0]), st.floats(min_value=FLOOR, max_value=3.0)),
    angle=st.floats(min_value=0.0, max_value=15.0),
)
def test_every_accepted_outline_builds(tmp_path_factory, aspect, corner, splitter, angle):
    pytest.importorskip("gmsh", reason="Gmsh cannot be imported here")
    assert splitter_refusal(splitter, SETTINGS) is None
    dest = tmp_path_factory.mktemp("floor")
    GmshMesher().build(outline(aspect, corner, splitter, angle, SETTINGS), SETTINGS, dest)
