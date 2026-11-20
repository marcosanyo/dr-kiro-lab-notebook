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
    assert night_found.classes["deco"] >= 6 and night_found.classes["deco-bat"] >= 4
    assert "deco-pumpkin" not in night and day_found.classes["deco"] == 0


def test_an_application_page_has_no_switch_and_no_tabs_only_two_small_links(site):
    for name, other in (
        ("body-lab/body-2.html", "/wind-tunnel/index.html"),
        ("wind-tunnel/wt-004.html", "/body-lab/index.html"),
    ):
        page, found = _page(site, name)
        assert found.classes["mode-toggle"] == 0 and found.classes["case-tab"] == 0
        assert "notebook-mode" not in (site / name.split("/")[0] / "a" / "notebook.js").read_text()
        assert found.classes["lab-links"] == 1 and "/index.html" in found.links and other in found.links
        assert page.count('href="/index.html"') >= 1
    page, found = _page(site, "wind-tunnel/wt-004.html")
    assert 'data-mode="day"' in page and "CASE 2" not in page


def test_the_cards_of_an_application_and_its_stopped_sessions_below_them_small(site):
    page, found = _page(site, "wind-tunnel/wt-004.html")
    assert found.classes["card"] == 3 and found.classes["card-stopped"] == 2 and found.classes["is-open"] == 1
    assert found.classes["shelf-stopped"] == 1
    assert page.index('class="shelf"') < page.index('class="shelf-stopped"') < page.index('id="book"')
    assert "wt-002.html" in found.links and "wt-003.html" in found.links
    body, body_found = _page(site, "body-lab/body-2.html")
    assert body_found.classes["card"] == 3 and body_found.classes["card-stopped"] == 0
    assert "body-1.html" in body_found.links


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


def test_the_wind_tunnel_best_is_the_lowest_cd_of_all_runs_of_the_session(site, loaded_all):
    for session in ("wt-004", "wt-002"):
        page, found = _page(site, f"wind-tunnel/{session}.html")
        cds = [dict(t.measurements)["cd"] for t in loaded_all[session].trials]
        lowest = min(c for c in cds if isinstance(c, float))
        assert f"{lowest:.3f}" in page, session
        assert "No trial counts toward the best yet." not in page
        assert found.classes["polaroid"] == 2


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


def _moving_pixels(trial, layout_gap=4, columns=3, rows=2):
    """Pixels that differ between the first two cells of a wind-tunnel picture: how much the flow moves."""
    from notebook import png

    image = png.decode(trial.picture.data, trial.id)
    width = (image.width - (columns - 1) * layout_gap) // columns
    height = (image.height - (rows - 1) * layout_gap) // rows
    stride = image.width * image.channels
    differing = 0
    for y in range(height):
        first = image.pixels[y * stride : y * stride + width * image.channels]
        start = (width + layout_gap) * image.channels
        second = image.pixels[y * stride + start : y * stride + start + width * image.channels]
        differing += sum(1 for a, b in zip(first, second, strict=True) if abs(a - b) > 8)
    return differing


def test_the_wind_tunnel_highlight_shows_a_flow_that_moves_and_the_same_flow_made_quiet(site, loaded_all):
    page, found = _page(site, "wind-tunnel/wt-004.html")
    assert found.classes["polaroid"] == 2
    assert "WHERE IT STARTED" in page.upper() and "THE QUIET BODY" in page.upper()
    record = loaded_all["wt-004"]
    trials = {t.id: t for t in record.trials}
    shedding = _moving_pixels(trials["T1"])
    steady = _moving_pixels(trials["T12"])
    assert shedding > 5 * max(steady, 1), (shedding, steady)
    assert dict(trials["T1"].measurements)["shedding"] == 1.0
    assert dict(trials["T12"].measurements)["shedding"] == 0.0
    # The two highlight photos are those trials, one after the other.
    first = re.search(r'class="polaroid[^"]*">.*?<span class="ink-p">(T\d+)</span>', page, re.S)
    assert first and first.group(1) == "T1"


@pytest.fixture(scope="module")
def loaded_all() -> dict[str, records.RecordModel]:
    return {r.session: r for r in records.load(ROOT / "sessions")}


def test_the_chart_is_one_line_that_fills_its_frame_and_has_no_scattered_dots(site):
    for name in ("body-lab/body-2.html", "wind-tunnel/wt-004.html", "body-lab/body-1.html"):
        page, found = _page(site, name)
        assert found.classes["ch-line"] == 1 and found.classes["ch-dot"] == 0, name
        path = re.search(r'<path class="ch-line" d="([^"]*)"', page)
        assert path, name
        ys = [float(y) for y in re.findall(r"[ V]([0-9.]+)(?=[HV]|$)", path.group(1))]
        assert ys and min(ys) > 41 and max(ys) < 215, (name, min(ys), max(ys))  # the frame is 40 to 220
        assert "hollow" not in page


def _text_of(page: str, start: str, end: str) -> str:
    part = page[page.index(start) : page.index(end)]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", part)).strip()


def test_the_story_of_body_2_says_what_happened_in_three_steps_from_the_record(site, loaded_all):
    page, found = _page(site, "body-lab/body-2.html")
    assert found.classes["story-step"] == 3
    story = _text_of(page, 'id="story"', 'class="chips"')
    record = loaded_all["body-2"]
    registered = sum(len(h.predictions) for h in record.hypotheses)
    assert f"Dr. Kiro wrote {registered} predictions, each before its experiment ran." in story
    assert "13 missed. 8 rules were struck out and rewritten." in story
    assert "Another Kiro, given only this spec, did the task in 2 of 2 tries. With nothing, 0 of 2." in story


