"""Coordinates of the prediction chart (task 17.1; Requirements 17.2, 17.3). Plain values, no record."""

from notebook.pages import chart as page
from notebook.pages.chart import MARGIN, WIDTH


def test_a_value_at_the_scale_ends_sits_at_the_margins():
    assert page._x((2.0, 6.0), 2.0) == MARGIN
    assert page._x((2.0, 6.0), 6.0) == WIDTH - MARGIN


def test_a_scale_of_one_value_is_drawn_in_the_middle():
    assert page._x((3.0, 3.0), 3.0) == WIDTH / 2


def test_coordinates_have_two_decimals_and_no_negative_zero():
    assert page._c(1.5) == "1.50"
    assert page._c(-0.0) == "0.00"
    assert page._c(-0.001) == "0.00"
