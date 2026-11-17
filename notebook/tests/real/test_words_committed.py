"""The committed commentary word list (task 6.4) loads through `words.py`. Its content is the list the user
approved; the words asserted here are a copy of that approved list (55 words), so an edit fails."""

from pathlib import Path

from notebook import words

ROOT = Path(__file__).resolve().parents[3]
LIST = ROOT / "notebook" / "commentary-words.txt"

APPROVED = (
    "limp",
    "hobble",
    "hobbled",
    "hobbling",
    "lame",
    "cripple",
    "crippled",
    "crippling",
    "paralyze",
    "paralyzed",
    "paralyzing",
    "paralyse",
    "paralysed",
    "paralysing",
    "paralysis",
    "paralytic",
    "injure",
    "injured",
    "injuring",
    "injury",
    "injuries",
    "wound",
    "hurt",
    "pain",
    "painful",
    "stumble",
    "stumbled",
    "stumbling",
    "spasm",
    "spastic",
    "convulse",
    "convulsed",
    "convulsing",
    "convulsion",
    "seizure",
    "sprain",
    "fracture",
    "fractured",
    "maim",
    "handicap",
    "handicapped",
    "disabled",
    "disability",
    "disabilities",
    "impaired",
    "impairment",
    "amputee",
    "amputate",
    "amputated",
    "crutch",
    "wheelchair",
    "palsy",
    "gimp",
    "deformed",
    "deformity",
)


def test_the_committed_list_is_the_approved_list() -> None:
    loaded = words.load(LIST)
    assert len(APPROVED) == len(set(APPROVED))
    assert set(loaded.words) == set(APPROVED)
    assert len(loaded.words) == len(APPROVED) == 55


def test_the_committed_list_refuses_its_words_and_suffix_forms() -> None:
    loaded = words.load(LIST)
    assert loaded.matches("The body limps, then limped.") == [("limps", "limp"), ("limped", "limp")]
    assert loaded.matches("It moved forward 2 units and turned left.") == []
