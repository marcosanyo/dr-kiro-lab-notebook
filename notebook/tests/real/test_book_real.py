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
        "--app", str(ROOT / "wind-tunnel" / "notebook"),
        "--app", str(ROOT / "body-lab" / "notebook"),
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


def test_the_front_page_has_two_doors_and_each_application_opens_on_its_notebook(site):
    page, found = _page(site, "index.html")
    assert found.classes["door"] == 2 and found.classes["door-day"] == 1 and found.classes["door-night"] == 1
    assert found.links.index("wind-tunnel/index.html") < found.links.index("body-lab/index.html")
    assert "<h2" in page and "skeleton" in page and found.classes["mode-toggle"] == 0
    assert (site / "wind-tunnel" / "index.html").read_bytes() == (
        site / "wind-tunnel/wt-004.html"
    ).read_bytes()
    assert (site / "body-lab" / "index.html").read_bytes() == (site / "body-lab/body-2.html").read_bytes()


def test_each_application_opens_in_its_own_theme_and_only_the_robot_has_decoration(site):
    day, day_found = _page(site, "wind-tunnel/index.html")
    night, night_found = _page(site, "body-lab/index.html")
    assert 'data-app="wind-tunnel" data-mode="day" data-pen="blue"' in day
    assert 'data-app="body-lab" data-mode="night" data-pen="orange"' in night
    assert "<svg" not in re.sub(
        r'<svg class="icon".*?</svg>|<svg class="chart".*?</svg>', "", day, flags=re.S
    )
    assert night_found.classes["deco"] >= 6 and night_found.classes["deco-bat"] >= 3
    assert "deco-pumpkin" not in night and day_found.classes["deco"] == 0


def test_the_cases_and_the_cards_of_the_open_application(site):
    page, found = _page(site, "body-lab/body-2.html")
    assert found.classes["case-tab"] == 2 and found.classes["is-on"] >= 1
    assert page.index("CASE 1") < page.index("CASE 2") and "THE WIND TUNNEL" in page
    assert found.classes["card"] == 2 and found.classes["is-open"] == 1
    assert "/wind-tunnel/" in found.links and "body-1.html" in found.links and "/" in found.links
    assert found.classes["mode-toggle"] == 1
    _, tunnel = _page(site, "wind-tunnel/wt-004.html")
    assert tunnel.classes["card"] == 3 and tunnel.classes["is-open"] == 1
    assert "/body-lab/" in tunnel.links


def test_every_id_of_a_page_is_unique(site):
    for name in sorted(p.relative_to(site).as_posix() for p in site.glob("*/*.html")):
        ids = _page(site, name)[1].ids
        assert [i for i, n in Counter(ids).items() if n > 1] == [], name


def test_body_2_states_its_story_from_the_choice_file_and_the_record(site, loaded):
    page, found = _page(site, "body-lab/body-2.html")
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
    page, found = _page(site, "body-lab/body-2.html")
    assert found.classes["tile"] == 3
    tiles = re.findall(r'<p class="tile-big"><span class="ink-p">(\d/\d)</span>', page)
    assert tiles == ["2/2", "1/2", "0/2"]
    assert found.classes["run-fail"] == 3 and found.classes["run-pass"] == 3
    assert "Move ahead by about 0.45 m" in page


def test_the_wind_tunnel_best_counts_only_steady_trials(site):
    page, _ = _page(site, "wind-tunnel/wt-004.html")
    assert '<p class="note-big"><span class="ink-p">0.9930 cd</span>' in page or "0.993" in page
    stopped, found = _page(site, "wind-tunnel/wt-002.html")
    assert found.classes["polaroid"] == 2
    assert "No trial counts toward the best yet." in stopped


def test_a_session_without_a_trial_has_no_photo_and_no_chart(site):
    page, found = _page(site, "wind-tunnel/wt-003.html")
    assert found.classes["polaroid"] == 0 and found.classes["chart"] == 0
    assert "stopped:" in page and "nothing to show here" in page


def test_body_1_has_no_table_and_says_so(site):
    page, found = _page(site, "body-lab/body-1.html")
    assert found.classes["rule"] == 0
    assert "no discovered spec in the record" in page


def _closed_part(page: str) -> str:
    """The page without its opened notes: what is seen before anything is pressed."""
    return re.sub(r'<section class="sticky-open">.*?</details>', "", page, flags=re.S)


