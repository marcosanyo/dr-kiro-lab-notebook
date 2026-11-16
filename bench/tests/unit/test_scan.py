import json
from pathlib import Path

import pytest

from bench.core.outcome import Quote, message
from bench.record.store import Store, authored
from bench.scan.patterns import Patterns
from bench.scan.scan import Scanner, main
from bench.scan.terms import AppSources, LabLayout, ScanError, load_app, load_stop_list
from bench.scan.tokens import term_tokens, tokenize

REPO = Path(__file__).resolve().parents[3]
FAKE_CONFIG = REPO / "bench" / "src" / "bench" / "fake" / "scan_sources.toml"
STOP_LIST = REPO / ".kiro" / "blind-scan" / "stop-list.txt"

MJCF = """<mujoco model="gadget_7">
  <default><default class="flexor"/></default>
  <asset><material name="plastic"/><texture name="dots" builtin="checker"/></asset>
  <worldbody>
    <body name="lowerFrame"><joint name="pivotA" type="hinge"/>
      <geom name="paddle" material="plastic"/>
    </body>
  </worldbody>
  <actuator><position name="pusher" joint="pivotA" class="flexor"/></actuator>
</mujoco>
"""
WIRING = {"channels": [{"channel": 0, "actuator": "pusher", "sign": 1}], "control_hz": 50}


def app(tmp_path: Path, *, allow: tuple[str, ...] = (), lab: LabLayout | None = None) -> AppSources:
    model = tmp_path / "model"
    model.mkdir(exist_ok=True)
    (model / "gadget_7.xml").write_text(MJCF)
    (model / "gadget_7.wiring.json").write_text(json.dumps(WIRING))
    config = tmp_path / "scan_sources.toml"
    config.write_text(
        'adapter = "bench.fake.adapter:FakeAdapter"\n'
        'solver_dirs = ["casefolder"]\n'
        '[[source]]\npath = "model/gadget_7.xml"\nextractor = "mjcf"\n'
        '[[source]]\npath = "model/gadget_7.wiring.json"\nextractor = "wiring-json"\n'
    )
    loaded = load_app(config)
    return AppSources(loaded.names, loaded.file_names, loaded.solver_dirs, loaded.allow + allow, lab)


def test_tokenizer() -> None:
    assert (
        term_tokens("quindle_arm")
        == term_tokens("quindleArm")
        == term_tokens("Quindle-Arm")
        == ("quindle", "arm")
    )
    assert term_tokens("gadget_07") == term_tokens("gadget07") == ("gadget", "07")
    assert term_tokens("XMLParser") == ("xml", "parser")
    assert [t.text for t in tokenize("legAmp=0.5")] == ["leg", "amp", "0", "5"]


def test_extractors(tmp_path: Path) -> None:
    sources = app(tmp_path)
    assert set(sources.names) == {
        "gadget_7",
        "flexor",
        "plastic",
        "dots",
        "lowerFrame",
        "pivotA",
        "paddle",
        "pusher",
    }
    assert sources.file_names == ("gadget_7.xml", "gadget_7.wiring.json")
    assert "drive" in sources.allow and "lost" in sources.allow


def test_terms_found_in_all_forms_at_builder_level(tmp_path: Path) -> None:
    scanner = Scanner([app(tmp_path)], [], local_paths=())
    for text in [
        "lower frame",
        "LOWER_FRAME",
        "lower-frames",
        "lowerFrame",
        "the pushers",
        "pivot a",
        "gadget 7",
    ]:
        assert [f.kind for f in scanner.scan_text(text, "builder", "x")] == ["term"], text
    assert scanner.scan_text("lower the frame; a pivot", "builder", "x") == []
    assert scanner.scan_text("pushed", "builder", "x") == []


