"""dr-kiro Requirement 8 (design 7.3) and lab-bench Requirement 15.10: the final spec of a sealed record, its
copy in `discovered/`, the check of every copy against its record, and the blind scan of a copy.

The records are the sealed sessions in `sessions/`, copied into a temporary folder: wt-004 ended with an end
snapshot, body-1 ended before the bench recorded one, wt-002 was stopped."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from bench.record.spec_copy import (
    COPY_FILES,
    SOURCE_NAME,
    SpecCopyError,
    check_copies,
    check_main,
    export_main,
    final_spec,
    write_copy,
)
from bench.scan import scan as scan_module
from bench.scan.scan import Scanner
from bench.scan.terms import AppSources, LabLayout, ScanError, load_app, load_stop_list

REPO = Path(__file__).resolve().parents[3]
SESSIONS = REPO / "sessions"
FAKE_CONFIG = REPO / "bench" / "src" / "bench" / "fake" / "scan_sources.toml"
STOP_LIST = REPO / ".kiro" / "blind-scan" / "stop-list.txt"
RECORDS = ("wind-tunnel/wt-004", "body-lab/body-1", "wind-tunnel/wt-002")


def sessions(tmp_path: Path) -> Path:
    root = tmp_path / "sessions"
    for name in RECORDS:
        shutil.copytree(SESSIONS / name, root / name)
    return root


def discovered(tmp_path: Path) -> Path:
    root = tmp_path / "discovered"
    root.mkdir()
    (root / "README.md").write_text("Copies.\n")
    return root


def end_snapshot(record: Path) -> dict:
    entries = [json.loads(line) for line in (record / "log.jsonl").read_text().splitlines()]
    (snapshot,) = [e for e in entries if e["kind"] == "snapshot" and e["body"]["for"] == "end"]
    return snapshot


def test_final_spec_is_the_end_snapshot() -> None:
    record = SESSIONS / "wind-tunnel" / "wt-004"
    final = final_spec(record)
    snapshot = end_snapshot(record)
    assert (final.application, final.session, final.snapshot_seq) == (
        "wind-tunnel",
        "wt-004",
        snapshot["seq"],
    )
    for key in ("requirements", "design", "tasks"):
        data = final.files[f"{key}.md"]
        assert hashlib.sha256(data).hexdigest() == snapshot["body"]["files"][key]["blob"]
    assert b"## Discovered spec" in final.files["design.md"]
    source = json.loads(final.source())
    assert source["snapshot"] == {"seq": snapshot["seq"], "hash": snapshot["hash"]}
    assert final.source() == final_spec(record).source()  # same input, same bytes


def test_records_without_a_final_spec_are_refused() -> None:
    with pytest.raises(SpecCopyError, match="body-1 has no end snapshot"):
        final_spec(SESSIONS / "body-lab" / "body-1")
    with pytest.raises(SpecCopyError, match="wt-002 was stopped, not ended"):
        final_spec(SESSIONS / "wind-tunnel" / "wt-002")


def test_a_record_that_does_not_verify_is_refused(tmp_path: Path) -> None:
    root = sessions(tmp_path)
    record = root / "wind-tunnel" / "wt-004"
    blob = end_snapshot(record)["body"]["files"]["design"]["blob"]
    (record / "blobs" / blob).write_text("edited\n")
    with pytest.raises(SpecCopyError, match="does not verify"):
        final_spec(record)


def test_write_check_and_every_kind_of_mismatch(tmp_path: Path) -> None:
    root, out = sessions(tmp_path), discovered(tmp_path)
    # No copy yet: the ended session with an end snapshot is missing; the other two need none.
    report, problems = check_copies(root, out)
    assert report == [
        "body-lab/body-1: ended without an end snapshot, no copy",
        "wind-tunnel/wt-002: stopped, no copy",
    ]
    assert len(problems) == 1 and "wt-004: missing" in problems[0]
    folder = write_copy(root / "wind-tunnel" / "wt-004", out)
    assert folder == out / "wind-tunnel" / "wt-004"
    assert sorted(p.name for p in folder.iterdir()) == sorted((*COPY_FILES, SOURCE_NAME))
    report, problems = check_copies(root, out)
    assert problems == [] and "wind-tunnel/wt-004: copy matches the record" in report
    with pytest.raises(SpecCopyError, match="already exists"):
        write_copy(root / "wind-tunnel" / "wt-004", out)

    design = folder / "design.md"
    original = design.read_bytes()
    design.write_bytes(original + b"edited by a person\n")
    assert check_copies(root, out)[1] == [f"{design}: differs from the record"]
    design.write_bytes(original)
    (folder / "notes.md").write_text("x\n")
    assert check_copies(root, out)[1] == [f"{folder / 'notes.md'}: not part of the copy"]
    (folder / "notes.md").unlink()
    (folder / SOURCE_NAME).unlink()
    assert check_copies(root, out)[1] == [f"{folder / SOURCE_NAME}: missing"]
    write_copy_again(root, out)
    planted = out / "body-lab" / "body-1"
    planted.mkdir(parents=True)
    assert "has no final spec to copy" in check_copies(root, out)[1][0]
    planted.rmdir()
    (out / "body-lab" / "body-9").mkdir()
    assert check_copies(root, out)[1] == [
        f"{out / 'body-lab' / 'body-9'}: no sealed session record has this name"
    ]
    (out / "body-lab" / "body-9").rmdir()
    (out / "stray.txt").write_text("x\n")
    assert check_copies(root, out)[1] == [f"{out / 'stray.txt'}: not part of the discovered folder"]


def write_copy_again(root: Path, out: Path) -> None:
    shutil.rmtree(out / "wind-tunnel" / "wt-004")
    write_copy(root / "wind-tunnel" / "wt-004", out)


def test_commands(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root, out = sessions(tmp_path), discovered(tmp_path)
    assert check_main([str(root), str(out)]) == 1
    assert export_main([str(root / "body-lab" / "body-1"), str(out)]) == 1
    assert "no end snapshot" in capsys.readouterr().err
    assert export_main([str(root / "wind-tunnel" / "wt-004"), str(out)]) == 0
    assert check_main([str(root), str(out)]) == 0
    assert "every copy matches its record" in capsys.readouterr().out
    assert check_main([str(root)]) == 2


def test_repository_copies_match_their_records() -> None:
    """The check run before publishing, on the repository itself."""
    report, problems = check_copies(SESSIONS, REPO / "discovered")
    assert problems == []
    assert "wind-tunnel/wt-004: copy matches the record" in report


def fake_scanner() -> Scanner:
    return Scanner([load_app(FAKE_CONFIG)], load_stop_list(STOP_LIST), local_paths=())


def test_blind_scan_of_a_copy(tmp_path: Path) -> None:
    root, out = sessions(tmp_path), discovered(tmp_path)
    folder = write_copy(root / "wind-tunnel" / "wt-004", out)
    scanner = fake_scanner()
    assert scanner.scan_paths([folder]) == []
    # Dr. Kiro's text is scanned for paths, as everywhere.
    tasks = folder / "tasks.md"
    tasks.write_text(tasks.read_text() + "see /Users/someone/notes\n")
    source = json.loads((folder / SOURCE_NAME).read_text())
    with pytest.raises(ScanError, match="does not match its SHA-256"):
        scanner.scan_paths([folder])
    source["files"]["tasks.md"] = hashlib.sha256(tasks.read_bytes()).hexdigest()
    (folder / SOURCE_NAME).write_text(json.dumps(source))
    (finding,) = scanner.scan_paths([folder])
    assert finding.kind == "path" and finding.file == str(tasks)
    (folder / "extra.md").write_text("x\n")
    with pytest.raises(ScanError, match="not part of a spec copy"):
        scanner.scan_paths([folder])


def test_template_in_a_lab_is_scanned_at_builder_level(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A lab spec file that still holds a template is the builder's text, not Dr. Kiro's (design 6)."""
    fake = load_app(FAKE_CONFIG)
    term = "zorblat"  # a part name of the fake model
    assert term in fake_scanner().terms.values()
    lab = tmp_path / "lab"
    (lab / ".kiro" / "specs" / "lab").mkdir(parents=True)
    path = lab / ".kiro" / "specs" / "lab" / "tasks.md"
    path.write_text(f"# Tasks\n\n- [ ] {term}\n")
    layout = LabLayout(lab, ("experiments/**", ".kiro/specs/**"))
    scanner = Scanner(
        [AppSources(fake.names, fake.file_names, fake.solver_dirs, fake.allow, layout)],
        load_stop_list(STOP_LIST),
        local_paths=(),
    )
    assert scanner.scan_paths([lab]) == []  # Dr. Kiro's own text: terms are not findings
    monkeypatch.setattr(scan_module, "TEMPLATE_BYTES", frozenset({path.read_bytes()}))
    (finding,) = scanner.scan_paths([lab])
    assert finding.kind == "term"


def test_templates_pass_the_builder_level_scan() -> None:
    """The fake application here; body-lab and wind-tunnel scan the templates with their own terms in their
    adapter tests."""
    for data in scan_module.TEMPLATE_BYTES:
        assert fake_scanner().scan_text(data.decode("utf-8"), "builder", "template") == []
