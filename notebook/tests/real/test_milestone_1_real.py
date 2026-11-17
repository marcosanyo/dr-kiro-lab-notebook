"""Milestone 1 on the committed records (task 10.1).

One full build of `sessions/` with the committed choice, cover, layout and word files, through the command
line into `tmp_path`, once for this module. Every assertion reads the written HTML files, parsed with
`html.parser`, so the test checks what a visitor gets. The ids, counts and texts asserted are facts of the
sealed records listed in the requirements' introduction and of the approved choice and cover files
(Decisions 36, 37), not results the notebook claims.
"""

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

import pytest
from bench.specfiles.discovered import STATUSES

from notebook import cli, records, tables, text
from notebook.ink import Ink, ink_for_author

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = ROOT / "sessions"

_VOID = {"meta", "link", "img", "br", "hr", "input", "source", "wbr", "col", "area", "base", "embed"}


@dataclass
class Node:
    tag: str
    attrs: dict[str, str]
    children: list["Node | str"] = field(default_factory=list)

    @property
    def classes(self) -> set[str]:
        return set(self.attrs.get("class", "").split())

    def text(self) -> str:
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)

    def elements(self) -> list["Node"]:
        return [c for c in self.children if isinstance(c, Node)]

    def walk(self):
        yield self
        for child in self.elements():
            yield from child.walk()

    def find_all(self, tag: str | None = None, cls: str | None = None, **attrs: str) -> list["Node"]:
        return [
            n
            for n in self.walk()
            if (tag is None or n.tag == tag)
            and (cls is None or cls in n.classes)
            and all(n.attrs.get(k) == v for k, v in attrs.items())
        ]

    def find(self, tag: str | None = None, cls: str | None = None, **attrs: str) -> "Node":
        found = self.find_all(tag, cls, **attrs)
        assert len(found) == 1, (tag, cls, attrs, len(found))
        return found[0]


class _Tree(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: v or "" for k, v in attrs})
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, {k: v or "" for k, v in attrs}))

    def handle_endtag(self, tag):
        if tag in _VOID:
            return
        assert self.stack[-1].tag == tag, f"</{tag}> closes <{self.stack[-1].tag}>"
        self.stack.pop()

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _parse(path: Path) -> Node:
    tree = _Tree()
    tree.feed(path.read_text(encoding="utf-8"))
    tree.close()
    assert tree.stack == [tree.root], f"{path.name}: unclosed elements"
    return tree.root


