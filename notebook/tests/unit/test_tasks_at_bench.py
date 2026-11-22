"""Dr. Kiro's tasks at the bench when Dr. Kiro follows the steering: a task line before each run, ticked before
its verdict (notebook-shelf Requirement 4.3, Decision 9). The record is a fake session; nothing here is a result."""

import pytest

from fixtures.choices import write_app
from fixtures.session import DESIGN_START, END_TABLE, Lab, exp_file, hyp_block, ok
from notebook import choices, layouts, records
from notebook.pages import shelf

LAYOUTS = (
    "[fake]\nframes = 1\nrows = 1\ncolumns = 1\ngap = 0\ninterval = 200\n"
    'source = "test fixture: one 8 x 8 picture"\n'
)
HEAD = "# Tasks\n\n## Map the system\n\n"
END = "\n## End\n\n- [ ] Fill the Discovered spec table and end the session\n"


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    root = tmp_path_factory.mktemp("tasks-at-bench")
    lab = Lab(root / "lab")
    session = lab.start()
    lab.write("tasks.md", HEAD + "- [ ] E1 / H1: amp at gain 1\n" + END)
    lab.add(
        hyp_block(
            "H1",
            "WHEN amp rises at gain 1, THE distance SHALL rise.",
            {"id": "P1", "range": [0.25, 0.35], "label": "not-comparable", "when": {"amp": 0.3, "gain": 1.0}},
        )
    )
    ok(session.register("H1"))
    sweep = [[a, 1.0] for a in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6)]
    ok(session.run(lab.experiment("e1_sweep_amp.py", exp_file("H1", sweep, mode="sweep", sweep=["amp"]))))
    lab.write("tasks.md", HEAD + "- [x] E1 / H1: amp at gain 1\n" + END)
    ok(session.verdict("E1", "supported", "distance rose with amp"))
    lab.write("tasks.md", HEAD + "- [x] E1 / H1: amp at gain 1\n- [ ] E2 / H2: amp 1 at gain 3\n" + END)
    lab.add(
        hyp_block(
            "H2",
            "WHEN amp is 1 and gain is 3, THE distance SHALL stay below 2.5.",
            {"id": "P1", "range": [2.0, 2.5], "label": "outside", "when": {"amp": 1.0, "gain": 3.0}},
        )
    )
    ok(session.register("H2"))
    ok(session.run(lab.experiment("e2_best.py", exp_file("H2", [[1.0, 3.0]], phase="best"))))
    lab.write("tasks.md", HEAD + "- [x] E1 / H1: amp at gain 1\n- [x] E2 / H2: amp 1 at gain 3\n" + END)
    ok(session.verdict("E2", "rejected", "it went further than predicted"))
    lab.write("design.md", DESIGN_START + END_TABLE)
    lab.write(
        "tasks.md",
        HEAD + "- [x] E1 / H1: amp at gain 1\n- [x] E2 / H2: amp 1 at gain 3\n"
        "\n## End\n\n- [x] Fill the Discovered spec table and end the session\n",
    )
    ok(session.end())
    (full,) = records.load(root / "lab" / "sessions", allow_fake=True)
    (app,) = choices.load_apps([write_app(root / "app")], [full]).apps
    return session, full, app, layouts.parse(LAYOUTS, "test fixture")


def _page(made, upto):
    session, full, app, table = made
    cut = records.from_entries(session.sealed_path, full.name, list(full.entries[:upto]), allow_fake=True)
    segments, _ = shelf.at_bench_page(cut, app, table, {})
    return "".join(s.text for s in segments)


def _task_of(page, hypothesis):
    """The task line text above the card of `hypothesis`, and whether its box is ticked."""
    at = page.index(f'id="{hypothesis}"')
    start = page.rindex('<li class="task', 0, at)
    head = page[start : page.index("</p>", start)]
    return head, 'class="task task-done"' in head


def test_after_each_verdict_the_task_of_that_experiment_is_ticked_at_the_bench(made):
    _, full, _, _ = made
    verdicts = [x.seq for x in full.snapshots if x.for_ == "verdict"]
    for n, upto in enumerate(verdicts, start=1):
        page = _page(made, upto)
        head, ticked = _task_of(page, f"H{n}")
        assert f"E{n} / H{n}" in head and ticked, f"after the verdict on E{n}"
        assert "Not in the task list yet" not in page
        assert "box was left empty" not in page


def test_a_hypothesis_registered_before_the_next_copy_is_not_in_the_task_list_yet(made):
    _, full, _, _ = made
    registered = [e["seq"] for e in full.entries if e["kind"] == "register"][1]
    page = _page(made, registered)
    assert "Not in the task list yet" in page
    assert page.index("Not in the task list yet") < page.index('id="H2"')
    runs = [x.seq for x in full.snapshots if x.for_ == "experiment"]
    page = _page(made, runs[1])
    head, ticked = _task_of(page, "H2")
    assert "E2 / H2" in head and not ticked
    assert "Not in the task list yet" not in page and "box was left empty" not in page