def test_dr_kiro_level_ignores_terms_but_not_paths(tmp_path: Path) -> None:
    scanner = Scanner([app(tmp_path)], [], local_paths=())
    assert scanner.scan_text("channel 2 acts like a paddle", "dr-kiro", "x") == []
    kinds = [f.kind for f in scanner.scan_text("see ../model/gadget_7.xml", "dr-kiro", "x")]
    assert kinds.count("path") == 2 and "file name" in kinds


def test_allow_list_and_stop_list(tmp_path: Path) -> None:
    scanner = Scanner([app(tmp_path, allow=("paddle",))], ["plastic", "dots"], local_paths=())
    assert scanner.scan_text("paddle, plastic and dots", "builder", "x") == []
    assert [f.match for f in scanner.scan_text("flexor", "builder", "x")] == ["flexor"]


@pytest.mark.parametrize(
    "text",
    [
        "../secret",
        "..\\up",
        "/home/user/x",
        "at /projects/sandbox",
        "~/notes",
        "C:\\Users\\x",
        "/Users/someone/Documents/run",
        "/private/var/folders/xy/T/tmp1",
        "/Volumes/Disk/x",
        "/opt/tool",
        "/etc/hosts",
        "/var/log/x",
        "model/thing",
        "Adapter/run.py",
        "casefolder/0/U",
    ],
)
def test_paths(text: str) -> None:
    assert [m.kind for m in Patterns([], ["casefolder"], ()).find(text)] == ["path"]


@pytest.mark.parametrize(
    "text",
    [
        "(t + a)/period/2",
        "amp /2",
        "m/s",
        "and/or",
        "1/2",
        "https://example.org/a",
        "the model is ...",
        "remodel/x",
    ],
)
def test_not_paths(text: str) -> None:
    assert Patterns([], [], ()).find(text) == []


@pytest.mark.parametrize(
    "text",
    [
        "AKIA" + "ABCDEFGHIJKLMNOP",
        "-----BEGIN RSA PRIVATE KEY-----",
        "ghp_" + "a" * 36,
        "github_pat_" + "a" * 40,
        "password = 'abcdefghijklmnop1234'",
        "aws_secret_access_key=abcdefghijklmnopqrstuvwxyz",
    ],
)
def test_credentials_are_found_and_redacted(text: str) -> None:
    (match,) = Patterns([], [], ()).find(text)
    assert match.kind == "credential" and match.text.endswith("…") and len(match.text) <= 5


def test_message_spans_keep_their_level(tmp_path: Path) -> None:
    scanner = Scanner([app(tmp_path)], [], local_paths=())
    quoted = message("cannot evaluate ", Quote("paddle_amp = 2", "experiments/e.py", 3))
    assert scanner.scan_message(quoted, "out") == []
    assert [f.kind for f in scanner.scan_message(message("the paddle moved"), "out")] == ["term"]


def test_lab_levels_and_sidecars(tmp_path: Path) -> None:
    lab = tmp_path / "lab"
    (lab / "experiments").mkdir(parents=True)
    (lab / "spec").mkdir()
    (lab / "experiments" / "e1.py").write_text("paddle = 1\n")
    (lab / "spec" / "requirements.md").write_text("Maybe a paddle.\n")
    (lab / "steering.md").write_text("Line one.\nThe paddle is here.\n")
    scanner = Scanner(
        [app(tmp_path, lab=LabLayout(lab, ("experiments/**", "spec/requirements.md")))], [], local_paths=()
    )
    (finding,) = scanner.scan_paths([lab])
    assert (Path(finding.file).name, finding.line, finding.kind) == ("steering.md", 2, "term")

    out = tmp_path / "site" / "index.html"
    out.parent.mkdir()
    out.write_text("Dr. Kiro: paddle\nOurs: plain\n")
    with pytest.raises(ScanError, match="no level source"):
        scanner.scan_paths([out])
    sidecar = out.with_name("index.html.authors.json")
    sidecar.write_text(
        json.dumps(
            {
                "ranges": [
                    {"start": 0, "end": 17, "author": "dr-kiro"},
                    {"start": 17, "end": 29, "author": "bench"},
                ]
            }
        )
    )
    assert scanner.scan_paths([out.parent]) == []
    out.write_text("Dr. Kiro: paddle\nOurs: paddle\n")
    sidecar.write_text(
        json.dumps(
            {
                "ranges": [
                    {"start": 0, "end": 17, "author": "dr-kiro"},
                    {"start": 17, "end": 30, "author": "bench"},
                ]
            }
        )
    )
    (finding,) = scanner.scan_paths([out])
    assert finding.line == 2
    sidecar.write_text(json.dumps({"ranges": [{"start": 0, "end": 10, "author": "dr-kiro"}]}))
    with pytest.raises(ScanError, match="cover"):
        scanner.scan_paths([out])


