"""The `bench-lab-hooks` command (design F2, F8, F9): install the two lab hooks into a lab.

    bench-lab-hooks <lab folder>

Copies `confine.py` and `calllog.py` into `<lab>/.kiro/hooks/` and writes the three hook files. The scripts
are copied, not referenced, because nothing in a lab may point at a path outside it (rules.md, Blind).
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

SOURCES = Path(__file__).resolve().parent / "hooks"
SCRIPTS = ("confine.py", "calllog.py")
RUN = "uv run --no-project python .kiro/hooks/"
HOOK_FILES = {
    "confine-pre-tool.json": ("Refuse calls outside the lab", "PreToolUse", "confine.py"),
    "calllog-pre-tool.json": ("Log every call before it runs", "PreToolUse", "calllog.py pre"),
    "calllog-post-tool.json": ("Log every call after it runs", "PostToolUse", "calllog.py post"),
}


def install(lab: Path) -> list[Path]:
    lab = Path(lab)
    if not lab.is_dir():
        raise FileNotFoundError(f"{lab} is not a folder")
    hooks = lab / ".kiro" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    written = []
    for script in SCRIPTS:
        shutil.copyfile(SOURCES / script, hooks / script)
        written.append(hooks / script)
    for file_name, (name, trigger, command) in HOOK_FILES.items():
        body = {
            "version": "v1",
            "hooks": [
                {"name": name, "trigger": trigger, "action": {"type": "command", "command": RUN + command}}
            ],
        }
        (hooks / file_name).write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
        written.append(hooks / file_name)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bench-lab-hooks", description="Install the lab hooks into a lab.")
    parser.add_argument("lab", type=Path)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        for path in install(args.lab):
            print(path)
    except OSError as error:
        print(f"bench-lab-hooks: {error}", file=sys.stderr)
        return 2
    return 0
