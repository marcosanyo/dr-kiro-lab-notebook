"""Requirement 1.2: the core imports no front end, transport, agent framework or hook,
and the bench has no runtime dependency outside the standard library (design section 1)."""

import json
import subprocess
import sys

CORE_PACKAGES = [
    "bench",
    "bench.core",
    "bench.lang",
    "bench.specfiles",
    "bench.record",
    "bench.scan",
    "bench.fake",
]

BANNED_PREFIXES = (
    "mcp",
    "fastmcp",
    "asyncio",
    "socket",
    "socketserver",
    "http",
    "urllib",
    "xmlrpc",
    "subprocess",
)


def _modules_after_import() -> tuple[set[str], set[str]]:
    """Import every core package in a fresh interpreter. Return (all modules, modules before)."""
    script = (
        "import sys, json\n"
        "before = set(sys.modules)\n"
        f"for name in {CORE_PACKAGES!r}:\n"
        "    __import__(name)\n"
        "print(json.dumps([sorted(before), sorted(sys.modules)]))\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script], capture_output=True, text=True, check=True
    )
    before, after = json.loads(result.stdout)
    return set(after), set(before)


def test_core_imports_no_front_end_or_transport() -> None:
    after, before = _modules_after_import()
    loaded = after - before
    banned = sorted(m for m in loaded if m.split(".")[0] in BANNED_PREFIXES)
    assert banned == [], f"core imported {banned}"


def test_core_has_no_runtime_dependency_outside_stdlib() -> None:
    after, before = _modules_after_import()
    tops = {m.split(".")[0] for m in after - before}
    outside = sorted(t for t in tops if t != "bench" and t not in sys.stdlib_module_names)
    assert outside == [], f"core imported non-standard modules {outside}"
