"""The session config file, found through the lab's session file (design F7, D2, D8).

A TOML file the builder writes outside the lab. It has one field for each field of `SessionConfig`, plus
`resume`. There are no defaults: a missing or extra field stops the server with a message (1.3, rules.md 2).
Folder and file paths are resolved against the folder of the config file. `spec_files` and `experiments_dir`
stay relative to the lab, as in `SessionConfig`.
"""

import importlib
import inspect
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

from bench.core.session import SessionConfig
from bench.frontend import pointer

FIELDS = tuple(f.name for f in fields(SessionConfig) if f.name != "variant") + ("resume",)
OPTIONAL = ("variant",)  # optional: lab-bench 23.1
_PATH_FIELDS = ("lab_dir", "state_dir", "sessions_dir", "stop_list")
# The messages name the config without its path: they reach stderr, which the reader's Kiro log may show.
WHERE = "session config"


class ConfigError(Exception):
    """The session config cannot be used. The message says what and where."""


@dataclass(frozen=True)
class ServerConfig:
    session: SessionConfig
    resume: bool


def _variant(data: dict, where: str) -> str | None:
    if "variant" not in data:
        return None
    value = data["variant"]
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{where}: variant must be a non-empty string")
    return value


def _adapter(spec: object, where: str, variant: str | None) -> object:
    if not isinstance(spec, str) or spec.count(":") != 1:
        raise ConfigError(f"{where}: adapter must be 'module:factory'")
    module_name, attribute = spec.split(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as error:
        raise ConfigError(f"{where}: cannot import adapter module {module_name} ({error})") from error
    factory = getattr(module, attribute, None)
    if not callable(factory):
        raise ConfigError(f"{where}: {spec} is not callable")
    if variant is None:
        return factory()
    if "variant" not in inspect.signature(factory).parameters:
        raise ConfigError(f"{where}: {spec} takes no variant; remove the variant setting")
    try:
        return factory(variant=variant)
    except ValueError as error:
        raise ConfigError(f"{where}: {error}") from error


def load(path: Path) -> ServerConfig:
    path = Path(path)
    where = WHERE
    if not path.is_file():
        raise ConfigError(f"{where}: file not found")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"{where}: not valid TOML ({error})") from error
    missing = [name for name in FIELDS if name not in data]
    if missing:
        raise ConfigError(f"{where}: missing field(s) {', '.join(missing)}")
    extra = sorted(set(data) - set(FIELDS) - set(OPTIONAL))
    if extra:
        raise ConfigError(f"{where}: unknown field(s) {', '.join(extra)}")
    if not isinstance(data["resume"], bool):
        raise ConfigError(f"{where}: resume must be true or false")
    base = path.parent
    for name in _PATH_FIELDS:
        if not isinstance(data[name], str) or not data[name]:
            raise ConfigError(f"{where}: {name} must be a path")
    spec_files = data["spec_files"]
    if not (
        isinstance(spec_files, list) and len(spec_files) == 3 and all(isinstance(s, str) for s in spec_files)
    ):
        raise ConfigError(f"{where}: spec_files must list requirements.md, design.md and tasks.md")
    sources = data["scan_sources"]
    if not (isinstance(sources, list) and sources and all(isinstance(s, str) and s for s in sources)):
        raise ConfigError(f"{where}: scan_sources must be a non-empty list of paths")
    for name in ("session_id", "application", "experiments_dir", "discovered_table"):
        if not isinstance(data[name], str):
            raise ConfigError(f"{where}: {name} must be a string")
    if isinstance(data["seed"], bool) or not isinstance(data["seed"], int):
        raise ConfigError(f"{where}: seed must be an integer")
    variant = _variant(data, where)
    session = SessionConfig(
        session_id=data["session_id"],
        application=data["application"],
        adapter=_adapter(data["adapter"], where, variant),  # type: ignore[arg-type]
        lab_dir=base / data["lab_dir"],
        spec_files=tuple(spec_files),  # type: ignore[arg-type]
        experiments_dir=data["experiments_dir"],
        state_dir=base / data["state_dir"],
        sessions_dir=base / data["sessions_dir"],
        seed=data["seed"],
        scan_sources=tuple(base / s for s in sources),
        stop_list=base / data["stop_list"],
        discovered_table=data["discovered_table"],
        variant=variant,
    )
    return ServerConfig(session, data["resume"])


def config_path_for(lab: Path) -> Path:
    """The session config named by the session file of `lab` (`pointer`)."""
    try:
        return pointer.read(lab)["session_config"]
    except pointer.PointerError as error:
        raise ConfigError(str(error)) from error


def for_lab(lab: Path) -> ServerConfig:
    """The config of the session that runs in `lab`. Its `lab_dir` must be `lab` itself."""
    loaded = load(config_path_for(lab))
    if loaded.session.lab_dir.resolve() != Path(lab).resolve():
        raise ConfigError(
            f"{WHERE}: lab_dir names another folder; start bench-mcp in the session's lab folder"
        )
    return loaded
