"""Unit tests of the frame layout table and the sheet check (task 5.1). The pictures here are fixtures built
with the bench's PNG encoder; none is a recorded result."""

from pathlib import Path

import pytest
from bench.pictures import encode_png

from notebook.errors import NotebookError
from notebook.layouts import Cells, Layout, check_sheet, layout_for, load, parse

FAKE = Layout("fake", frames=6, rows=2, columns=3, gap=4, source="test fixture")


def _png(width: int, height: int) -> bytes:
    return encode_png([[(0, 0, 0)] * width for _ in range(height)])


def _entry(**overrides: object) -> str:
    values: dict[str, object] = {"frames": 1, "rows": 1, "columns": 1, "gap": 0, "source": '"test fixture"'}
    values.update(overrides)
    return "[fake]\n" + "".join(f"{key} = {value}\n" for key, value in values.items() if value is not None)


def test_committed_layouts_file() -> None:
    path = Path(__file__).resolve().parents[2] / "layouts.toml"
    layouts = load(path)
    assert layouts == {
        "body-lab": Layout("body-lab", 10, 2, 5, 0, "body-lab design, picture: 10 frames, 2 rows of 5"),
        "wind-tunnel": Layout("wind-tunnel", 6, 2, 3, 4, "wind-tunnel Requirement 9.4"),
    }


def test_fixture_entry_parses() -> None:
    assert parse(_entry(), "f.toml") == {"fake": Layout("fake", 1, 1, 1, 0, "test fixture")}


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"frames": 2}, "does not equal rows times columns"),
        ({"gap": None}, "missing key(s): gap"),
        ({"extra": 1}, "unknown key(s): extra"),
        ({"rows": 0}, "rows must be at least 1"),
        ({"gap": -1}, "gap must be at least 0"),
        ({"columns": "true"}, "columns must be a whole number"),
        ({"frames": "1.0"}, "frames must be a whole number"),
        ({"source": '""'}, "source must be a non-empty string"),
    ],
)
def test_bad_entry_fails_naming_it(overrides: dict[str, object], fragment: str) -> None:
    with pytest.raises(NotebookError) as caught:
        parse(_entry(**overrides), "f.toml")
    assert caught.value.where == "f.toml [fake]"
    assert fragment in caught.value.problem


def test_entry_that_is_not_a_table_fails() -> None:
    with pytest.raises(NotebookError, match=r"f.toml \[fake\]: must be a table"):
        parse('fake = "x"\n', "f.toml")


def test_missing_application_entry_fails_naming_it() -> None:
    with pytest.raises(NotebookError) as caught:
        layout_for({"fake": FAKE}, "other-lab", "sessions/other-lab/s1")
    assert caught.value.where == "sessions/other-lab/s1"
    assert "'other-lab'" in caught.value.problem


def test_sheet_with_gap_gives_cell_size() -> None:
    assert check_sheet(FAKE, "rec", "T1", "image/png", _png(3 * 5 + 2 * 4, 2 * 3 + 4)) == Cells(5, 3)


def test_wrong_media_type_fails() -> None:
    with pytest.raises(NotebookError) as caught:
        check_sheet(FAKE, "rec", "T1", "image/gif", _png(23, 10))
    assert caught.value.where == "rec T1"
    assert "image/gif" in caught.value.problem


def test_sheet_one_pixel_too_wide_fails_with_sizes() -> None:
    with pytest.raises(NotebookError) as caught:
        check_sheet(FAKE, "rec", "T2", "image/png", _png(24, 10))
    assert caught.value.where == "rec T2"
    assert "24 x 10" in caught.value.problem


def test_sheet_too_small_for_one_pixel_cells_fails() -> None:
    with pytest.raises(NotebookError):
        check_sheet(FAKE, "rec", "T1", "image/png", _png(8, 10))


def test_picture_that_fails_the_bench_check_fails() -> None:
    data = _png(23, 10) + b"x"
    with pytest.raises(NotebookError, match="bench's picture check"):
        check_sheet(FAKE, "rec", "T1", "image/png", data)
