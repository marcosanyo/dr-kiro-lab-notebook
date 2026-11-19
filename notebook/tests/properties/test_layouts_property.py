"""Property test of the frame layout table and the sheet size check (task 5.2).

The pictures here are fixtures built with the bench's PNG encoder; none is a recorded result.
"""

# Feature: lab-notebook, Property 12: Layouts and sheet sizes
# **Validates: Requirements 7.2, 7.3**

import pytest
from bench.pictures import encode_png
from hypothesis import given, settings
from hypothesis import strategies as st

from notebook.errors import NotebookError
from notebook.layouts import Cells, Layout, check_sheet, parse

counts = st.integers(min_value=1, max_value=6)
gaps = st.integers(min_value=0, max_value=5)


def _entry(frames: int, rows: int, columns: int, gap: int) -> str:
    return (
        f"[fake]\nframes = {frames}\nrows = {rows}\ncolumns = {columns}\ngap = {gap}\n"
        "interval = 200\n"
        'source = "test fixture"\n'
    )


def _whole_cell(length: int, count: int, gap: int) -> int | None:
    """Reference: search every cell size c >= 1 for length == count * c + (count - 1) * gap."""
    for c in range(1, length + 1):
        if count * c + (count - 1) * gap == length:
            return c
    return None


@settings(max_examples=200)
@given(frames=st.integers(min_value=1, max_value=40), rows=counts, columns=counts, gap=gaps)
def test_layout_accepted_iff_frames_equal_rows_times_columns(
    frames: int, rows: int, columns: int, gap: int
) -> None:
    text = _entry(frames, rows, columns, gap)
    if frames == rows * columns:
        assert parse(text, "f.toml") == {
            "fake": Layout("fake", frames, rows, columns, gap, 200, "test fixture")
        }
    else:
        with pytest.raises(NotebookError) as caught:
            parse(text, "f.toml")
        assert caught.value.where == "f.toml [fake]"


@st.composite
def layout_and_size(draw: st.DrawFn) -> tuple[Layout, int, int]:
    rows = draw(counts)
    columns = draw(counts)
    gap = draw(gaps)
    layout = Layout("fake", rows * columns, rows, columns, gap, 200, "test fixture")
    if draw(st.booleans()):
        # A size built from whole cells, possibly nudged by one pixel so the near misses are tried.
        width = columns * draw(st.integers(1, 8)) + (columns - 1) * gap + draw(st.sampled_from([-1, 0, 0, 1]))
        height = rows * draw(st.integers(1, 8)) + (rows - 1) * gap + draw(st.sampled_from([-1, 0, 0, 1]))
    else:
        width = draw(st.integers(1, 60))
        height = draw(st.integers(1, 60))
    return layout, max(width, 1), max(height, 1)


@settings(max_examples=200)
@given(case=layout_and_size())
def test_sheet_accepted_iff_whole_cells_exist(case: tuple[Layout, int, int]) -> None:
    layout, width, height = case
    data = encode_png([[(0, 0, 0)] * width for _ in range(height)])
    cw = _whole_cell(width, layout.columns, layout.gap)
    ch = _whole_cell(height, layout.rows, layout.gap)
    if cw is not None and ch is not None:
        assert check_sheet(layout, "rec", "T1", "image/png", data) == Cells(cw, ch)
    else:
        with pytest.raises(NotebookError) as caught:
            check_sheet(layout, "rec", "T1", "image/png", data)
        assert caught.value.where == "rec T1"
        assert f"{width} x {height}" in caught.value.problem