def test_record_levels(tmp_path: Path) -> None:
    (tmp_path / "state").mkdir()
    store = Store.create(tmp_path / "state" / "s1")
    store.append("start", {"note": authored("dr-kiro", "a paddle?"), "knobs": ["drive"]})
    store.append(
        "snapshot",
        {"file": store.put_blob(b"# H1\nmaybe a paddle\n", "dr-kiro", "text/markdown")},
    )
    store.append("refusal", {"message": [authored("bench", "plain words")]})
    scanner = Scanner([app(tmp_path)], [], local_paths=())
    assert scanner.scan_paths([store.folder]) == []
    store.append("failure", {"reason": authored("bench", "the pusher stalled")})
    (finding,) = scanner.scan_paths([store.folder])
    assert finding.line == 4 and finding.kind == "term"
    store.append("failure", {"pusher": 1})
    assert len(scanner.scan_paths([store.folder])) == 2  # keys are bench text too


def test_record_with_unknown_media_or_author_fails(tmp_path: Path) -> None:
    (tmp_path / "state").mkdir()
    store = Store.create(tmp_path / "state" / "s1")
    store.append("start", {"file": store.put_blob(b"\x00", "bench", "application/octet-stream")})
    with pytest.raises(ScanError, match="media type"):
        Scanner([app(tmp_path)], [], local_paths=()).scan_paths([store.folder])


def test_missing_sources_fail(tmp_path: Path) -> None:
    with pytest.raises(ScanError, match="not found"):
        load_app(tmp_path / "missing.toml")
    with pytest.raises(ScanError, match="stop list not found"):
        load_stop_list(tmp_path / "missing.txt")
    config = tmp_path / "scan_sources.toml"
    config.write_text(
        'adapter = "bench.fake.adapter:FakeAdapter"\n[[source]]\npath = "x.xml"\nextractor = "mjcf"\n'
    )
    with pytest.raises(ScanError, match="source file"):
        load_app(config)
    config.write_text(
        'adapter = "bench.fake.adapter:FakeAdapter"\n[[source]]\npath = "x.xml"\nextractor = "guess"\n'
    )
    with pytest.raises(ScanError, match="unknown extractor"):
        load_app(config)
    bad = tmp_path / "stop.txt"
    bad.write_text("Upper Arm\n")
    with pytest.raises(ScanError, match="one lowercase word"):
        load_stop_list(bad)


def test_repository_stop_list_loads() -> None:
    assert load_stop_list(STOP_LIST) == (
        ("bone", "grid", "hide", "metal", "rubber", "floor", "top")
        # wind-tunnel, approved by the user in task 12.4
        + ("body", "flow", "height", "depth", "speed", "density", "gap", "picture", "settings", "time", "end")
        + ("number", "arc", "line", "point", "move", "turn", "value", "forces")
        # wind-tunnel lab, approved by the user in task 13.1 ("settings" was already listed)
        + ("name", "none", "run", "raw", "field", "keep", "p", "functions", "include", "method", "replace")
        + ("behind", "points")
        # wind-tunnel session wt-001, common words found when sealing (wind-tunnel Decision 42)
        + ("application", "image")
        # wind-tunnel session wt-003 and the sweep of the bench's own text (wind-tunnel Decision 44)
        + ("empty", "columns", "rows", "default", "domain")
        # stems of builder-chosen file names that are ordinary words (wind-tunnel Decision 46)
        + ("geometry", "constants", "monitors")
    )


