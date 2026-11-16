"""Every trial sheet of the committed records passes the sheet check (task 5.1).

records.py does not exist yet (task 4.1), so this test reads the trial entries and picture blobs straight from
`sessions/`. The cell sizes asserted are facts of the committed records (requirements Decision 15).
"""

import json
from pathlib import Path

from notebook.layouts import Cells, check_sheet, layout_for, load

NOTEBOOK = Path(__file__).resolve().parents[2]
SESSIONS = NOTEBOOK.parent / "sessions"
EXPECTED_CELLS = {"body-lab": Cells(320, 180), "wind-tunnel": Cells(400, 200)}


def _trials() -> list[tuple[str, str, Path, dict]]:
    found = []
    for log in sorted(SESSIONS.glob("*/*/log.jsonl")):
        folder = log.parent
        application = folder.parent.name
        for line in log.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            if entry["kind"] == "trial":
                found.append((application, f"sessions/{application}/{folder.name}", folder, entry["body"]))
    return found


def test_every_real_sheet_passes_with_its_cell_size() -> None:
    layouts = load(NOTEBOOK / "layouts.toml")
    trials = _trials()
    assert {application for application, *_ in trials} == {"body-lab", "wind-tunnel"}
    for application, record, folder, body in trials:
        layout = layout_for(layouts, application, record)
        picture = body["picture"]
        data = (folder / "blobs" / picture["blob"]).read_bytes()
        cells = check_sheet(layout, record, body["trial"], picture["media"], data)
        assert cells == EXPECTED_CELLS[application], (record, body["trial"])
