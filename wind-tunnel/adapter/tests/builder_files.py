"""The files the builder puts in the lab, as opposed to the files Dr. Kiro writes there.

Dr. Kiro's files are defined once, by `[lab] dr_kiro` in `scan_sources.toml` (the definition the blind scan
uses), plus `pictures/**`, which the bench writes into the lab and the lab's own `.gitignore` lists."""
from __future__ import annotations

import tomllib
from pathlib import Path

from bench.scan.terms import glob_regex

ADAPTER = Path(__file__).resolve().parents[1]
EXTRA_DR_KIRO_GLOBS = ("pictures/**",)
def dr_kiro_globs() -> tuple[str, ...]:
    data = tomllib.loads((ADAPTER / "scan_sources.toml").read_text(encoding="utf-8"))
    return tuple(data["lab"]["dr_kiro"]) + EXTRA_DR_KIRO_GLOBS
def builder_files(lab: Path) -> list[Path]:
    """Every file in `lab` that is not one of Dr. Kiro's files."""
    patterns = [glob_regex(glob) for glob in dr_kiro_globs()]
    return sorted(
        path
        for path in lab.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and not any(p.fullmatch(path.relative_to(lab).as_posix()) for p in patterns)
    )
