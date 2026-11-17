"""The session config file named by BENCH_SESSION_CONFIG (design F7, D8).

A TOML file the builder writes outside the lab. It has one field for each field of `SessionConfig`, plus
`resume`. There are no defaults: a missing or extra field stops the server with a message (1.3, rules.md 2).
Folder and file paths are resolved against the folder of the config file. `spec_files` and `experiments_dir`
stay relative to the lab, as in `SessionConfig`.
"""

import importlib
import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

from bench.core.session import SessionConfig

ENV_VAR = "BENCH_SESSION_CONFIG"
FIELDS = tuple(f.name for f in fields(SessionConfig)) + ("resume",)
_PATH_FIELDS = ("lab_dir", "state_dir", "sessions_dir", "stop_list")


class ConfigError(Exception):
    """The session config cannot be used. The message says what and where."""


@dataclass(frozen=True)
class ServerConfig:
    session: SessionConfig
    resume: bool


def _adapter(spec: object, where: str) -> object:
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
    return factory()


def load(path: Path) -> ServerConfig:
    path = Path(path)
    where = str(path)
    if not path.is_file():
        raise ConfigError(f"{where}: session config file not found")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"{where}: not valid TOML ({error})") from error
    missing = [name for name in FIELDS if name not in data]
    if missing:
        raise ConfigError(f"{where}: missing field(s) {', '.join(missing)}")
    extra = sorted(set(data) - set(FIELDS))
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
    session = SessionConfig(
        session_id=data["session_id"],
        application=data["application"],
        adapter=_adapter(data["adapter"], where),  # type: ignore[arg-type]
        lab_dir=base / data["lab_dir"],
        spec_files=tuple(spec_files),  # type: ignore[arg-type]
        experiments_dir=data["experiments_dir"],
        state_dir=base / data["state_dir"],
        sessions_dir=base / data["sessions_dir"],
        seed=data["seed"],
        scan_sources=tuple(base / s for s in sources),
        stop_list=base / data["stop_list"],
        discovered_table=data["discovered_table"],
    )
    return ServerConfig(session, data["resume"])


def from_environment() -> ServerConfig:
    value = os.environ.get(ENV_VAR)
    if not value:
        raise ConfigError(f"{ENV_VAR} is not set; it names the session config file")
    return load(Path(value))