def test_fake_sources_and_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fake = load_app(FAKE_CONFIG)
    assert "zorblat" in fake.names and "gain" in fake.allow
    out = tmp_path / "out.txt"
    out.write_text("The zorblat turned.\n")
    out.with_name("out.txt.authors.json").write_text(
        json.dumps({"ranges": [{"start": 0, "end": 20, "author": "bench"}]})
    )
    assert main(["--config", str(FAKE_CONFIG), "--stop-list", str(STOP_LIST), str(out)]) == 1
    assert "out.txt:1: term: zorblat" in capsys.readouterr().out
    out.write_text("The gain on the grid.\n")
    out.with_name("out.txt.authors.json").write_text(
        json.dumps({"ranges": [{"start": 0, "end": 22, "author": "bench"}]})
    )
    assert main(["--config", str(FAKE_CONFIG), "--stop-list", str(STOP_LIST), str(out)]) == 0
    assert main(["--config", str(FAKE_CONFIG), "--stop-list", str(tmp_path / "none"), str(out)]) == 2


def test_local_paths_are_flagged_whatever_their_root(tmp_path: Path) -> None:
    patterns = Patterns([], [], ["/srvx/build/me", "/"])
    assert [m.kind for m in patterns.find("logs in /srvx/build/me/x")] == ["path"]
    assert patterns.find("logs in /srvx/build/mexico") == []
    assert patterns.find("a / b") == []  # "/" alone is never a local path


def test_from_config_flags_home_and_repository(tmp_path: Path) -> None:
    scanner = Scanner.from_config([FAKE_CONFIG], STOP_LIST)
    repo = str(REPO.resolve())
    assert [f.kind for f in scanner.scan_text(f"see {repo}/notes", "dr-kiro", "x")] == ["path"]
    home = str(Path.home().resolve())
    assert "path" in {f.kind for f in scanner.scan_text(f"see {home}/x", "dr-kiro", "x")}


def test_repository_root_is_required(tmp_path: Path) -> None:
    from bench.scan.scan import repository_root

    with pytest.raises(ScanError, match="not inside a git repository"):
        repository_root(tmp_path)


def test_digit_only_names_are_never_terms(tmp_path: Path) -> None:
    sources = AppSources(("01", "7", "1_2", "gadget_01"), (), (), (), None)
    scanner = Scanner([sources], [], local_paths=())
    assert scanner.scan_text("trial 01, 7 and 1 2", "builder", "x") == []
    assert [f.kind for f in scanner.scan_text("gadget 01", "builder", "x")] == ["term"]


def test_pictures_in_a_lab_are_checked_as_pictures(tmp_path: Path) -> None:
    from bench.pictures import _png_chunk, encode_png

    lab = tmp_path / "lab"
    (lab / "pictures").mkdir(parents=True)
    png = encode_png([[(0, 0, 0)]])
    (lab / "pictures" / "E1-T1.png").write_bytes(png)
    scanner = Scanner([app(tmp_path, lab=LabLayout(lab, ("experiments/**",)))], [], local_paths=())
    assert scanner.scan_paths([lab]) == []
    end = png.rindex(b"IEND") - 4
    (lab / "pictures" / "E1-T2.png").write_bytes(png[:end] + _png_chunk(b"tEXt", b"a\x00paddle") + png[end:])
    (finding,) = scanner.scan_paths([lab])
    assert finding.kind == "picture"
    (lab / "pictures" / "E1-T2.png").unlink()
    (lab / "data.bin").write_bytes(b"\xff\xfe\x00")
    with pytest.raises(ScanError, match="not UTF-8"):
        scanner.scan_paths([lab])


