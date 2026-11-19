"""The cover and the session page's pinned pictures on the committed records (task 8.2). The ids asserted are
facts of the committed records and of the approved cover and choice files (requirements introduction and
Decisions 36, 37), not results the notebook claims."""

import re
from pathlib import Path

import pytest

from notebook import choices, ink, layouts, readerrequest, readerruns, records, text, views, words
from notebook.ink import Ink
from notebook.pages import cover, photo, session

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = ROOT / "sessions"
REQUESTS = ROOT / "build-from-spec" / "requests"
CHOICES = ROOT / "notebook" / "choices"
LAYOUTS = ROOT / "notebook" / "layouts.toml"
WORDS = ROOT / "notebook" / "commentary-words.txt"


@pytest.fixture(scope="module")
def loaded() -> list[records.RecordModel]:
    return records.load(SESSIONS)


@pytest.fixture(scope="module")
def table() -> dict[str, layouts.Layout]:
    return layouts.load(LAYOUTS)


@pytest.fixture(scope="module")
def built(loaded, table):
    runs = readerruns.load(SESSIONS)
    return cover.page(
        loaded, choices.load_cover(CHOICES, loaded), table, runs, readerrequest.load(REQUESTS, runs)
    )


def _by_session(loaded, session_id: str) -> records.RecordModel:
    (record,) = [r for r in loaded if r.session == session_id]
    return record


def _trial(record: records.RecordModel, tid: str) -> records.Trial:
    (trial,) = [t for t in record.trials if t.id == tid]
    return trial


def test_cover_shows_body_2_h4_p1_with_t12_its_track_and_miss(loaded, built) -> None:
    segments, pictures = built
    page = ink.join(segments)[0]
    body_2 = _by_session(loaded, "body-2")
    t12 = _trial(body_2, "T12")
    assert pictures[0].path == f"p/{t12.picture.digest}.png"
    large = re.search(r'<figure class="photo tilt-\d photo-large"[^>]*><img src="([^"]+)"', page)
    assert large is not None and large.group(1) == pictures[0].path
    assert page.count("<polyline") == 1  # the track of T12, beside the photo
    assert '<span class="ink-p">H4.P1</span>' in page
    statement = next(h for h in body_2.hypotheses if h.id == "H4").statement.text
    assert f'<span class="ink-k">{statement}</span>' in page
    assert '<span class="miss"><span class="ink-p">miss</span></span>' in page
    assert re.search(r'<span class="miss-value"><span class="ink-p">-0\.2047 m</span></span>', page)


def test_cover_rows_are_r4_rejected_and_r5_replacing_it(built) -> None:
    page = ink.join(built[0])[0]
    rows = re.findall(r'href="body-lab-body-2\.html#row-(R\d+)"', page)
    assert rows == ["R4", "R5"]
    assert (
        '<li class="rule-card row-rejected st-rejected"><span class="rule-head">'
        '<a href="body-lab-body-2.html#row-R4">' in page
    )
    assert '<span class="stamp stamp-rejected"><span class="ink-s">rejected</span></span>' in page
    # R5 is one line under R4 ("replaced by R5 ..."), not a second card with its own stamp.
    replaced = '<span class="cover-replaced"><span class="ink-c">replaced by </span>'
    assert replaced + '<a href="body-lab-body-2.html#row-R5">' in page
    assert page.count('class="rule-card') == 1
    assert '<span class="stamp stamp-observed">' not in page


def test_cover_cards_and_labels(loaded, built) -> None:
    segments, pictures = built
    page = ink.join(segments)[0]
    t31 = _trial(_by_session(loaded, "body-2"), "T31")
    wt_t1 = _trial(_by_session(loaded, "wt-004"), "T1")
    # The miss shows its recorded sheet and its magnified picture first (Requirement 7.9), then the cards.
    assert [p.path for p in pictures[2:]] == [f"p/{wt_t1.picture.digest}.png", f"p/{t31.picture.digest}.png"]
    assert page.count("photo-small") == 2
    assert 'href="body-lab.html"' in page and 'href="wind-tunnel.html"' in page
    assert page.count("chosen by a person") >= 2
    # Stopped sessions never reach the cover (14.4).
    assert "wt-002" not in page and "wt-003" not in page
    assert 'href="legend.html"' in page


def test_cover_commentary_is_short_and_passes_the_word_check(built) -> None:
    segments, _ = built
    assert len(cover.visible_words(segments)) <= cover.MAX_VISIBLE_WORDS
    checked = words.load(WORDS)
    for segment in segments:
        if segment.ink is Ink.COMMENTARY:
            checked.check(segment.text, segment.source)
    for name in dir(text):
        if name.startswith("COVER_") or name in ("SITE_TITLE", "TAGLINE", "TRACK_CAPTION_COVER"):
            checked.check(getattr(text, name), text.source(name))


def test_session_margin_pins_the_chosen_trials_as_photos(loaded, table) -> None:
    record = _by_session(loaded, "body-2")
    chosen = choices.load(CHOICES, loaded)[(record.application, record.session)]
    pins = photo.Pins(record, table[record.application])
    page = ink.join(session.table_section(views.full(record), chosen, pins))[0]
    margin = page[page.index('<aside class="margin">') :]
    pinned = re.findall(
        r'<figure class="pinned" data-trial="(T\d+)"><section class="photo-pair">'
        r'<figure class="photo tilt-\d photo-small"',
        margin,
    )
    assert pinned == ["T25", "T30", "T36"]
    # Each pin keeps its recorded sheet, then its magnified picture (Requirement 7.9).
    recorded = [p.path for p in pins.files[::2]]
    assert recorded == [f"p/{_trial(record, tid).picture.digest}.png" for tid in ("T25", "T30", "T36")]
    assert len(pins.files) == 6


def test_cover_reader_line_gives_the_passes_of_the_six_runs(built) -> None:
    page = ink.join(built[0])[0]
    chips = re.findall(r'<span class="reader-chip reader-(\w+)"><span class="ink-p">([^<]+)</span>', page)
    assert chips == [("spec", "spec 2/2"), ("record", "record 1/2"), ("none", "none 0/2")]
    assert page.index("cover-miss") < page.index("cover-reader") < page.index("cover-labs")


def test_cover_tabs_list_the_ended_sessions_of_each_lab(built) -> None:
    page = ink.join(built[0])[0]
    assert page.count('<input type="radio" name="lab-tab"') == 2
    sessions = re.findall(r'<li class="session-line"><span class="session-id"><a href="([^"]+)"', page)
    assert sessions == ["wind-tunnel-wt-004.html", "body-lab-body-1.html", "body-lab-body-2.html"]
