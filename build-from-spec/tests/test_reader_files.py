"""The reader's builder files and the README (Requirements 1.1, 9.1, 9.2, 9.4, 9.6)."""

import json
from importlib import resources
from pathlib import Path

import pytest
from bench.scan.scan import Scanner

from build_from_spec.apps import APPS

REPO_ROOT = Path(__file__).resolve().parents[2]
FILES = resources.files("build_from_spec") / "files"
DR_KIRO_JSON = resources.files("bench.drkiro") / "files" / "dr-kiro.json"
STOP_LIST = REPO_ROOT / ".kiro" / "blind-scan" / "stop-list.txt"
TEMPLATES = ("requirements.md", "design.md", "tasks.md")
BUILDER_TEXT = ("reader.json", "reader-prompt.md", "reader.md", *TEMPLATES)


def read(name: str) -> str:
    return (FILES / name).read_text(encoding="utf-8")


def test_reader_json_is_dr_kiro_json_with_name_description_and_prompt_changed_and_the_env_entry_removed():
    reader = json.loads(read("reader.json"))
    dr_kiro = json.loads(DR_KIRO_JSON.read_text(encoding="utf-8"))
    assert reader["name"] == "reader"
    assert reader["prompt"] == "file://./reader-prompt.md"
    assert isinstance(reader["description"], str) and "\n" not in reader["description"]
    for name in ("name", "description", "prompt"):
        del reader[name], dr_kiro[name]
    # K31: no other difference. Neither bench entry has an env entry: bench-mcp finds the session through the
    # folder's session file (lab-bench design D2).
    assert "env" not in reader["mcpServers"]["bench"]
    assert reader == dr_kiro


def test_reader_has_read_write_and_bench_tools_and_no_shell():
    reader = json.loads(read("reader.json"))
    assert reader["tools"] == ["read", "write", "@bench"]
    assert "shell" not in json.dumps(reader)
    assert reader["mcpServers"]["bench"]["command"] == "bench-mcp"


def test_templates_hold_no_hypothesis_no_experiment_no_number_and_no_table():
    for name in TEMPLATES:
        text = read(name)
        assert "```prediction" not in text
        assert "PHASE" not in text
        assert "## Discovered spec" not in text
        assert not any(ch.isdigit() for ch in text), name


def test_reader_steering_holds_the_relied_on_line_and_the_phase_rule():
    text = read("reader.md")
    assert text.startswith("---\ninclusion: always\n---\n")
    assert "# relies on: " in text
    assert 'PHASE = "best"' in text


def test_reader_steering_says_nothing_about_the_setup():
    text = read("reader.md").lower()
    for word in ("setup", "record", "reduced", "source", "sessions/", "spec, none"):
        assert word not in text, word


def test_reader_prompt_names_request_given_and_end_session():
    text = read("reader-prompt.md")
    assert "request.md" in text and "given/" in text and "end_session" in text
    assert "ask the user" in text


@pytest.mark.parametrize("name", BUILDER_TEXT)
def test_builder_files_pass_the_blind_scan_at_the_builder_level(name):
    scanner = Scanner.from_config([REPO_ROOT / APPS["body-lab"].scan_sources], STOP_LIST)
    assert scanner.scan_text(read(name), "builder", name) == []


def test_readme_holds_the_start_and_continue_lines_and_the_install_command():
    text = (REPO_ROOT / "build-from-spec" / "README.md").read_text(encoding="utf-8")
    assert "Begin the session." in text
    assert "Continue the session." in text
    install_lines = [line for line in text.splitlines() if line.startswith("uv tool install")]
    assert len(install_lines) == 1, install_lines
    for part in (
        "--editable './bench[frontend]'",
        "--with-editable ./body-lab/adapter",
        "--with-editable ./build-from-spec",
        "--with-editable ./wind-tunnel/adapter",
        "--with-executables-from build-from-spec",
        "--reinstall",
    ):
        assert part in install_lines[0], part
    assert "## Checks at implementation" in text
    assert "## Runs" in text
