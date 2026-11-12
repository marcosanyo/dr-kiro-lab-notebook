"""Task 18: picture files, Session.fail and the picture scan (Requirements 11.3, 15.9, 17.13-17.16)."""

import json
from pathlib import Path

import anyio
from mcp.client import Client

from bench.core.outcome import BenchFailure
from bench.frontend.pictures import NOT_DELIVERED
from bench.frontend.server import BenchServer
from bench.pictures import _png_chunk
from bench.record.chain import verify
from bench.scan.scan import Scanner, local_paths
from bench.scan.terms import LabLayout, load_app, load_stop_list
from labkit import FAKE_SOURCES, STOP_LIST, Lab, exp_file, hyp_block

STATEMENT = "WHEN amp rises, THE distance SHALL rise."
P1 = {"id": "P1", "range": [0.4, 0.6], "when": {"amp": 0.5, "gain": 1.0}}


def run(lab: Lab, srv: BenchServer, rows: list) -> object:
    lab.add(hyp_block("H1", STATEMENT, P1))
    path = lab.experiment("e1.py", exp_file("H1", rows))

    async def main() -> object:
        async with Client(srv.mcp) as client:
            await client.call_tool("register_hypothesis", {"id": "H1"})
            return await client.call_tool("run_experiment", {"path": path})

    return anyio.run(main)


def recorded_pictures(srv: BenchServer) -> list[bytes]:
    store = srv.session.store
    return [store.read_blob(e["body"]["picture"]) for e in store.entries if e["kind"] == "trial"]


def test_picture_file_holds_the_adapter_bytes_and_the_record_keeps_its_own(lab: Lab) -> None:
    srv = BenchServer(lab.start())
    result = run(lab, srv, [[0.5, 1.0], [0.25, 1.0]])
    data = json.loads(result.content[0].text)  # type: ignore[attr-defined]
    paths = [t["picture"] for t in data["trials"]]
    assert paths == ["pictures/E1-T1.png", "pictures/E1-T2.png"]
    assert [(lab.lab / p).read_bytes() for p in paths] == recorded_pictures(srv)
    assert not list((lab.lab / "pictures").glob(".*.tmp"))
    original = recorded_pictures(srv)
    (lab.lab / paths[0]).write_bytes(b"changed by Dr. Kiro")
    assert recorded_pictures(srv) == original


def test_unwritable_pictures_folder_is_a_recorded_bench_failure(lab: Lab) -> None:
    srv = BenchServer(lab.start())
    (lab.lab / "pictures").write_text("a file where the folder should be")
    result = run(lab, srv, [[0.5, 1.0]])
    assert result.is_error and result.content[0].text == NOT_DELIVERED  # type: ignore[attr-defined]
    kinds = [e["kind"] for e in srv.session.store.entries]
    assert kinds[-2:] == ["failure", "seal"]
    assert srv.session.state.sealed == "stopped"
    assert "pictures" in (srv.session.last_failure_detail or "")
    verify(srv.session.sealed_path, sealed=True)


def test_fail_after_sealing_records_nothing(lab: Lab) -> None:
    session = lab.start()
    session.stop("test over")
    count = len(session.store.entries)
    outcome = session.fail("run", NOT_DELIVERED, "late")
    assert isinstance(outcome, BenchFailure) and len(session.store.entries) == count


def _scanner(lab: Lab) -> Scanner:
    app = load_app(FAKE_SOURCES)
    layout = LabLayout(lab.lab, ("experiments/**", ".kiro/specs/**"))
    sources = type(app)(app.names, app.file_names, app.solver_dirs, app.allow, layout)
    return Scanner([sources], load_stop_list(STOP_LIST), local_paths=local_paths(STOP_LIST))


def test_scan_passes_on_a_lab_with_pictures_and_finds_a_picture_with_text(lab: Lab) -> None:
    srv = BenchServer(lab.start())
    run(lab, srv, [[0.5, 1.0]])
    scanner = _scanner(lab)
    assert scanner.scan_paths([lab.lab]) == []
    png = (lab.lab / "pictures" / "E1-T1.png").read_bytes()
    end = png.rindex(b"IEND") - 4
    leaky = png[:end] + _png_chunk(b"tEXt", b"Comment\x00hello") + png[end:]
    planted = Path(lab.lab / "pictures" / "planted.png")
    planted.write_bytes(leaky)
    (finding,) = scanner.scan_paths([lab.lab])
    assert finding.kind == "picture" and finding.file == str(planted)
