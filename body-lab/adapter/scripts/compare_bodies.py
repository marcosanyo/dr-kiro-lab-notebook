"""Builder side only, not part of the product (body-lab task 8): three probes, run on both bodies.

Probes: every channel at 0; the wheel's channel at +1; the wheel's channel at -1. The wheel's
channel is read from the wiring, so the script never names a channel number itself. Prints x, y
and heading (m, m, degrees) per body.
Run: uv run python scripts/compare_bodies.py
"""

import json

from body_lab.adapter import BodyAdapter
from body_lab.settings import WIRING_FILE


def main() -> None:
    wiring = json.loads(WIRING_FILE.read_text(encoding="utf-8"))
    wheel = next(c["channel"] for c in wiring["channels"] if c["actuator"] == "wheel")
    probes = {
        "all channels 0": {},
        "wheel channel at +1": {wheel: 1.0},
        "wheel channel at -1": {wheel: -1.0},
    }
    for name, drive in probes.items():
        for label in ("a", "b"):
            adapter = BodyAdapter(variant=label)
            inputs = {
                knob.name: tuple(drive.get(i, 0.0) for _ in adapter.sample_times)
                for i, knob in enumerate(adapter.declaration().knobs)
            }
            measured = adapter.run_trial(inputs, seed=0).values
            cells = "  ".join(f"{key}={measured[key]}" for key in ("x", "y", "heading"))
            print(f"{name:20} body {label}: {cells}")


if __name__ == "__main__":
    main()
