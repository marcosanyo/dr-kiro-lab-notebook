"""dr-kiro task 3: `bench-new-session` (Requirements 5.2, 5.3, 7.3)."""

from pathlib import Path

from bench.core.session import Session
from bench.drkiro.lab import BUILDER_FILES, FILES, TEMPLATES, make_lab
from bench.drkiro.session import main
from bench.frontend import config as config_file
from labkit import FAKE_SOURCES, STOP_LIST


def args(root: Path, session_id: str) -> list[str]:
    return [
        "--application",
        "fake",
        "--adapter",
        "bench.fake.adapter:FakeAdapter",
        "--scan-sources",
        str(FAKE_SOURCES),
        "--stop-list",
        str(STOP_LIST),
        "--lab",
        str(root / "lab"),
        "--state",
        str(root / "state"),
        "--sessions",
        str(root / "sessions"),
        "--session-id",
        session_id,
        "--seed",
        "1",
        "--config-out",
        str(root / f"{session_id}.toml"),
    ]


def test_new_session_resets_the_lab_and_refuses_while_one_is_open(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]  # noqa: E501
    for name in ("lab", "state", "sessions"):
        (tmp_path / name).mkdir()
    make_lab(tmp_path / "lab")
    assert main(args(tmp_path, "s1")) == 0
    lab = tmp_path / "lab"
    for target in TEMPLATES.values():
        assert (lab / target).is_file()

    # Dr. Kiro's files from the session, then a second start while s1 is still open.
    (lab / "experiments" / "e1.py").write_text("# H1\n")
    (lab / "pictures" / "E1-T1.png").write_bytes(b"x")
    (lab / TEMPLATES["requirements.md"]).write_text("# Requirements\n\n### H1: changed\n")
    assert main(args(tmp_path, "s2")) == 2
    assert "session s1 is not sealed" in capsys.readouterr().err
    assert (lab / "experiments" / "e1.py").exists()  # nothing changed

    config = config_file.load(tmp_path / "s1.toml")
    assert config.resume is True
    assert config.session.discovered_table == "required"
    session = Session.open(config.session)
    assert session.state.sealed is None
    session.stop("test over")
    session.close()

    assert main(args(tmp_path, "s2")) == 0
    files = sorted(p.relative_to(lab).as_posix() for p in lab.rglob("*") if p.is_file())
    expected = set(BUILDER_FILES.values()) | set(TEMPLATES.values()) | {".gitignore"}
    hooks = {p for p in files if p.startswith(".kiro/hooks/")}
    assert set(files) - hooks == expected
    assert (lab / TEMPLATES["requirements.md"]).read_bytes() == (FILES / "requirements.md").read_bytes()
    assert main(args(tmp_path, "s2")) == 2  # a session id is used once