# File-name stems and the stop list (lab-bench Requirement 20, design C1)
STEM_FILES = ("p.in", "U.in", "geometry.py", "mesh.py", "Allrun", "X", "solver_output.json")


def _file_name_hits(patterns: Patterns, text: str) -> list[str]:
    return [m.text for m in patterns.find(text) if m.kind == "file name"]


def test_one_character_stem_is_not_a_file_name() -> None:
    patterns = Patterns(STEM_FILES, [], [])
    assert _file_name_hits(patterns, "the pressure P in Pa and U = 3") == []
    assert _file_name_hits(patterns, "open p.in and U.in") == ["p.in", "U.in"]


def test_stop_listed_stem_is_not_a_file_name_but_the_full_name_is() -> None:
    patterns = Patterns(STEM_FILES, [], [], stop_list=["mesh", "solver_output"])
    assert _file_name_hits(patterns, "the Mesh is fine, and solver_output too") == []
    assert _file_name_hits(patterns, "see mesh.py") == ["mesh.py"]
    assert _file_name_hits(patterns, "see solver_output.json") == ["solver_output.json"]


def test_unlisted_stem_is_still_a_file_name() -> None:
    patterns = Patterns(STEM_FILES, [], [], stop_list=["mesh"])
    assert _file_name_hits(patterns, "the geometry here") == ["geometry"]
    # The full name and its stem are reported separately, as before.
    assert _file_name_hits(patterns, "geometry.py") == ["geometry.py", "geometry"]


def test_name_without_a_dot_is_a_full_name_even_when_short_or_stop_listed() -> None:
    patterns = Patterns(["X", "mesh"], [], [], stop_list=["mesh", "x"])
    assert _file_name_hits(patterns, "run X and mesh") == ["X", "mesh"]


def test_stem_and_stop_list_apply_at_both_levels(tmp_path: Path) -> None:
    sources = AppSources((), ("p.in", "U.in", "geometry.py", "mesh.py"), (), (), None)
    scanner = Scanner([sources], ["mesh"], local_paths=[])
    for level in ("builder", "dr-kiro"):
        quiet = scanner.scan_text("the pressure P in Pa and U = 3, the mesh", level, "x")
        assert [f for f in quiet if f.kind == "file name"] == [], level
        loud = scanner.scan_text("open p.in, U.in, mesh.py and geometry.py; geometry", level, "x")
        assert sorted(f.match for f in loud if f.kind == "file name") == sorted(
            ["p.in", "U.in", "mesh.py", "geometry.py", "geometry", "geometry"]
        ), level


def test_real_stop_list_lets_a_bare_stem_word_pass_but_not_the_file_name_or_mesh() -> None:
    """Decision 46: `geometry`, `constants` and `monitors` pass as words at the Dr. Kiro level; the full file
    names are found at both levels; `mesh` stays forbidden."""
    sources = AppSources(
        ("geometry", "mesh"), ("geometry.py", "mesh.py", "constants.toml", "monitors.in"), (), (), None
    )
    scanner = Scanner([sources], load_stop_list(STOP_LIST), local_paths=[])
    for word in ("geometry", "constants", "monitors"):
        assert scanner.scan_text(f"the {word} of the body", "dr-kiro", "x") == [], word
        assert scanner.scan_text(f"the {word} of the body", "builder", "x") == [], word
    for level in ("builder", "dr-kiro"):
        names = {
            f.match for f in scanner.scan_text("see geometry.py, constants.toml, monitors.in", level, "x")
        }
        assert names >= {"geometry.py", "constants.toml", "monitors.in"}, level
        assert [f.match for f in scanner.scan_text("the mesh", level, "x") if f.kind == "file name"] == [
            "mesh"
        ], level
    assert [f.match for f in scanner.scan_text("the mesh", "builder", "x") if f.kind == "term"] == ["mesh"]
