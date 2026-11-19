"""The two scan passes of `scan.py` (design 11, N7; Requirements 12.8, 20.1, 20.2, 20.5).

The planted term is taken at test time from the scanner's own derived terms, so no term is written here.
"""

import dataclasses
import json
from pathlib import Path

import pytest
from bench.scan.levels import SIDECAR_SUFFIX, sidecar_pieces

from fixtures.session import DESIGN_START, Lab, exp_file, hyp_block, ok
from notebook import records, scan, text
from notebook.choices import Choices
from notebook.errors import NotebookError
from notebook.ink import Ink, Segment, commentary, join, markup, pencil
from notebook.pages import parts

ROOT = Path(__file__).resolve().parents[3]
CONFIGS = [
    ROOT / "body-lab" / "adapter" / "scan_sources.toml",
    ROOT / "wind-tunnel" / "adapter" / "scan_sources.toml",
]
STOP_LIST = ROOT / ".kiro" / "blind-scan" / "stop-list.txt"


@pytest.fixture(scope="module")
def scanner():
    return scan.load(CONFIGS, STOP_LIST)


@pytest.fixture(scope="module")
def term(scanner) -> str:
    """One single-word term the scan derives from the scan sources."""
    return sorted(t[0] for t in scanner.terms if len(t) == 1 and t[0].isalpha())[0]


@pytest.fixture(scope="module")
def planted_record(tmp_path_factory, term) -> records.RecordModel:
    """A fake session whose verdict words, written by Dr. Kiro, hold the planted term."""
    lab = Lab(tmp_path_factory.mktemp("scan-session"))
    session = lab.start()
    lab.add(
        hyp_block(
            "H1",
            "WHEN amp rises at gain 1, THE distance SHALL rise.",
            {"id": "P1", "range": [0.25, 0.35], "label": "inside", "when": {"amp": 0.3, "gain": 1.0}},
        )
    )
    ok(session.register("H1"))
    sweep = [[a, 1.0] for a in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6)]
    ok(session.run(lab.experiment("e1_sweep_amp.py", exp_file("H1", sweep, mode="sweep", sweep=["amp"]))))
    ok(session.verdict("E1", "supported", f"it moved like a {term}"))
    lab.write(
        "design.md",
        DESIGN_START + "\n| id | rule | scope | experiments | predictions | status | replaced by |\n"
        "|---|---|---|---|---|---|---|\n"
        "| R1 | distance grows with amp | gain 1 | E1 | H1.P1 | observed | |\n",
    )
    ok(session.end())
    assert session.sealed_path is not None
    return records.load_record(session.sealed_path, "sessions/fake/s1", allow_fake=True)


def test_a_term_planted_in_a_text_py_string_fails_naming_the_source(scanner, term, monkeypatch) -> None:
    monkeypatch.setattr(text, "LEGEND_LINK", f"ink legend of the {term}")
    with pytest.raises(scan.ScanFailed) as caught:
        scan.check(scanner, {"legend.html": parts.footer()})
    found = caught.value.findings
    # Pass 1 names the text.py string; pass 2 names the finished file.
    assert any(f.file == text.source("LEGEND_LINK") and f.kind == "term" and f.match == term for f in found)
    assert any(f.file == "legend.html" and f.kind == "term" for f in found)
    assert caught.value.where == scan.WHERE
    assert f"{text.SOURCE_FILE}: LEGEND_LINK:1: term: {term}" in caught.value.problem


def test_the_same_term_in_dr_kiros_text_of_a_fixture_record_passes(scanner, term, planted_record) -> None:
    (verdict,) = planted_record.verdicts
    assert term in verdict.words.text and verdict.words.author == "dr-kiro"
    segment = verdict.words.segment()
    joined = scan.check(scanner, {"page.html": [markup("<p>"), segment, markup("</p>")]})
    assert term in joined["page.html"][0]
    # The same words as builder text fail.
    with pytest.raises(scan.ScanFailed):
        scan.check(scanner, {"page.html": [commentary(segment.text, "probe")]})


def test_a_term_planted_in_a_choice_text_fails_naming_the_file_and_key(scanner, term) -> None:
    chosen = Choices(
        record="sessions/fake/s1",
        file="choices/fake/s1.toml",
        title="A title",
        subtitle=f"the {term} did not move",
        summary="A summary.",
        line="A line.",
        model="a model",
        date="2026-01-01",
        color="violet",
        progress=None,
        polaroids=(),
    )
    assert [s.text for s in scan.choice_segments([chosen])][:3] == [
        "A title",
        f"the {term} did not move",
        "A summary.",
    ]
    with pytest.raises(scan.ScanFailed) as caught:
        scan.check(scanner, {}, scan.choice_segments([chosen]))
    assert [(f.file, f.kind, f.match) for f in caught.value.findings] == [
        ("choices/fake/s1.toml key subtitle", "term", term)
    ]


