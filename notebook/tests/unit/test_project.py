"""The project: the lock holds no MCP SDK, and the package imports with both adapters (Req. 1.5, 21.3)."""

import importlib
import tomllib
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]


def test_lock_file_holds_no_mcp():
    lock = tomllib.loads((PROJECT / "uv.lock").read_text(encoding="utf-8"))
    names = {package["name"] for package in lock["package"]}
    assert "mcp" not in names
    assert {"lab-notebook", "lab-bench", "body-lab-adapter", "wind-tunnel-adapter"} <= names


def test_notebook_imports_with_the_adapters_importable():
    notebook = importlib.import_module("notebook")
    assert notebook.__name__ == "notebook"
    # The bench scan imports these to read each application's allow list (design N23).
    importlib.import_module("body_lab.adapter")
    importlib.import_module("wind_tunnel.declaration")
    importlib.import_module("mujoco")
    importlib.import_module("wind_tunnel_model")
