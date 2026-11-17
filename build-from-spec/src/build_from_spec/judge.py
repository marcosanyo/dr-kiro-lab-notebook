"""Result program (design 3.8, Requirement 15).

Only `counted_trials` is here so far: the request check (design 3.2) reads the
counted trials of a source record. The rest of the result program comes with its task.
"""

from typing import Any


def counted_trials(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The bodies of the trial entries of experiments with an `"for": "experiment"` snapshot, in log order.

    `Session._run_trials` writes that snapshot only when the run call returns Ran. A trial recorded before a
    bench failure has no snapshot and does not count (Requirement 15.9).
    """
    snapshotted = {
        e["body"]["experiment"]
        for e in entries
        if e["kind"] == "snapshot" and e["body"].get("for") == "experiment"
    }
    return [e["body"] for e in entries if e["kind"] == "trial" and e["body"]["experiment"] in snapshotted]
