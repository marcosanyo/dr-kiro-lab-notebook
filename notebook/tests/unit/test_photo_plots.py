"""The track plot, the picture name check and the page script (task 8.1). All values here are fixture values,
labelled as such, and are never presented as results."""

import hashlib
import re
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from notebook import ink, plots, text
from notebook.errors import NotebookError
from notebook.ink import Authored, Ink
from notebook.pages import photo
from notebook.records import Blob, NotMeasuredValue, Trial

ASSETS = Path(__file__).resolve().parents[2] / "src" / "notebook" / "assets"
RECORD = SimpleNamespace(name="fixture/fake/fake-1", application="fake")


def _trial(measurements) -> Trial:
    blob = Blob("0" * 64, "bench", "image/png", b"fixture", "fixture/blobs/x")
    return Trial(
        seq=3,
        id="T1",
        experiment="E1",
        seed=0,
        params=(),
        inputs={},
        key="k",
        measurements=tuple(measurements),
        picture=blob,
        fake=True,
    )


def test_points_keep_equal_scale_and_put_y_up() -> None:
    drawn = plots.points((0.0, 2.0, 2.0), (0.0, 0.0, 1.0))
    (x0, y0), (x1, y1), (x2, y2) = drawn
    assert y1 == y0 and x2 == x1
    # x spans 2, y spans 1: the same scale makes the y step half the x step, and y up is SVG y down.
    assert (x1 - x0) == pytest.approx(2 * (y1 - y2))
    assert x1 - x0 == pytest.approx(plots.BOX - 2 * plots.MARGIN)


def test_a_track_at_one_place_is_one_point_in_the_centre() -> None:
    assert plots.points((1.0, 1.0), (2.0, 2.0)) == [(80.0, 80.0), (80.0, 80.0)]


def test_track_svg_marks_the_start_with_two_decimals() -> None:
    trial = _trial([("track_x", (0.0, 1.0, 1.0)), ("track_y", (0.0, 0.0, 1.0))])
    page = ink.join(plots.track(RECORD, trial))[0]
    # A square track fills the box, so the cropped box is the whole box (the origin has 2 decimals).
    assert '<svg viewbox="0.00 0.00 160.00 160.00"' in page and "xmlns" not in page
    (points,) = re.findall(r'points="([^"]*)"', page)
    assert all(re.fullmatch(r"-?\d+\.\d\d,-?\d+\.\d\d", p) for p in points.split(" "))
    first = points.split(" ")[0].split(",")
    assert f'cx="{first[0]}" cy="{first[1]}"' in page
    assert "</polyline>" in page and "</circle>" in page
    assert text.TRACK_CAPTION in page


def test_the_track_box_is_cropped_to_the_drawing_so_a_flat_track_leaves_no_empty_band() -> None:
    # Fixture values: x spans 4, y spans 1, so the drawing is a quarter as high as it is wide.
    trial = _trial([("track_x", (0.0, 4.0, 2.0)), ("track_y", (0.0, 0.0, 1.0))])
    page = ink.join(plots.track(RECORD, trial))[0]
    (box,) = re.findall(r'<svg viewbox="([^"]*)" width="([^"]*)" height="([^"]*)"', page)
    left, top, width, height = (float(v) for v in box[0].split())
    assert (box[1], box[2]) == (f"{width:.2f}", f"{height:.2f}")
    assert (left, width) == (0.0, plots.BOX)
    assert height == pytest.approx((plots.BOX - 2 * plots.MARGIN) / 4 + 2 * plots.MARGIN)
    # Every drawn point lies inside the box, a margin from its edge.
    (points,) = re.findall(r'points="([^"]*)"', page)
    xy = [tuple(float(v) for v in p.split(",")) for p in points.split(" ")]
    assert min(y for _, y in xy) == pytest.approx(top + plots.MARGIN, abs=0.01)
    assert max(y for _, y in xy) == pytest.approx(top + height - plots.MARGIN, abs=0.01)


def test_a_track_at_one_place_keeps_the_whole_box() -> None:
    trial = _trial([("track_x", (1.0, 1.0)), ("track_y", (2.0, 2.0))])
    page = ink.join(plots.track(RECORD, trial))[0]
    assert '<svg viewbox="0.00 0.00 160.00 160.00" width="160.00" height="160.00"' in page


def test_a_not_measured_track_is_shown_by_name_and_reason() -> None:
    reason = Authored("fixture reason", "bench", "fixture line 3")
    trial = _trial([("track_x", NotMeasuredValue("not_settled", reason)), ("track_y", (0.0,))])
    segments = plots.track(RECORD, trial)
    page = ink.join(segments)[0]
    assert "<svg" not in page
    assert "track_x: not_settled. " in page and "fixture reason" in page
    assert any(s.text == "fixture reason" and s.ink is Ink.PENCIL for s in segments)


def test_one_track_series_alone_fails() -> None:
    with pytest.raises(NotebookError, match="only track_x"):
        plots.track(RECORD, _trial([("track_x", (0.0,))]))


def test_a_picture_whose_bytes_do_not_match_its_hash_fails() -> None:
    trial = _trial([])
    with pytest.raises(NotebookError, match="not its blob hash"):
        photo.picture_file(RECORD, trial)
    named = replace(trial.picture, digest=hashlib.sha256(b"fixture").hexdigest())
    picture = photo.picture_file(RECORD, replace(trial, picture=named))
    assert picture.path == f"p/{named.digest}.png" and picture.data == b"fixture"


def test_the_script_makes_no_request_and_loads_no_code() -> None:
    script = (ASSETS / "notebook.js").read_text(encoding="utf-8")
    for banned in (
        "fetch",
        "XMLHttpRequest",
        "WebSocket",
        "sendBeacon",
        "EventSource",
        "import",
        "http:",
        "https:",
        "eval",
        'createElement("script")',
        ".src",
    ):
        assert banned not in script, banned


def test_the_script_reads_the_interval_of_each_picture_from_its_figure() -> None:
    script = (ASSETS / "notebook.js").read_text(encoding="utf-8")
    css = (ASSETS / "notebook.css").read_text(encoding="utf-8")
    assert "--cell-interval" not in css and "--cell-interval" not in script
    assert '"interval"' in script and "prefers-reduced-motion: reduce" in script
    assert '"first"' in script and "data-whole-src" in script
