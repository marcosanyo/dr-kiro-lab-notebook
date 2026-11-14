"""Print the tables of spikes/timing/extreme-v2-summary.md from the progress files (no numbers typed by hand).
usage: python3 spikes/timing/summarize_v2.py > /tmp/tables.md
"""

import json
from pathlib import Path

RUN = Path(__file__).resolve().parents[2] / "bench-run" / "wind-tunnel"
new = [
    json.loads(x)
    for x in (RUN / "extreme-progress-v2.jsonl").read_text().splitlines()
    if x.strip()
]
old = {
    i: json.loads(x)
    for i, x in enumerate((RUN / "extreme-progress.jsonl").read_text().splitlines())
    if x.strip()
}
old_by_knobs = {tuple(r["knobs"].values()): (i, r) for i, r in old.items()}


def g(x, f):
    return "-" if x is None else format(x, f)


def row(r, with_old=False):
    k = r["knobs"]
    geo, log = r["geometry"], r.get("log") or {}
    cells = [
        r["label"],
        f"{k['aspect']:g}/{k['corner']:g}/{k['splitter']:g}/{k['angle']:g}",
        r["outcome"],
        f"{r['wall_clock_s']:.1f}",
        g(log.get("sim_time_reached"), "g"),
        g(log.get("min_delta_t"), ".3g"),
        g(log.get("last_delta_t"), ".3g"),
        g(geo["arc_length_each"], ".5f"),
        f"{geo['shortest_piece']:.5f}",
    ]
    if with_old:
        hit = old_by_knobs.get(tuple(k.values()))
        cells.append(
            f"#{hit[0] + 1} {hit[1]['outcome']} {hit[1]['wall_clock_s']:.0f} s"
            if hit
            else "-"
        )
    cells.append(r.get("cause", "").replace("|", "/"))
    return "| " + " | ".join(cells) + " |"


head = "| label | aspect/corner/splitter/angle | outcome | wall-clock run_trial (s) | simulated time reached | smallest time step | last time step | corner arc length | shortest piece |"
sep = "|---|---|---|---|---|---|---|---|---|"
for title, prefix in (
    ("Part A", "A"),
    ("Part B1 (angle)", "B1"),
    ("Part B2 (corner)", "B2"),
):
    print(f"### {title}\n")
    extra = " old survey |" if prefix == "A" else ""
    print(head + extra + " cause |")
    print(sep + ("---|" if prefix == "A" else "") + "---|")
    for r in new:
        if (
            (r["label"][0] == "A")
            if prefix == "A"
            else (r["label"].split()[0] == prefix)
        ):
            print(row(r, prefix == "A"))
    print()
