"""The moving picture and the track plot on the committed records (task 8.1). The sizes and sample counts
asserted are facts of the committed records (requirements introduction and Decision 15), not results."""

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from notebook import ink, layouts, plots, records
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
        if tag == "figure":
            self.figure = dict(attrs)
        elif tag == "img":
            self.img = dict(attrs)
        elif tag == "button":
            self.actions.append(dict(attrs)["data-action"])


@pytest.mark.parametrize(
    ("session_id", "tid", "expected"),
    [
        (
            "body-2",
            "T12",
            {"columns": "5", "rows": "2", "gap": "0", "tile-width": "320", "tile-height": "180"},
        ),
        (
            "wt-004",
            "T1",
            {"columns": "3", "rows": "2", "gap": "4", "tile-width": "400", "tile-height": "200"},
        ),
    ],
)
def test_figure_attributes_for_both_layouts(loaded, table, session_id, tid, expected) -> None:
    record = loaded[session_id]
    trial = _trial(record, tid)
    segments, picture = photo.photo(record, trial, table[record.application], "../../")
    parser = _Figure()
    parser.feed(ink.join(segments)[0])
    assert {key[5:]: value for key, value in parser.figure.items() if key.startswith("data-")} == expected
    assert parser.figure["class"] == f"photo tilt-{int(tid[1:]) % 5}"
    assert parser.img["src"] == f"../../{picture.path}"
    assert parser.actions == ["play", "pause", "step", "sheet"]


def test_every_picture_is_named_by_the_sha256_of_its_bytes(loaded, table) -> None:
    for record in loaded.values():
        for trial in record.trials:
            _, picture = photo.photo(record, trial, table[record.application], "")
            assert picture.data == trial.picture.data
            assert picture.path == f"p/{hashlib.sha256(picture.data).hexdigest()}.png"


def test_body_2_t12_track_has_one_point_per_recorded_sample(loaded) -> None:
    record = loaded["body-2"]
    trial = _trial(record, "T12")
    samples = dict(trial.measurements)["track_x"]
    page = ink.join(plots.track(record, trial))[0]
    (points,) = re.findall(r'<polyline points="([^"]*)"', page)
    assert len(points.split(" ")) == len(samples) == 51
    assert "xmlns" not in page and "http" not in page


def test_wind_tunnel_trials_have_no_track(loaded) -> None:
    record = loaded["wt-004"]
    assert plots.track(record, record.trials[0]) == []


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
    segments, _ = photo.photo(record, trial, table[record.application], "")
    segments += plots.track(record, trial)
    for segment in segments:
        if segment.ink is not ink.Ink.DRKIRO:
            assert scanner.scan_text(segment.text, level, segment.source) == [], segment