def test_dr_kiros_fixed_words_are_builder_level_segments(planted_record) -> None:
    (hypothesis,) = planted_record.hypotheses
    (verdict,) = planted_record.verdicts
    log = "sessions/fake/s1/log.jsonl"
    assert scan.drkiro_word_segments([planted_record]) == [
        pencil("inside", f"{log} line {hypothesis.seq}"),
        pencil("supported", f"{log} line {verdict.seq}"),
    ]
    assert {scan.level(s) for s in scan.drkiro_word_segments([planted_record])} == {"builder"}


def test_a_term_planted_in_a_verdict_word_fails_at_the_builder_level(scanner, term, planted_record) -> None:
    # The bench accepts only its fixed verdict words, so the term is planted in the loaded fixture record.
    (verdict,) = planted_record.verdicts
    planted = dataclasses.replace(planted_record, verdicts=(dataclasses.replace(verdict, verdict=term),))
    # Shown in Dr. Kiro's ink, the word passes at Dr. Kiro's level ...
    shown = Segment(term, Ink.DRKIRO, f"sessions/fake/s1/log.jsonl line {verdict.seq}")
    scan.check(scanner, {"page.html": [markup("<p>"), shown, markup("</p>")]})
    # ... and the builder-level segments of the record fail, naming the record's log line.
    with pytest.raises(scan.ScanFailed) as caught:
        scan.check(
            scanner,
            {"page.html": [markup("<p>"), shown, markup("</p>")]},
            scan.drkiro_word_segments([planted]),
        )
    assert [(f.file, f.kind, f.match) for f in caught.value.findings] == [
        (f"sessions/fake/s1/log.jsonl line {verdict.seq}", "term", term)
    ]


def test_the_home_folder_in_a_builder_string_fails(scanner) -> None:
    home = str(Path.home().resolve())
    with pytest.raises(scan.ScanFailed) as caught:
        scan.check(scanner, {"index.html": [commentary(f"built in {home}/site", "probe")]})
    assert {f.kind for f in caught.value.findings} == {"path"}
    assert {f.file for f in caught.value.findings} == {"probe", "index.html"}


def test_every_finding_is_collected_not_only_the_first(scanner, term) -> None:
    home = str(Path.home().resolve())
    files = {
        "a.html": [commentary(f"one {term}", "first")],
        "b.html": [pencil(f"{home}/x", "second")],
    }
    with pytest.raises(scan.ScanFailed) as caught:
        scan.check(scanner, files)
    assert {f.file for f in caught.value.findings} == {"first", "a.html", "second", "b.html"}
    for finding in caught.value.findings:
        assert str(finding) in caught.value.problem


def test_file_pieces_equal_the_pieces_the_bench_reads_from_the_sidecar(planted_record, tmp_path) -> None:
    segments = [
        markup("<p>\n"),
        planted_record.verdicts[0].words.segment(),
        markup("\n</p>"),
        commentary("a <b> & 'c'\nd", "probe"),
    ]
    written, ranges = join(segments)
    path = tmp_path / "page.html"
    path.write_text(written, encoding="utf-8")
    path.with_name(path.name + SIDECAR_SUFFIX).write_text(json.dumps({"ranges": ranges}), encoding="utf-8")
    assert scan.file_pieces(str(path), written, ranges) == sidecar_pieces(path, written)


def test_ranges_that_do_not_cover_the_file_fail(scanner) -> None:
    with pytest.raises(NotebookError, match="cover 2 of 3"):
        scan.file_pieces("x.html", "abc", [{"start": 0, "end": 2, "author": "bench"}])
    with pytest.raises(NotebookError, match="unknown author"):
        scan.file_pieces("x.html", "abc", [{"start": 0, "end": 3, "author": "someone"}])


def test_a_clean_page_passes_and_returns_its_joined_text(scanner) -> None:
    joined = scan.check(
        scanner, {"index.html": [markup("<p>"), commentary("a quiet page", "probe"), markup("</p>")]}
    )
    assert joined == {"index.html": ("<p>a quiet page</p>", [{"start": 0, "end": 19, "author": "bench"}])}
