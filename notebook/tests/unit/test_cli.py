"""The command line: required options, the output-folder check, messages and exit codes (Req. 1.3, 1.4)."""

from pathlib import Path

import pytest

from notebook import cli
from notebook.inputs import check_out

# Paths that do not exist: if the command line read one, the error would name it instead of the option.
OPTIONS = {
    "--sessions": "no-such/sessions",
    "--requests": "no-such/requests",
    "--app": "no-such/notebook",
    "--layouts": "no-such/layouts.toml",
    "--words": "no-such/words.txt",
    "--scan-config": "no-such/scan_sources.toml",
    "--stop-list": "no-such/stop-list.txt",
    "--out": "no-such/out",
}


def _argv(without: str | None = None, out: Path | None = None) -> list[str]:
    argv: list[str] = []
    for option, value in OPTIONS.items():
        if option == without:
            continue
        if option == "--out" and out is not None:
            value = str(out)
        argv += [option, value]
    return argv


@pytest.mark.parametrize("option", list(OPTIONS))
def test_each_missing_option_is_named_and_exits_2(option, tmp_path, capsys):
    # A non-empty output folder: if the parser reached the output check, the error would name the folder.
    out = tmp_path / "out"
    out.mkdir()
    (out / "keep").write_text("x")
    argv = _argv(without=option, out=out if option != "--out" else None)
    with pytest.raises(SystemExit) as stop:
        cli.main(argv)
    assert stop.value.code == 2
    err = capsys.readouterr().err
    assert f"notebook-build: arguments: the following arguments are required: {option}" in err
    assert str(out) not in err.splitlines()[-1]


def test_scan_config_may_be_given_more_than_once(tmp_path):
    argv = _argv(out=tmp_path / "out") + ["--scan-config", "no-such/other.toml"]
    inputs = cli.parse(argv)
    assert inputs.scan_configs == (Path("no-such/scan_sources.toml"), Path("no-such/other.toml"))
    assert inputs.out == tmp_path / "out"


def test_non_empty_out_is_refused_naming_it(tmp_path, capsys):
    out = tmp_path / "out"
    out.mkdir()
    (out / "index.html").write_text("old")
    assert cli.main(_argv(out=out)) == 1
    err = capsys.readouterr().err
    assert err == f"notebook-build: {out}: the output folder is not empty; give a new or empty folder\n"
    assert (out / "index.html").read_text() == "old"


def test_out_that_is_a_file_is_refused(tmp_path):
    out = tmp_path / "out"
    out.write_text("x")
    with pytest.raises(cli.NotebookError) as error:
        check_out(out)
    assert error.value.where == str(out)


def test_absent_and_empty_out_pass_the_check(tmp_path):
    check_out(tmp_path / "absent")
    empty = tmp_path / "empty"
    empty.mkdir()
    check_out(empty)
    assert not (tmp_path / "absent").exists()


def test_a_failed_check_exits_1_naming_the_input_and_writes_nothing(tmp_path, capsys):
    assert cli.main(_argv(out=tmp_path / "out")) == 1
    err = capsys.readouterr().err
    assert err.startswith("notebook-build: no-such/scan_sources.toml") or err.startswith(
        "notebook-build: blind scan: "
    )
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / ".out.staging").exists()
