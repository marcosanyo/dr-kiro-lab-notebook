"""The reader's working folder (Requirements 4.1, 4.2, 4.5, 7.2, 7.3, 7.5, 7.6, 7.7, 8.4, 9.3, 19.4).

Design 3.5.
"""

import hashlib
import importlib
import json
from importlib import resources
from pathlib import Path

import pytest
from bench.frontend import labhooks
from bench.frontend.describe import descriptions
from bench.record.spec_copy import final_spec
from bench.scan.scan import Finding, Scanner

from build_from_spec import folder, wrap
from build_from_spec.apps import APPS, REQUESTS, App
from build_from_spec.folder import FolderError, GivenFiles, given_files, write_folder
from build_from_spec.reduced import check_reduced
from build_from_spec.request import parse_request
from support import seal_record

REPO_ROOT = Path(__file__).resolve().parents[2]
STOP_LIST = REPO_ROOT / ".kiro" / "blind-scan" / "stop-list.txt"
BODY_2 = REPO_ROOT / "sessions" / "body-lab" / "body-2"
REPO_REQUESTS = REPO_ROOT / REQUESTS
BENCH_METHOD = resources.files("bench.drkiro") / "files" / "method.md"
WORDS = 'Go "straight" on: \\ 前へ, then stop.'
RUN_ID = "run-7f3a"
FAKE_APP = App("fake", "bench.fake.adapter:FakeAdapter", "bench/src/bench/fake/scan_sources.toml", 12, False)
FAKE_TABLE = {"body-lab": APPS["body-lab"], "fake": FAKE_APP}
SPEC_NAMES = ("requirements.md", "design.md", "tasks.md")
SETUP_TREE = {
    ".kiro/agents/reader.json",
    ".kiro/agents/reader-prompt.md",
    ".kiro/steering/method.md",
    ".kiro/steering/reader.md",
    ".kiro/specs/lab/requirements.md",
    ".kiro/specs/lab/design.md",
    ".kiro/specs/lab/tasks.md",
    ".kiro/hooks/confine.py",
    ".kiro/hooks/calllog.py",
    ".kiro/hooks/confine-pre-tool.json",
    ".kiro/hooks/calllog-pre-tool.json",
    ".kiro/hooks/calllog-post-tool.json",
    "request.md",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def files_of(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


def fake_requests(root: Path) -> Path:
    """A repository root whose request folder holds one request for the fake application (words: WORDS)."""
    folder_path = root / REQUESTS
    folder_path.mkdir(parents=True)
    (folder_path / "fake-go.toml").write_text(
        f'id = "fake-go"\napplication = "fake"\nwords = {json.dumps(WORDS, ensure_ascii=False)}\n\n'
        '[[pass]]\nmeasurement = "distance"\nrange = [0.0, 1.0]\n',
        encoding="utf-8",
    )
    return root


@pytest.fixture(scope="module")
def scanner() -> Scanner:
    return Scanner.from_config([REPO_ROOT / APPS["body-lab"].scan_sources], STOP_LIST)


@pytest.fixture
def body_request():
    return parse_request(REPO_REQUESTS / "stop-ahead.toml", APPS)


@pytest.fixture
def fresh(tmp_path: Path) -> Path:
    """A working folder inside a temporary repository; the real bench-run folder is never used."""
    return tmp_path / "repo" / "bench-run" / "build-from-spec" / RUN_ID


def test_spec_setup_writes_the_design_tree(fresh, body_request):
    write_folder(fresh, body_request, given_files("spec", BODY_2))
    assert files_of(fresh) == SETUP_TREE | {f"given/{name}" for name in SPEC_NAMES}
    assert (fresh / "experiments").is_dir()
    assert not any((fresh / "experiments").iterdir())


def test_none_setup_writes_an_empty_given_folder(fresh, body_request):
    write_folder(fresh, body_request, given_files("none", BODY_2))
    assert files_of(fresh) == SETUP_TREE
    assert (fresh / "given").is_dir()
    assert not any((fresh / "given").iterdir())


def test_spec_given_files_are_the_final_spec_byte_for_byte(fresh, body_request):
    write_folder(fresh, body_request, given_files("spec", BODY_2))
    expected = final_spec(BODY_2).files
    for name in SPEC_NAMES:
        assert (fresh / "given" / name).read_bytes() == expected[name]


def test_setups_differ_only_in_given(tmp_path, body_request):
    spec, none = tmp_path / "spec", tmp_path / "none"
    write_folder(spec, body_request, given_files("spec", BODY_2))
    write_folder(none, body_request, given_files("none", BODY_2))
    outside = {k: v for k, v in folder.file_hashes(spec).items() if not k.startswith("given/")}
    assert outside == folder.file_hashes(none)
    assert files_of(spec) - files_of(none) == {f"given/{name}" for name in SPEC_NAMES}
    assert files_of(none) - files_of(spec) == set()


def test_method_is_the_bench_file_byte_for_byte_and_there_is_no_workflow(fresh, body_request):
    write_folder(fresh, body_request, given_files("none", BODY_2))
    assert (fresh / ".kiro" / "steering" / "method.md").read_bytes() == BENCH_METHOD.read_bytes()
    assert not list(fresh.rglob("workflow.md"))


def test_request_file_and_declared_goal_are_the_words(tmp_path, fresh):
    root = fake_requests(tmp_path / "repo")
    request = parse_request(root / REQUESTS / "fake-go.toml", FAKE_TABLE)
    write_folder(fresh, request, GivenFiles({}))
    assert (fresh / "request.md").read_bytes() == WORDS.encode("utf-8")
    adapter = wrap.build("reader/fake/fake-go/12", FAKE_TABLE, root)
    assert adapter.declaration().goal.encode("utf-8") == WORDS.encode("utf-8")


def test_no_file_outside_given_holds_the_run_id_source_or_a_path(fresh, body_request):
    write_folder(fresh, body_request, given_files("spec", BODY_2))
    forbidden = (RUN_ID, "body-2", str(fresh.parents[2]), str(REPO_ROOT), str(Path.home()))
    for where in files_of(fresh):
        if where.startswith("given/"):
            continue
        text = (fresh / where).read_text(encoding="utf-8")
        for word in forbidden:
            assert word not in text, f"{where} holds {word!r}"


def test_tool_hashes_are_the_texts_for_not_required(tmp_path):
    adapter = wrap.build("reader/fake/fake-go/12", FAKE_TABLE, fake_requests(tmp_path / "repo"))
    hashes = folder.tool_hashes(adapter)
    texts = descriptions(adapter.declaration(), "not-required")
    assert hashes == {name: sha(text.encode("utf-8")) for name, text in texts.items()}
    required = descriptions(adapter.declaration(), "required")["end_session"]
    assert hashes["end_session"] != sha(required.encode("utf-8"))


def test_file_hashes_cover_every_file_outside_given(fresh, body_request):
    write_folder(fresh, body_request, given_files("spec", BODY_2))
    hashes = folder.file_hashes(fresh)
    assert set(hashes) == SETUP_TREE
    assert hashes[".kiro/steering/method.md"] == sha(BENCH_METHOD.read_bytes())


def test_clean_folders_pass_the_blind_scan(tmp_path, body_request, scanner):
    for setup in ("spec", "none"):
        target = tmp_path / setup
        write_folder(target, body_request, given_files(setup, BODY_2))
        assert folder.scan_folder(scanner, target) == []


def test_planted_term_in_a_builder_file_is_found_with_its_file_and_line(tmp_path, body_request, scanner):
    term = next(name for name in scanner.terms.values() if name.isalpha())
    target = tmp_path / "builder"
    write_folder(target, body_request, given_files("none", BODY_2))
    reader = target / ".kiro" / "steering" / "reader.md"
    text = reader.read_text(encoding="utf-8")
    assert text.endswith("\n")
    reader.write_text(text + f"{term}\n", encoding="utf-8")
    line = text.count("\n") + 1
    assert Finding(".kiro/steering/reader.md", line, "term", term) in folder.scan_folder(scanner, target)


def test_same_term_in_a_given_spec_file_passes_at_the_dr_kiro_level(tmp_path, body_request, scanner):
    term = next(name for name in scanner.terms.values() if name.isalpha())
    target = tmp_path / "given"
    write_folder(target, body_request, given_files("spec", BODY_2))
    design = target / "given" / "design.md"
    design.write_text(design.read_text(encoding="utf-8") + f"{term}\n", encoding="utf-8")
    assert folder.scan_folder(scanner, target) == []


def test_a_path_in_a_given_spec_file_is_found(tmp_path, body_request, scanner):
    target = tmp_path / "given-path"
    write_folder(target, body_request, given_files("spec", BODY_2))
    design = target / "given" / "design.md"
    design.write_text(design.read_text(encoding="utf-8") + f"see {REPO_ROOT}/sessions\n", encoding="utf-8")
    kinds = {f.kind for f in folder.scan_folder(scanner, target) if f.file == "given/design.md"}
    assert "path" in kinds


def test_an_existing_folder_is_refused_by_name(fresh, body_request):
    write_folder(fresh, body_request, given_files("none", BODY_2))
    with pytest.raises(FolderError, match="already exists") as error:
        write_folder(fresh, body_request, given_files("none", BODY_2))
    assert str(fresh) in str(error.value)


def snapshot_entries(record: Path) -> list[dict]:
    lines = (record / "log.jsonl").read_bytes().split(b"\n")[:-1]
    return [json.loads(line) for line in lines if json.loads(line)["kind"] == "snapshot"]


def test_record_setup_writes_the_reduced_copy_in_given_record(fresh, body_request):
    given = given_files("record", BODY_2)
    write_folder(fresh, body_request, given)
    assert files_of(fresh) == SETUP_TREE | {f"given/{name}" for name in given.files}
    assert (fresh / "given" / "record" / "blobs").is_dir()
    assert check_reduced(fresh / "given" / "record", BODY_2) == []


def test_record_setup_drops_the_snapshots_and_its_copy_is_the_source_minus_them(fresh, body_request):
    write_folder(fresh, body_request, given_files("record", BODY_2))
    source_lines = (BODY_2 / "log.jsonl").read_bytes().split(b"\n")[:-1]
    kept = [line for line in source_lines if json.loads(line)["kind"] != "snapshot"]
    copy = (fresh / "given" / "record" / "log.jsonl").read_bytes()
    assert copy == b"".join(line + b"\n" for line in kept)


def test_record_setup_returns_the_removed_snapshots_in_log_order():
    given = given_files("record", BODY_2)
    expected = [(e["seq"], e["hash"]) for e in snapshot_entries(BODY_2)]
    assert [(r.seq, r.hash) for r in given.removed] == expected
    assert given.removed, "body-2 holds snapshot entries"


def test_three_setups_differ_only_in_given(tmp_path, body_request):
    folders = {}
    for setup in ("spec", "none", "record"):
        folders[setup] = tmp_path / setup
        write_folder(folders[setup], body_request, given_files(setup, BODY_2))
    outside = {
        setup: {w: d for w, d in folder.file_hashes(path).items() if not w.startswith("given/")}
        for setup, path in folders.items()
    }
    assert outside["spec"] == outside["none"] == outside["record"]
    for path in folders.values():
        assert {p for p in files_of(path) if not p.startswith("given/")} == SETUP_TREE
    assert all(name.startswith("given/record/") for name in files_of(folders["record"]) - SETUP_TREE)
    assert files_of(folders["none"]) == SETUP_TREE


def test_a_copy_that_does_not_match_its_source_is_refused_naming_the_line(tmp_path, body_request):
    given = given_files("record", BODY_2)
    log = given.files["record/log.jsonl"]
    first = log.split(b"\n", 1)[0]
    tampered = log.replace(first, first + b" ", 1)
    target = tmp_path / "tampered"
    with pytest.raises(FolderError, match="log.jsonl line 1: differs from source entry seq 1") as error:
        write_folder(
            target,
            body_request,
            GivenFiles({**given.files, "record/log.jsonl": tampered}, given.removed, BODY_2),
        )
    assert str(target / "given" / "record") in str(error.value)
    assert (target / "given" / "record" / "log.jsonl").is_file()


def test_a_copy_with_a_missing_blob_is_refused_naming_the_blob(tmp_path, body_request):
    given = given_files("record", BODY_2)
    blob = next(name for name in given.files if name.startswith("record/blobs/"))
    files = {name: data for name, data in given.files.items() if name != blob}
    with pytest.raises(FolderError, match=f"blobs/{blob.split('/')[-1]}: missing"):
        write_folder(tmp_path / "missing", body_request, GivenFiles(files, given.removed, BODY_2))


def test_the_record_setup_passes_the_blind_scan_for_body_2(tmp_path, body_request, scanner):
    target = tmp_path / "record"
    write_folder(target, body_request, given_files("record", BODY_2))
    assert folder.scan_folder(scanner, target) == []


def test_a_planted_term_in_a_recorded_bench_text_is_found_in_the_copy(tmp_path, body_request, scanner):
    term = next(name for name in scanner.terms.values() if name.isalpha())

    def build(store):
        return [
            ("start", {"application": "body-lab", "session": "s1"}),
            ("trial", {"note": term}),
            ("snapshot", {"for": "end", "files": {}}),
        ]

    (tmp_path / "sessions").mkdir()
    record = seal_record(tmp_path / "sessions" / "s1", build)
    target = tmp_path / "planted"
    write_folder(target, body_request, given_files("record", record))
    findings = folder.scan_folder(scanner, target)
    assert Finding("given/record/log.jsonl", 2, "term", term) in findings


def test_record_setup_is_scanned_only_through_the_record_levels(tmp_path, body_request, scanner):
    term = next(name for name in scanner.terms.values() if name.isalpha())

    def build(store):
        ref = store.put_blob(f"{term}\n".encode(), "dr-kiro", "text/markdown")
        return [
            ("start", {"application": "body-lab", "session": "s1"}),
            ("experiment", {"files": {"e.md": ref}}),
        ]

    (tmp_path / "sessions").mkdir()
    record = seal_record(tmp_path / "sessions" / "s1", build)
    target = tmp_path / "dr-kiro-text"
    write_folder(target, body_request, given_files("record", record))
    assert folder.scan_folder(scanner, target) == []


def test_unknown_setup_is_refused_by_name():
    with pytest.raises(FolderError, match="unknown setup 'both'"):
        given_files("both", BODY_2)


def test_an_unexpected_given_file_fails_the_scan(tmp_path, body_request, scanner):
    target = tmp_path / "extra"
    write_folder(target, body_request, given_files("none", BODY_2))
    (target / "given" / "notes.md").write_text("notes\n", encoding="utf-8")
    with pytest.raises(FolderError, match="given/notes.md"):
        folder.scan_folder(scanner, target)


@pytest.fixture
def confine(monkeypatch):
    monkeypatch.syspath_prepend(str(labhooks.SOURCES))
    return importlib.import_module("confine")


@pytest.fixture
def lab(tmp_path, body_request) -> Path:
    """A working folder in a temporary repository, resolved as the hook resolves its lab (the real bench-run
    folder is never used). The sibling run folder exists so that a reference to it resolves."""
    target = tmp_path / "repo" / "bench-run" / "build-from-spec" / RUN_ID
    write_folder(target, body_request, given_files("none", BODY_2))
    (target.parent / "run-0001").mkdir()
    return target.resolve()


def call(tool: str, path: str) -> dict:
    return {"tool_name": tool, "tool_input": {"path": path}}


@pytest.mark.parametrize(
    "event",
    [
        call("read_file", "../../../build-from-spec/requests/stop-ahead.toml"),
        call("read_file", "../../../sessions/body-lab/body-2/log.jsonl"),
        call("list_directory", "../../../sessions"),
        call("read_file", "../run-0001/request.md"),
        call("read_file", "../../../body-lab/lab/.kiro/specs/lab/tasks.md"),
        call("read_file", "../../../notebook/index.html"),
        call("fs_write", "../../../sessions/body-lab/body-2/x.md"),
        call("fs_write", "../run-0001/request.md"),
        call("read_file", "~/dev/llm/hackathon/dr-kiro-lab-notebook/sessions/body-lab/body-2/log.jsonl"),
        call("fs_write", ".kiro/hooks/confine.py"),
        call("fs_write", ".kiro/agents/reader.json"),
        call("str_replace", ".kiro/steering/method.md"),
    ],
)
def test_the_confine_hook_refuses_paths_outside_the_working_folder(confine, lab, event):
    assert confine.decide(event, lab) in (confine.OUTSIDE, confine.PROTECTED)


def test_the_confine_hook_refuses_an_absolute_path_into_the_repository(confine, lab):
    absolute = str(lab.parents[2] / "sessions" / "body-lab" / "body-2" / "log.jsonl")
    assert confine.decide(call("read_file", absolute), lab) == confine.OUTSIDE


def test_the_confine_hook_allows_paths_inside_the_working_folder(confine, lab):
    allowed = [
        call("read_file", "request.md"),
        call("read_file", "given/design.md"),
        call("read_file", ".kiro/steering/reader.md"),
        call("read_file", ".kiro/hooks/confine.py"),
        call("fs_write", "experiments/e1.py"),
        call("fs_write", "given/notes.md"),
    ]
    for event in allowed:
        assert confine.decide(event, lab) is None, event