def test_the_story_of_the_wind_tunnel_does_not_claim_a_reader_that_was_not_run(site):
    page, found = _page(site, "wind-tunnel/wt-004.html")
    story = _text_of(page, 'id="story"', 'class="chips"')
    assert "Another Kiro" not in story and found.classes["tile"] == 0
    assert "4 rows are validated and can be trusted; 2 are only partly tested or observed" in story
    assert "No second Kiro has been run on this spec yet." in story
    # The miss did not strike a rule out; the story names the row it kept from being validated.
    assert "1 missed. No rule was struck out, but the miss kept R5 at partly instead of validated." in story


def test_the_stopped_sessions_tell_what_they_can(site):
    page, _ = _page(site, "wind-tunnel/wt-003.html")
    assert "No prediction was written" in page
    page, _ = _page(site, "wind-tunnel/wt-002.html")
    assert "checked predictions came true before the session stopped." in page
    assert "nothing yet for a next Kiro to read" in page


def test_the_reader_comes_right_after_the_highlight_and_every_section_says_what_it_is(site):
    page, _ = _page(site, "body-lab/body-2.html")
    ids = [page.index(f'id="{i}"') for i in ("highlight", "reader", "spec", "plan", "experiments")]
    assert ids == sorted(ids)
    assert "A struck line was believed, tested, and proved wrong; the line under it replaced it." in page
    assert "Each card: what Dr. Kiro predicted before the run, and what happened." in page
    text = re.sub(r"<[^>]*>", "", page)
    assert "predictions, written before the run, came true" in text and "predictions hit" not in text


def test_the_wind_tunnel_line_is_the_lowest_cd_of_every_run_with_a_flag_where_the_vortices_stop(
    site, loaded_all
):
    page, found = _page(site, "wind-tunnel/wt-004.html")
    record = loaded_all["wt-004"]
    cds = [dict(t.measurements)["cd"] for t in record.trials]
    lowest = min(c for c in cds if isinstance(c, float))
    assert f"{lowest:.3f}" in page  # the best note and the axis
    steady = next(t for t in record.trials if dict(t.measurements)["shedding"] == 0.0)
    assert found.classes["ch-mark"] == 1 and "vortices stop" in page
    assert steady.id == "T8"  # the first trial without shedding
    assert "The dashed line marks the first trial where shedding = 0." in re.sub(r"<[^>]*>", "", page)
    body, body_found = _page(site, "body-lab/body-2.html")
    assert body_found.classes["ch-mark"] == 0


def test_the_chart_line_wavers_like_a_pencil_line_and_is_the_same_every_build(site):
    page, _ = _page(site, "body-lab/body-2.html")
    path = re.search(r'<path class="ch-line" d="([^"]*)"', page).group(1)
    assert path.count("L") > 40  # many short pieces, not four straight strokes
    again = re.search(r'<path class="ch-line" d="([^"]*)"', _page(site, "body-lab/body-2.html")[0]).group(1)
    assert path == again


def test_each_retaken_picture_has_a_corner_map_with_one_dot_per_cell(site):
    page, _found = _page(site, "body-lab/body-2.html")
    maps = re.findall(r'<svg class="corner-map".*?</svg>', page, re.S)
    assert maps
    for one in maps:
        dots = re.findall(r'class="map-dot"[^>]*data-frame="(\d+)"', one)
        assert dots == [str(k) for k in range(25)]
        lines = re.findall(r'class="map-line"[^>]*data-frame="(\d+)"', one)
        assert lines == [str(k) for k in range(25)]
        # Only the last travelled line and the last dot show without the script.
        assert one.count('hidden="hidden"') == 48
        assert 'class="map-route"' in one and "10 cm" in one


def test_the_changed_body_shows_the_earlier_spec_beside_its_own_on_the_same_request(site):
    page, found = _page(site, "body-lab/body-3.html")
    story = _text_of(page, 'id="story"', 'class="chips"')
    assert "Another Kiro, given only this spec, did the task in 2 of 2 tries. With nothing, 0 of 2." in story
    assert "Given the spec of body-2, written before the body changed, 0 of 2." in story
    reader = _text_of(page, 'id="reader"', 'id="spec"')
    # Three columns: body-2's spec tried on this body, this session's spec, nothing.
    assert found.classes["tile-borrowed"] == 1 and found.classes["tile"] == 3
    assert reader.index("Spec of an earlier session") < reader.index("Spec only") < reader.index("Nothing")
    # The earlier spec's rules it relied on link to body-2's page, and are quoted from body-2's table.
    assert "body-2.html#row-R11" in found.links and "body-2.html#row-R9" in found.links
    assert "Constant c1 gives x" in reader
    # body-2's own page still shows only its own request, on its own body.
    other, _ = _page(site, "body-lab/body-2.html")
    own = _text_of(other, 'id="reader"', 'id="spec"')
    assert "Move ahead by about 0.45 m" in own and "Crawl ahead" not in own


def test_the_body_chip_comes_from_the_record_or_from_a_person(site):
    page, _ = _page(site, "body-lab/body-3.html")
    chips = _text_of(page, 'class="chips"', "</ul>")
    assert "body" in chips and ">b<" in page[page.index('class="chips"') :]
    old, _ = _page(site, "body-lab/body-2.html")
    assert 'class="ink-c">a<' in old[old.index('class="chips"') :]