def _argv(out: Path) -> list[str]:
    return [
        "--sessions", str(SESSIONS),
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
    out = tmp_path_factory.mktemp("milestone-1") / "site"
    assert cli.main(_argv(out)) == 0
    return out


@pytest.fixture(scope="module")
def loaded() -> dict[str, records.RecordModel]:
    return {r.session: r for r in records.load(SESSIONS)}


def _session_page(site: Path, record: records.RecordModel) -> Node:
    return _parse(site / f"{record.application}-{record.session}.html")


def _rows(page: Node) -> list[Node]:
    return [n for n in page.find_all("tr") if n.attrs.get("id", "").startswith("row-")]


def _cells(row: Node) -> list[Node]:
    return [c for c in row.elements() if c.tag == "td"]


def _ink_class(author: str, where: str) -> str:
    return f"ink-{ink_for_author(author, where).value}"


def _trial(record: records.RecordModel, tid: str) -> records.Trial:
    (trial,) = [t for t in record.trials if t.id == tid]
    return trial


# body-2: the end table (Requirements 8.1-8.4, 8.10, 22.5)

BODY_2_TABS = {
    "R2": "R1",
    "R3": "R11",
    "R4": "R5",
    "R6": "R7",
    "R8": "R9",
    "R10": "R11",
    "R12": "R13",
    "R14": "R13",
}
BODY_2_REVERSE = {
    "R1": ["R2"],
    "R5": ["R4"],
    "R7": ["R6"],
    "R9": ["R8"],
    "R11": ["R3", "R10"],
    "R13": ["R12", "R14"],
}


def test_the_full_build_writes_the_cover_and_the_session_pages(site):
    for name in ("index.html", "body-lab-body-1.html", "body-lab-body-2.html", "wind-tunnel-wt-004.html"):
        assert (site / name).is_file(), name


def test_body_2_has_14_rows_in_order_and_8_struck_through_with_their_tabs(site, loaded):
    page = _session_page(site, loaded["body-2"])
    rows = _rows(page)
    assert [r.attrs["id"] for r in rows] == [f"row-R{n}" for n in range(1, 15)]
    struck = {r.attrs["id"][4:] for r in rows if "row-rejected" in r.classes}
    assert struck == set(BODY_2_TABS)
    for row in rows:
        rid = row.attrs["id"][4:]
        tabs = row.find_all("details", "tab")
        if rid not in BODY_2_TABS:
            assert tabs == []
            continue
        (tab,) = tabs
        target = BODY_2_TABS[rid]
        assert tab.find("summary").text() == text.REPLACED_BY + target
        assert [a.attrs["href"] for a in tab.find_all("a")] == [f"#row-{target}"]
        # The tab shows the replacing row's rule text, as that row's own rule cell shows it.
        (target_row,) = [r for r in rows if r.attrs["id"] == f"row-{target}"]
        assert tab.find("span", "rule-small").text() == _cells(target_row)[1].text()


def test_body_2_replacing_rows_show_their_reverse_links(site, loaded):
    rows = _rows(_session_page(site, loaded["body-2"]))
    for row in rows:
        rid = row.attrs["id"][4:]
        spans = _cells(row)[0].find_all("span", "replaces")
        if rid not in BODY_2_REVERSE:
            assert spans == []
            continue
        (span,) = spans
        ids = BODY_2_REVERSE[rid]
        assert span.text() == text.REPLACES + text.LIST_SEPARATOR.join(ids)
        assert [a.attrs["href"] for a in span.find_all("a")] == [f"#row-{i}" for i in ids]


def test_body_2_r13_carries_the_refused_end_note_with_both_messages_in_their_inks(site, loaded):
    record = loaded["body-2"]
    body = _session_page(site, record).find("tbody")
    trs = [n for n in body.elements() if n.tag == "tr"]
    notes = [i for i, tr in enumerate(trs) if "row-note" in tr.classes]
    assert len(notes) == 1
    (at,) = notes
    assert trs[at - 1].attrs["id"] == "row-R13"
    sticky = trs[at].find("aside", "sticky-stamp")
    assert "sticky" in sticky.classes
    heading = sticky.find("span", "sticky-heading")
    assert heading.text() == text.REFUSED_END_BEFORE_COUNT + "2" + text.REFUSED_END_AFTER_COUNT
    assert [(sorted(s.classes), s.text()) for s in heading.elements()][1] == (["ink-p"], "2")

    ends = [r for r in record.refusals if r.action == "end"]
    assert len(ends) == 2
    paragraphs = [p for p in sticky.elements() if p.tag == "p"]
    shown = [
        [(" ".join(sorted(s.classes)), s.text()) for s in p.elements()]
        for p in paragraphs
        if p.elements() and "sticky-heading" not in p.elements()[0].classes
    ]
    expected = [
        [(_ink_class(part.text.author, part.text.source), part.text.text) for part in refusal.message]
        for refusal in ends
    ]
    messages = [s for s in shown if s and s[0][0] != "ink-c"]
    assert messages == expected
    # Each message holds quotes in Dr. Kiro's ink and bench text in pencil, in the recorded parts.
    for message in messages:
        assert len(message) == 8
        assert ("ink-k", "R13") in message and ("ink-k", "H11.P3: hit/not-comparable") in message
    texts = [p.text() for p in paragraphs]
    assert texts.count(text.REFUSAL_QUOTE_NOTE) == 2
    assert text.REFUSED_END_SEALED in texts and text.REFUSED_END_NO_COPY in texts


# Every row of every table shows its status word (Requirements 8.2, 22.2)


def test_every_row_of_every_table_shows_its_status_word_as_the_record_holds_it(site, loaded):
    seen = 0
    for record in loaded.values():
        page_file = site / f"{record.application}-{record.session}.html"
        assert page_file.is_file(), record.name  # every record has its page (Requirement 2.8)
        if not record.snapshots:
            assert _rows(_parse(page_file)) == []  # wt-003: no snapshot, no table (14.6)
            continue
        view_end = tables.end_snapshot(record)
        snapshot = view_end if view_end is not None else (record.snapshots[-1] if record.snapshots else None)
        shown_rows = _rows(_parse(page_file))
        read = tables.read(record, snapshot) if snapshot is not None else None
        if record.seal.end == "ended" and view_end is None:
            assert shown_rows == []  # body-1: "no table"
            continue
        if isinstance(read, tables.Unreadable):
            assert shown_rows == []  # 10.14: the section as written, no rows guessed
            continue
        label = text.CHECKED if view_end is not None else text.NOT_CHECKED
        assert [r.attrs["id"] for r in shown_rows] == [f"row-{row.id}" for row in read.rows]
        for tr, row in zip(shown_rows, read.rows, strict=True):
            status = _cells(tr)[5]
            stamp = status.find("span", "stamp")
            assert stamp.text() == row.status
            assert row.status in STATUSES and f"stamp-{row.status}" in stamp.classes
            assert stamp.find("span", "ink-s").text() == row.status
            assert status.find("span", "stamp-label").text() == label
            seen += 1
    assert seen == 14 + 6  # body-2 and wt-004 hold the only tables the reader accepts


def test_wt_004_rows_r1_to_r6_are_stamped_checked_by_the_bench(site, loaded):
    rows = _rows(_session_page(site, loaded["wt-004"]))
    assert [r.attrs["id"] for r in rows] == [f"row-R{n}" for n in range(1, 7)]
    for row in rows:
        assert _cells(row)[5].find("span", "stamp-label").text() == text.CHECKED
        assert "row-rejected" not in row.classes


# body-1, wt-002, wt-003 (Requirements 10.9, 10.14, 14.6)


def test_body_1_shows_no_table_and_no_rows(site, loaded):
    page = _session_page(site, loaded["body-1"])
    assert page.find("p", "no-table").text() == text.NO_TABLE
    assert page.find_all("table") == []
    misses = [o for o in loaded["body-1"].outcomes if o.outcome == "miss"]
    assert len(page.find("ul", "missed").find_all("li")) == len(misses) == 8


def test_wt_002_shows_its_last_snapshot_section_with_the_readers_message(site, loaded):
    record = loaded["wt-002"]
    read = tables.read(record, record.snapshots[-1])
    assert isinstance(read, tables.Unreadable) and read.section is not None
    page = _session_page(site, record)
    section = page.find(cls="table-page")
    (block,) = section.find_all("p", "block-k")
    assert "ink-k" in block.classes and block.text() == read.section
    message = [p for p in section.find_all("p") if p.text().startswith(text.UNREADABLE_MESSAGE)]
    assert len(message) == 1
    spans = message[0].elements()[1:]
    where = "wt-002 reader message"
    assert [(" ".join(sorted(s.classes)), s.text()) for s in spans] == [
        (_ink_class(span.author, where), span.text) for span in read.message.spans
    ]
    texts = [p.text() for p in section.find_all("p")]
    assert text.UNREADABLE in texts and text.NOT_CHECKED in texts
    assert text.NO_TABLE not in texts and section.find_all("table") == []


def test_wt_003_has_a_page_with_only_what_the_record_holds_and_no_replay(site, loaded):
    """wt-003 (stopped, no snapshot) has a page with only the content of Requirement 14.2 (14.6); no replay
    section (Decision 48). The page in detail: `test_stopped_real.py`."""
    record = loaded["wt-003"]
    assert not record.snapshots
    page = _session_page(site, record)
    assert page.find_all("section", "replay") == [] and page.find_all("p", "no-replay") == []
    assert page.find_all("table") == [] and page.find_all("details", "entry") == []


# The cover (Requirements 13.1, 13.2, 13.7)


def test_cover_shows_h4_p1_with_t12_picture_track_and_miss(site, loaded):
    cover = _parse(site / "index.html")
    t12 = _trial(loaded["body-2"], "T12")
    miss = cover.find(cls="cover-miss")
    large = miss.find("figure", "photo-large")
    assert large.find("img").attrs["src"] == f"p/{t12.picture.digest}.png"
    assert (site / f"p/{t12.picture.digest}.png").read_bytes() == t12.picture.data
    assert "T12" in large.find("figcaption").text()

    measured = dict(t12.measurements)
    xs = measured["track_x"]
    assert isinstance(xs, tuple)
    (polyline,) = miss.find("figure", "track").find_all("polyline")
    assert len(polyline.attrs["points"].split()) == len(xs)

    claim = miss.find(cls="cover-claim")
    assert "H4.P1" in [s.text() for s in claim.find_all("span", "ink-p")]
    assert claim.find("span", "miss").text() == "miss"
    assert claim.find("span", "miss-value").text() == "-0.2047"


def test_cover_shows_rows_r4_and_its_replacement_r5(site):
    claim = _parse(site / "index.html").find(cls="cover-rows")
    links = [a.attrs["href"] for a in claim.find_all("a")]
    assert links == ["body-lab-body-2.html#row-R4", "body-lab-body-2.html#row-R5"]
    (item,) = claim.find_all("li")
    assert "row-rejected" in item.classes
    stamps = [s.text() for s in claim.find_all("span", "stamp")]
    assert stamps == ["rejected", "observed"]
    # Each row's stamp keeps its label, as in the table (Requirement 8.2; user, checkpoint 11).
    labels = [s.text() for s in claim.find_all("span", "stamp-label")]
    assert labels == [text.CHECKED, text.CHECKED]
    for status in claim.find_all("span", "cover-status"):
        assert [(c.tag, sorted(c.classes)[0]) for c in status.elements()] == [
            ("span", "stamp"),
            ("span", "stamp-label"),
        ]


def test_ink_of_status_words_is_the_stamp(site, loaded):
    page = _session_page(site, loaded["body-2"])
    for stamp in page.find_all("span", "stamp"):
        assert [c.tag for c in stamp.elements()] == ["span"]
        assert f"ink-{Ink.STAMP.value}" in stamp.elements()[0].classes


# The four fixes of checkpoint 11 (user, 2026-11-17; visual steering)

CSS = ROOT / "notebook" / "src" / "notebook" / "assets" / "notebook.css"


def _paths(node: Node, ancestors: tuple[Node, ...] = ()):
    """Every element with the elements above it, outermost first."""
    yield ancestors, node
    for child in node.elements():
        yield from _paths(child, (*ancestors, node))


def _struck_selectors() -> set[str]:
    """The selectors of every stylesheet rule that draws a strike-through."""
    found: set[str] = set()
    for rule in CSS.read_text(encoding="utf-8").split("}"):
        if "{" not in rule:
            continue
        selectors, declarations = rule.split("{", 1)
        if "line-through" in declarations:
            lines = [ln for ln in selectors.splitlines() if not ln.strip().startswith("/*")]
            selectors = "\n".join(lines).rsplit("*/", 1)[-1]
            found |= {s.strip() for s in selectors.split(",") if s.strip()}
    return found


def test_the_strike_through_rules_leave_the_status_cell_and_the_cover_status_out():
    assert _struck_selectors() == {
        ".row-rejected td:not(.status)",
        ".cover-rows .row-rejected > a",
        ".cover-rows .row-rejected > .cover-rule",
    }


def test_no_stamp_label_sits_inside_a_struck_element(site, loaded):
    pages = [_session_page(site, loaded["body-2"]), _parse(site / "index.html")]
    labels = 0
    for page in pages:
        for ancestors, node in _paths(page):
            if "stamp-label" not in node.classes:
                continue
            labels += 1
            for i, above in enumerate(ancestors):
                parent = ancestors[i - 1] if i else None
                in_rejected_row = parent is not None and "row-rejected" in parent.classes
                # `.row-rejected td:not(.status)`
                assert not (above.tag == "td" and in_rejected_row and "status" not in above.classes)
                # `.row-rejected > a`, `.row-rejected > .cover-rule`
                assert not (in_rejected_row and (above.tag == "a" or "cover-rule" in above.classes))
    # Every label of body-2's table (14 rows) and of the cover's two cited rows was looked at.
    assert labels >= 14 + 2
    rejected = [r for r in _rows(pages[0]) if "row-rejected" in r.classes]
    assert len(rejected) == len(BODY_2_TABS)
    for row in rejected:
        status = _cells(row)[5]
        assert "status" in status.classes and status.find_all("span", "stamp-label")
        assert [c for c in _cells(row) if "status" in c.classes] == [status]


def test_cover_photo_and_track_are_siblings_in_one_row(site):
    evidence = _parse(site / "index.html").find(cls="cover-evidence")
    children = evidence.elements()
    # The photo pair (the moving picture and its magnified picture, Requirement 7.9) and the track.
    assert [(c.tag, "photo-pair" in c.classes or "track" in c.classes) for c in children] == [
        ("section", True),
        ("figure", True),
    ]
    assert "photo-pair" in children[0].classes and "track" in children[1].classes
    assert children[0].find("figure", "photo-large") is not None
    css = CSS.read_text(encoding="utf-8")
    rule = css[css.index(".cover-evidence {") :]
    rule = rule[: rule.index("}")]
    assert "display: flex;" in rule and "flex-wrap: wrap;" in rule


def test_cover_cards_label_sits_directly_above_the_cards(site):
    cards = _parse(site / "index.html").find("section", "cover-cards")
    label, row = cards.elements()
    assert "block-label" in label.classes and label.text() == text.CHOSEN_BY_A_PERSON
    assert "card-row" in row.classes
    assert [len(c.find_all("figure", "photo-small")) for c in row.elements()] == [1, 1]


def test_sticky_note_sets_the_measurement_name_apart(site, loaded):
    record = loaded["body-2"]
    sticky = _session_page(site, record).find("aside", "margin").find_all("aside", "sticky")[0]
    (name,) = sticky.find_all("span", "measure-name")
    predictions = {p.id: p for h in record.hypotheses for p in h.predictions}
    (outcome,) = [o for o in record.outcomes if o.prediction == "H8.P6" and o.outcome == "miss"]
    assert "ink-p" in name.classes and name.text() == predictions["H8.P6"].measurement
    paragraph = sticky.find_all("p")[0].text()
    assert text.MEASURED + name.text() + text.MEASURED_NAME_END in paragraph
    assert paragraph.startswith(text.MISS_POINTER + "H8.P6" + text.REGISTERED_RANGE)
    assert outcome.value is not None
