"""The opened notebooks of the committed records, as built (notebook-shelf design 4 to 9). Every number
asserted here is read from the record or the choice file by the same code the page uses, or is a count
that the record's own entries give."""

import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import pytest

from notebook import cli, records

ROOT = Path(__file__).resolve().parents[3]


def _argv(out: Path) -> list[str]:
    return [
        "--sessions", str(ROOT / "sessions"),
        "--requests", str(ROOT / "build-from-spec" / "requests"),
        "--choices", str(ROOT / "notebook" / "choices"),
        "--layouts", str(ROOT / "notebook" / "layouts.toml"),
        "--words", str(ROOT / "notebook" / "commentary-words.txt"),
        "--scan-config", str(ROOT / "body-lab" / "adapter" / "scan_sources.toml"),
        "--scan-config", str(ROOT / "wind-tunnel" / "adapter" / "scan_sources.toml"),
        "--stop-list", str(ROOT / ".kiro" / "blind-scan" / "stop-list.txt"),
        "--out", str(out),
    ]  # fmt: skip


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("book-build") / "site"
    assert cli.main(_argv(out)) == 0
    return out


@pytest.fixture(scope="module")
def loaded() -> dict[str, records.RecordModel]:
    return {r.session: r for r in records.load(ROOT / "sessions")}


class _Ids(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.classes: Counter[str] = Counter()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(a["id"])
        for name in (a.get("class") or "").split():
            self.classes[name] += 1
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])


def _page(site: Path, name: str) -> tuple[str, _Ids]:
    page = (site / name).read_text(encoding="utf-8")
    parsed = _Ids()
    parsed.feed(page)
    return page, parsed


def test_the_first_page_is_the_notebook_the_cover_file_names(site):
    assert (site / "index.html").read_bytes() == (site / "body-lab-body-2.html").read_bytes()


def test_the_cases_and_the_cards_of_the_open_lab(site):
    page, found = _page(site, "body-lab-body-2.html")
    assert found.classes["case-tab"] == 2 and found.classes["is-on"] >= 1
    assert found.classes["card"] == 2 and found.classes["is-open"] == 1
    assert "wind-tunnel-wt-004.html" in found.links and "body-lab-body-1.html" in found.links
    assert found.classes["mode-toggle"] == 1
    _, tunnel = _page(site, "wind-tunnel-wt-004.html")
    assert tunnel.classes["card"] == 3 and tunnel.classes["is-open"] == 1


def test_every_id_of_a_page_is_unique(site):
    for name in sorted(p.name for p in site.glob("*.html")):
        ids = _page(site, name)[1].ids
        assert [i for i, n in Counter(ids).items() if n > 1] == [], name


def test_body_2_states_its_story_from_the_choice_file_and_the_record(site, loaded):
    page, found = _page(site, "body-lab-body-2.html")
    assert "The Reversed Wave" in page and "a wave meant to walk forward went 0.20 m back" in page
    assert found.classes["polaroid"] == 2 and found.classes["note"] == 3
    record = loaded["body-2"]
    hits = sum(1 for o in record.outcomes if o.outcome == "hit")
    assert f"{hits}/{len(record.outcomes)}" in page
    assert f'<span class="ink-p">{len(record.trials)}</span> ' in page
    assert found.classes["hyp"] == len(record.hypotheses) == 11
    assert found.classes["rule"] == 14 and found.classes["struck"] == 8
    assert found.classes["plan-step"] == 13


def test_body_2_shows_the_readers_three_results(site):
    page, found = _page(site, "body-lab-body-2.html")
    assert found.classes["tile"] == 3
    tiles = re.findall(r'<p class="tile-big"><span class="ink-p">(\d/\d)</span>', page)
    assert tiles == ["2/2", "1/2", "0/2"]
    assert found.classes["run-fail"] == 3 and found.classes["run-pass"] == 3
    assert "Move ahead by about 0.45 m" in page


def test_the_wind_tunnel_best_counts_only_steady_trials(site):
    page, _ = _page(site, "wind-tunnel-wt-004.html")
    assert '<p class="note-big"><span class="ink-p">0.9930 cd</span>' in page or "0.993" in page
    stopped, found = _page(site, "wind-tunnel-wt-002.html")
    assert found.classes["polaroid"] == 2
    assert "No trial counts toward the best yet." in stopped


def test_a_session_without_a_trial_has_no_photo_and_no_chart(site):
    page, found = _page(site, "wind-tunnel-wt-003.html")
    assert found.classes["polaroid"] == 0 and found.classes["chart"] == 0
    assert "stopped:" in page and "nothing to show here" in page


def test_body_1_has_no_table_and_says_so(site):
    page, found = _page(site, "body-lab-body-1.html")
    assert found.classes["rule"] == 0
    assert "no discovered spec in the record" in page
