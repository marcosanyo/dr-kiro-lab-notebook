"""Application settings and choice file text for the fake session of `fixtures.session` (labelled fake;
none of it is a result)."""

from pathlib import Path

CHOICE = """title = "A Fake Notebook"
subtitle = "words written for a test fixture"
summary = "A fixture summary. It states nothing about a real session."
line = "A fixture line."
model = "a fixture model"
date = "2026-01-01"
color = "violet"

[progress]
measurement = "distance"
better = "higher"

[[polaroid]]
heading = "The miss"
trial = "T7"
words = "A fixture line for the photo."

[[polaroid]]
heading = "Best"
trial = "T1"
words = "Another fixture line."
star = true

[[note]]
kind = "best"

[[note]]
kind = "hits"

[[note]]
kind = "trials"
"""
APP = """application = "fake"
order = 1
case = "CASE 1 · THE FAKE LAB"
door = "The Fake Lab"
door_line = "A fixture door."
about = "A fixture description of the fake lab."
open = "s1"
unit = "runs"
unit_one = "run"
theme = "day"
pen = "blue"
decoration = "none"
"""


def write_app(folder: Path) -> Path:
    """The notebook folder of the fake application: `app.toml` and `choices/s1.toml`."""
    (folder / "choices").mkdir(parents=True)
    (folder / "app.toml").write_text(APP)
    (folder / "choices" / "s1.toml").write_text(CHOICE)
    return folder