def test_the_top_of_a_page_has_no_exponent_numbers(site):
    for name in ("body-lab/body-2.html", "body-lab/body-1.html", "wind-tunnel/wt-004.html"):
        page = _closed_part((site / name).read_text(encoding="utf-8"))
        text = re.sub(r"<[^>]*>", " ", page)
        assert not re.search(r"\d[eE][-+]?\d", text), name


def test_the_two_highlight_photos_play_together_with_a_slider_and_say_how_far_they_came(site):
    page, found = _page(site, "body-lab/body-2.html")
    assert found.classes["polaroids"] == 1 and 'data-sync="yes"' in page
    assert 'data-interval="200"' in page and 'data-whole-src="p/' in page
    first = re.search(r'<span class="reel-clock" data-frame="0" hidden="hidden">(.*?)</span>', page)
    assert first and "t = 0.2 s" in first.group(1)
    assert "forward" in page and " cm" in page


def test_the_chart_names_at_most_four_steps_each_with_a_hypothesis(site):
    page, found = _page(site, "body-lab/body-2.html")
    names = re.findall(r'<text class="ch-note[^"]*"[^>]*>(H\d+: [+-][^<]*)</text>', page)
    assert 1 <= len(names) <= 4 and all(re.fullmatch(r"H\d+: [+-][\d.]+ (cm|m)", n) for n in names), names


def test_titles_are_marked_as_our_notes_and_the_other_pages_have_every_retaken_picture(site):
    page, found = _page(site, "body-lab/body-2.html")
    assert found.classes["ours"] == 2
    pictures = set(re.findall(r'src="(p/[0-9a-f]{64}\.png)"', page))
    assert len(pictures) >= 39  # every trial's retaken sheet (the recorded sheets load only when asked)


def test_the_plan_steps_and_the_rule_details_are_closed_notes(site):
    page, found = _page(site, "body-lab/body-2.html")
    assert found.classes["plan-step"] == 13 and found.classes["rule-more"] == 14


def test_an_opened_note_shows_headings_and_predictions_as_they_read_not_as_they_were_written(site):
    for name in ("body-lab/body-2.html", "wind-tunnel/wt-004.html", "body-lab/body-1.html"):
        page, found = _page(site, name)
        assert "```" not in page and "### " not in page and "[[prediction]]" not in page, name
        assert found.classes["frozen-title"] >= 1
    page, _ = _page(site, "wind-tunnel/wt-004.html")
    # "cd in [0.5, 1.25] when aspect = 3, ... -> hit": the range, the conditions and the outcome of H3.P1.
    line = re.search(r'<li id="H3.P1">(.*?)</li>', page, re.S)
    assert line
    text = re.sub(r"<[^>]*>", "", line.group(1))
    assert "cd in [0.5, 1.25] when aspect = 3" in text and "→ hit" in text.replace("&rarr;", "→")


def test_the_sticky_notes_are_the_ones_the_choice_file_names(site, loaded):
    page, found = _page(site, "wind-tunnel/wt-004.html")
    assert found.classes["note"] == 3
    assert "H5.P3" in page and "missed:" in page and "was expected in" in page
    assert "rules rejected" not in page
    body_2, _ = _page(site, "body-lab/body-2.html")
    assert "rules rejected" in body_2
    stopped, _ = _page(site, "wind-tunnel/wt-002.html")
    assert "used, of the whole budget" in stopped


def test_the_lines_under_a_moving_photo_share_one_place_so_the_page_does_not_jump(site):
    page, _ = _page(site, "body-lab/body-2.html")
    assert page.count('<span class="reel-lines">') >= 41  # the two highlight photos and every trial
    css = (site / "body-lab" / "a" / "notebook.css").read_text(encoding="utf-8")
    assert re.search(r"\.reel-lines \{[^}]*min-height", css)
    assert re.search(r"\.newbest \{[^}]*white-space: nowrap", css)


def test_a_narrow_screen_has_one_column_of_cards_so_the_page_does_not_scroll_sideways(site):
    css = (site / "body-lab" / "a" / "notebook.css").read_text(encoding="utf-8")
    assert re.search(
        r"@media \(max-width: 900px\) \{\s*\.hyps \{\s*grid-template-columns: minmax\(0, 1fr\)", css
    )
