"""Told-set export (wind-tunnel Requirement 2.1-2.4)."""

import re

import pytest
from bench.frontend.describe import declaration_text, descriptions

from wind_tunnel.declaration import scan_adapter
from wind_tunnel.told_set import main


def test_two_runs_write_identical_bytes(tmp_path):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    main(["--out", str(a)])
    main(["--out", str(b)])
    assert a.read_bytes() == b.read_bytes()


def test_file_equals_declaration_text_in_tool_descriptions(tmp_path):
    out = tmp_path / "told.txt"
    main(["--out", str(out)])
    text = out.read_text(encoding="utf-8")
    decl = scan_adapter().declaration()
    assert text == declaration_text(decl) + "\n"
    assert text.endswith("\n") and not text.endswith("\n\n")
    descs = descriptions(decl, "required")
    assert descs["run_experiment"].endswith(text[:-1])
    assert descs["register_hypothesis"].endswith(text[:-1])


def test_file_holds_no_path_version_or_session_value(tmp_path):
    out = tmp_path / "told.txt"
    main(["--out", str(out)])
    text = out.read_text(encoding="utf-8")
    assert str(tmp_path) not in text
    assert "told.txt" not in text
    assert not re.search(r"\d+\.\d+\.\d+", text)
    assert not re.search(r"(?:^|\s)(?:/|~/|\.\./)\w", text)
    assert not re.search(r"\b(?:session|version)\b", text, re.IGNORECASE)


def test_path_is_required():
    with pytest.raises(SystemExit) as info:
        main([])
    assert info.value.code != 0
