"""The moving picture and the track plot on the committed records (task 8.1). The sizes and sample counts
asserted are facts of the committed records (requirements introduction and Decision 15), not results."""

import hashlib
from html.parser import HTMLParser
from pathlib import Path

import pytest

from notebook import ink, layouts, records
from notebook.pages import photo

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = ROOT / "sessions"
LAYOUTS = ROOT / "notebook" / "layouts.toml"


@pytest.fixture(scope="module")
def loaded() -> dict[str, records.RecordModel]:
    return {r.session: r for r in records.load(SESSIONS)}


@pytest.fixture(scope="module")
def table() -> dict[str, layouts.Layout]:
    return layouts.load(LAYOUTS)


def _trial(record: records.RecordModel, tid: str) -> records.Trial:
    (trial,) = [t for t in record.trials if t.id == tid]
    return trial


class _Figure(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.figure: dict[str, str | None] = {}
        self.img: dict[str, str | None] = {}
        self.actions: list[str | None] = []

    def handle_starttag(self, tag, attrs) -> None:
        # The first figure and picture of the page text (Requirement 7.9).
        if tag == "figure" and not self.figure:
            self.figure = dict(attrs)
        elif tag == "img" and not self.img:
            self.img = dict(attrs)
        elif tag == "button":
            self.actions.append(dict(attrs)["data-action"])


@pytest.mark.parametrize(
    ("session_id", "tid", "expected"),
    [
        (
            "body-2",
            "T12",
            # The one figure of a body-lab trial is its magnified picture; the whole sheet is only named.
            {
                "columns": "5",
                "rows": "2",
                "gap": "0",
                "tile-width": None,
                "tile-height": None,
                "interval": "220",
                "whole-src": None,
                "whole-columns": "5",
                "whole-rows": "2",
                "whole-interval": "220",
                "whole-gap": "0",
                "whole-tile-width": "320",
                "whole-tile-height": "180",
            },
        ),
        (
            "wt-004",
            "T1",
            {
                "columns": "3",
                "rows": "2",
                "gap": "4",
                "tile-width": "400",
                "tile-height": "200",
                "interval": "150",
                "crop-left": None,
                "crop-top": None,
                "crop-width": None,
                "crop-height": None,
            },
        ),
    ],
)
def test_figure_attributes_for_both_layouts(loaded, table, session_id, tid, expected) -> None:
    record = loaded[session_id]
    trial = _trial(record, tid)
    segments, pictures = photo.photo(record, trial, table[record.application])
    picture = pictures[0]
    parser = _Figure()
    parser.feed(ink.join(segments)[0])
    data = {key[5:]: value for key, value in parser.figure.items() if key.startswith("data-")}
    assert data.keys() == expected.keys()
    for key, value in expected.items():
        if value is not None:
            assert data[key] == value, key
    # The site is flat: the picture is linked from the site root, without `..` (design N28).
    assert picture.path == f"p/{trial.picture.digest}.png"
    if "crop-width" in data:
        # The crop is a window inside one cell, with the cell's shape.
        left, top, width, height = (int(data[f"crop-{k}"]) for k in ("left", "top", "width", "height"))
        assert left >= 0 and top >= 0 and left + width <= 400 and top + height <= 200
        assert abs(width * 200 - height * 400) <= 400
    if session_id == "body-2":
        # The sheet of the whole picture is only named by the figure; the page shows the magnified picture.
        assert data["whole-src"] == picture.path
        assert parser.img["src"] != picture.path
        assert parser.img["class"] == "first-cell"
        assert parser.actions == ["play", "pause", "step", "sheet", "back"]
    else:
        assert parser.figure["class"] == f"photo tilt-{int(tid[1:]) % 5}"
        assert parser.img["src"] == picture.path
        assert parser.actions == ["play", "pause", "step", "sheet"]


def test_a_body_lab_photo_is_the_magnified_figure_alone(loaded, table) -> None:
    record = loaded["body-2"]
    trial = _trial(record, "T12")
    layout = table[record.application]
    row, row_files = photo.photo(record, trial, layout, "large")
    moving, enlarged, files = photo.figures(record, trial, layout, "large")
    # No figure shows the sheet of the whole picture side by side, and nothing wraps two pictures in a row.
    assert moving == [] and ink.join(row)[0] == ink.join(enlarged)[0]
    assert ink.join(row)[0].count("<img") == 1 and "photo-pair" not in ink.join(row)[0]
    assert files == row_files and len(files) == 2
    # A wind-tunnel trial has no magnified picture: `photo` gives the moving one alone.
    tunnel = loaded["wt-004"]
    moving, enlarged, files = photo.figures(tunnel, _trial(tunnel, "T1"), table[tunnel.application])
    assert enlarged == [] and len(files) == 1
    assert photo.photo(tunnel, _trial(tunnel, "T1"), table[tunnel.application]) == (moving, files)


def test_every_picture_is_named_by_the_sha256_of_its_bytes(loaded, table) -> None:
    for record in loaded.values():
        for trial in record.trials:
            _, (picture, *_) = photo.photo(record, trial, table[record.application])
            assert picture.data == trial.picture.data
            assert picture.path == f"p/{hashlib.sha256(picture.data).hexdigest()}.png"


def test_script_and_parts_pass_the_builder_level_scan(loaded, table) -> None:
    from bench.scan.levels import AUTHOR_LEVEL
    from bench.scan.scan import Scanner

    scanner = Scanner.from_config(
        [
            ROOT / "body-lab" / "adapter" / "scan_sources.toml",
            ROOT / "wind-tunnel" / "adapter" / "scan_sources.toml",
        ],
        ROOT / ".kiro" / "blind-scan" / "stop-list.txt",
    )
    level = AUTHOR_LEVEL["bench"]
    script = (ROOT / "notebook" / "src" / "notebook" / "assets" / "notebook.js").read_text(encoding="utf-8")
    assert scanner.scan_text(script, level, "notebook.js") == []
    record = loaded["body-2"]
    trial = _trial(record, "T12")
    segments, _ = photo.photo(record, trial, table[record.application])
    for segment in segments:
        if segment.ink is not ink.Ink.DRKIRO:
            assert scanner.scan_text(segment.text, level, segment.source) == [], segment


def test_the_magnified_figure_moves_and_names_the_whole_picture(loaded, table) -> None:
    record = loaded["body-2"]
    layout = table[record.application]
    trial = _trial(record, "T12")
    whole, enlarged, files = photo.figures(record, trial, layout, "large")
    enlarged_html = ink.join(enlarged)[0]
    assert whole == [] and "data-start" not in enlarged_html
    # The magnified sheet has the layout's grid, no gap, and the layout's interval.
    assert 'data-columns="5" data-rows="2" data-gap="0"' in enlarged_html
    assert 'data-interval="220"' in enlarged_html
    # The whole sheet is named for the script, with its own cell size and gap; it is not an image of the page.
    assert f'data-whole-src="{files[0].path}"' in enlarged_html
    assert enlarged_html.count("<img") == 1 and files[0].path not in enlarged_html.split("data-whole-src")[0]
    assert enlarged_html.count("<button") == 5
    # A body-lab trial without a magnified picture (a lab card) shows its first cell and waits for play.
    card, none, _ = photo.figures(record, trial, layout, "small", magnified=False)
    card_html = ink.join(card)[0]
    assert none == [] and 'data-start="first"' in card_html and 'class="first-cell"' in card_html
    assert card_html.count("<button") == 3 and "sheet" not in card_html.split("<figcaption")[1]
    # A wind-tunnel picture is the only picture of its trial: it moves on its own, every 150 ms.
    tunnel = loaded["wt-004"]
    moving, none, _ = photo.figures(tunnel, _trial(tunnel, "T1"), table[tunnel.application])
    assert none == [] and "data-start" not in ink.join(moving)[0] and "first-cell" not in ink.join(moving)[0]
