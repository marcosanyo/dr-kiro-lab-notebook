"""Term sources of an application and the extractors that read them (design 11.1).

Each application names its model and solver files in a `scan_sources.toml` outside its `lab/` folder:

    adapter = "package.module:factory"      # called with no arguments; its declaration is the allow list
    solver_dirs = ["case"]                  # optional: folder names that a path must not contain

    [lab]                                   # optional: the application's lab folder
    path = "../lab"
    dr_kiro = ["experiments/**", ".kiro/specs/*/requirements.md"]   # globs of files Dr. Kiro writes

    [[source]]
    path = "../model/thing.xml"
    extractor = "mjcf"                      # mjcf | wiring-json | fake-json

Paths are relative to the `scan_sources.toml` file. Nothing here holds a copy of a term.
"""

import importlib
import json
import re
import tomllib
import xml.etree.ElementTree as ElementTree
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from bench.adapter import Declaration
from bench.scan.foam_terms import (
    extract_openfoam_dict,
    extract_python_names,
    extract_shell_words,
    extract_toml_names,
)


class ScanError(Exception):
    """The scan cannot run as specified. It never assumes a level or skips a file (15.7)."""


# rules.md, Blind scan: the attributes whose values are names.
MJCF_NAME_ATTRIBUTES = ("name", "class", "joint", "material", "texture", "model")


def extract_mjcf(path: Path) -> list[str]:
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as error:
        raise ScanError(f"{path}: cannot read as MJCF ({error})") from error
    names = []
    for element in root.iter():
        for attribute in MJCF_NAME_ATTRIBUTES:
            value = element.get(attribute)
            if value:
                names.append(value)
    return names


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ScanError(f"{path}: cannot read as JSON ({error})") from error


def extract_wiring_json(path: Path) -> list[str]:
    data = _load_json(path)
    channels = data.get("channels") if isinstance(data, dict) else None
    if not isinstance(channels, list):
        raise ScanError(f"{path}: wiring has no channels list")
    names = []
    for channel in channels:
        actuator = channel.get("actuator") if isinstance(channel, dict) else None
        if not isinstance(actuator, str) or not actuator:
            raise ScanError(f"{path}: a wiring channel has no actuator name")
        names.append(actuator)
    return names


def extract_fake_json(path: Path) -> list[str]:
    data = _load_json(path)
    names = data.get("names") if isinstance(data, dict) else None
    if not isinstance(names, list) or not all(isinstance(n, str) and n for n in names):
        raise ScanError(f"{path}: the fake application file needs a list of names")
    return list(names)


EXTRACTORS: dict[str, Callable[[Path], list[str]]] = {
    "mjcf": extract_mjcf,
    "wiring-json": extract_wiring_json,
    "fake-json": extract_fake_json,
    "openfoam-dict": extract_openfoam_dict,
    "shell-words": extract_shell_words,
    "toml-names": extract_toml_names,
    "python-names": extract_python_names,
}


def glob_regex(pattern: str) -> re.Pattern[str]:
    """A glob over `/`-separated relative paths: `**` matches across folders, `*` and `?` within one."""
    out = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile(out)


@dataclass(frozen=True)
class LabLayout:
    root: Path
    dr_kiro: tuple[str, ...]

    def level(self, path: Path) -> str | None:
        """The level of a file inside this lab folder, or None if the file is not inside it."""
        try:
            relative = path.resolve().relative_to(self.root.resolve())
        except ValueError:
            return None
        posix = relative.as_posix()
        for pattern in self.dr_kiro:
            if glob_regex(pattern).fullmatch(posix):
                return "dr-kiro"
        return "builder"


@dataclass(frozen=True)
class AppSources:
    """Everything the scan needs from one application."""

    names: tuple[str, ...]  # derived terms, before the allow list and stop list
    file_names: tuple[str, ...]  # source file names
    solver_dirs: tuple[str, ...]
    allow: tuple[str, ...]  # the declaration's knob, measurement and not-measured outcome names
    lab: LabLayout | None


def allow_list(decl: Declaration) -> tuple[str, ...]:
    names = [k.name for k in decl.knobs] + [m.name for m in decl.measurements]
    names += [outcome for m in decl.measurements for outcome in m.not_measured]
    return tuple(names)


def _load_declaration(spec: object, where: Path) -> Declaration:
    if not isinstance(spec, str) or ":" not in spec:
        raise ScanError(f"{where}: adapter must be 'module:factory'")
    module_name, _, attribute = spec.partition(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        raise ScanError(f"{where}: cannot import adapter module {module_name} ({error})") from error
    factory = getattr(module, attribute, None)
    if not callable(factory):
        raise ScanError(f"{where}: {spec} is not callable")
    decl = factory().declaration()
    if not isinstance(decl, Declaration):
        raise ScanError(f"{where}: {spec} did not give a Declaration")
    return decl


def load_app(config: Path) -> AppSources:
    config = Path(config)
    if not config.is_file():
        raise ScanError(f"{config}: scan sources file not found")
    try:
        data = tomllib.loads(config.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ScanError(f"{config}: not valid TOML ({error})") from error
    unknown = set(data) - {"adapter", "solver_dirs", "lab", "source"}
    if unknown:
        raise ScanError(f"{config}: unknown keys {sorted(unknown)}")
    base = config.parent
    sources = data.get("source")
    if not isinstance(sources, list) or not sources:
        raise ScanError(f"{config}: needs at least one [[source]]")
    names: list[str] = []
    file_names: list[str] = []
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"path", "extractor"}:
            raise ScanError(f"{config}: each [[source]] needs exactly path and extractor")
        extractor = EXTRACTORS.get(source["extractor"])
        if extractor is None:
            raise ScanError(f"{config}: unknown extractor {source['extractor']!r}")
        path = base / source["path"]
        if not path.is_file():
            raise ScanError(f"{config}: source file {path} not found")
        names += extractor(path)
        file_names.append(path.name)
    solver_dirs = data.get("solver_dirs", [])
    if not isinstance(solver_dirs, list) or not all(isinstance(d, str) and d for d in solver_dirs):
        raise ScanError(f"{config}: solver_dirs must be a list of folder names")
    lab = None
    if "lab" in data:
        section = data["lab"]
        if not isinstance(section, dict) or set(section) != {"path", "dr_kiro"}:
            raise ScanError(f"{config}: [lab] needs exactly path and dr_kiro")
        root = base / section["path"]
        if not root.is_dir():
            raise ScanError(f"{config}: lab folder {root} not found")
        globs = section["dr_kiro"]
        if not isinstance(globs, list) or not all(isinstance(g, str) and g for g in globs):
            raise ScanError(f"{config}: dr_kiro must be a list of globs")
        lab = LabLayout(root, tuple(globs))
    decl = _load_declaration(data.get("adapter"), config)
    return AppSources(tuple(names), tuple(file_names), tuple(solver_dirs), allow_list(decl), lab)


def load_stop_list(path: Path) -> tuple[str, ...]:
    path = Path(path)
    if not path.is_file():
        raise ScanError(f"{path}: stop list not found")
    words = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if not line.replace("_", "").isalnum() or line != line.lower() or " " in line:
            raise ScanError(f"{path} line {number}: a stop list entry is one lowercase word")
        words.append(line)
    return tuple(words)
