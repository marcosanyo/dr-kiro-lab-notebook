"""Reference values of two real runs, for the output-reduction check (task 14.4 (c), user decision 2).

usage: reference.py LABEL        (LABEL is `before` or `after`; writes reference-LABEL.json next to this file)
       reference.py compare      (compares reference-before.json with reference-after.json; exit 1 on a difference)

Each input is run once with the real mesher and the real runner (seed 0). Before the case folder of the settled run is
removed, the SHA-256 of its force file and a size listing are recorded. The adapter code is not changed by this
script. Case folders are made under bench-run/wind-tunnel-ref so that the folders of earlier runs are not touched.
Reproducibility holds only on the same machine and image build (requirement 10.3); the image digest is recorded.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CASE_BASE = REPO / "bench-run" / "wind-tunnel-ref"
SEED = 0
INPUTS = {
    "circle_re150": {"aspect": 1.0, "corner": 1.0, "splitter": 0.0, "angle": 0.0},
    "plate_1.5_0.5_1.0_10": {"aspect": 1.5, "corner": 0.5, "splitter": 1.0, "angle": 10.0},
}

from bench.adapter import TrialResult  # noqa: E402
from wind_tunnel import adapter as am  # noqa: E402
from wind_tunnel import environment  # noqa: E402


def du(path: Path) -> int:
    return int(subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True, check=True).stdout.split()[0]) * 1024


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def listing(root: Path) -> dict:
    """Size of every folder down to depth 3 below the case folder, and the number of files in it."""
    out = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.is_dir() and not path.is_symlink() and len(rel.parts) <= 3:
            out[str(rel)] = {"bytes": du(path), "files": sum(1 for p in path.rglob("*") if p.is_file())}
    return out


def run_one(name: str, knobs: dict) -> dict:
    adapter = am.WindAdapter(case_base=CASE_BASE)
    seen: dict = {}
    real_remove = am.move_to_trash

    def remove(path):
        path = Path(path)
        seen["case_bytes"] = du(path)
        seen["listing"] = listing(path)
        forces = sorted(path.glob("postProcessing/forces/*/force.dat"))
        assert len(forces) == 1, forces
        seen["force_file_sha256"] = sha(forces[0].read_bytes())
        seen["force_file_bytes"] = forces[0].stat().st_size
        seen["force_file"] = str(forces[0].relative_to(path))
        t0 = time.monotonic()
        real_remove(path)
        seen["remove_s"] = time.monotonic() - t0

    am.move_to_trash = remove
    t0 = time.monotonic()
    result = adapter.run_trial(dict(knobs), SEED)
    seen["run_trial_s"] = time.monotonic() - t0
    am.move_to_trash = real_remove
    if not isinstance(result, TrialResult):
        raise SystemExit(f"{name}: not a result: {result.public_reason}\n{result.detail}")
    values = {k: (v if isinstance(v, float) else repr(v)) for k, v in result.values.items()}
    return {
        "knobs": knobs,
        "seed": SEED,
        "values": values,
        "values_repr": {k: repr(v) for k, v in values.items()},
        "picture_kind": result.picture.kind,
        "picture_sha256": sha(result.picture.data),
        "picture_bytes": len(result.picture.data),
        **seen,
    }


def compare() -> None:
    before = json.loads((HERE / "reference-before.json").read_text())
    after = json.loads((HERE / "reference-after.json").read_text())
    bad = []
    for name in INPUTS:
        for key in ("knobs", "seed", "values_repr", "picture_kind", "picture_sha256", "picture_bytes",
                    "force_file", "force_file_sha256", "force_file_bytes"):
            b, a = before["runs"][name][key], after["runs"][name][key]
            same = b == a
            print(f"{name:24} {key:20} {'identical' if same else 'DIFFERENT'}")
            if not same:
                bad.append((name, key, b, a))
    if before["image_digest"] != after["image_digest"]:
        bad.append(("image", "digest", before["image_digest"], after["image_digest"]))
    for item in bad:
        print("DIFFERENCE:", *item)
    raise SystemExit(1 if bad else 0)


def main() -> None:
    label = sys.argv[1]
    if label == "compare":
        compare()
    CASE_BASE.mkdir(parents=True, exist_ok=True)
    runs = {name: run_one(name, knobs) for name, knobs in INPUTS.items()}
    doc = {"label": label, "image_digest": environment.load_lock().digest, "runs": runs}
    (HERE / f"reference-{label}.json").write_text(json.dumps(doc, indent=2) + "\n")
    for name, run in runs.items():
        print(name, run["values_repr"], run["picture_sha256"], run["force_file_sha256"], run["case_bytes"])


if __name__ == "__main__":
    main()
