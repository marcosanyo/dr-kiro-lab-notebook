"""The `bench-make-lab` command (dr-kiro Requirements 1, 5.1, 5.4, design 7.1).

    bench-make-lab <lab folder>

Writes the builder files into a lab: the agent file and prompt into `.kiro/agents/`, the two steering
files into `.kiro/steering/`, and the two hooks (the `bench-lab-hooks` installer). Creates `experiments/`
and writes the lab's `.gitignore`. It overwrites builder files only and never touches Dr. Kiro's files.
"""

import argparse
import sys
from importlib import resources
from pathlib import Path

from bench.frontend.labhooks import install as install_hooks

FILES = resources.files("bench.drkiro") / "files"
BUILDER_FILES = {
    "dr-kiro.json": ".kiro/agents/dr-kiro.json",
    "dr-kiro-prompt.md": ".kiro/agents/dr-kiro-prompt.md",
    "method.md": ".kiro/steering/method.md",
    "workflow.md": ".kiro/steering/workflow.md",
}
TEMPLATES = {
    "requirements.md": ".kiro/specs/lab/requirements.md",
    "design.md": ".kiro/specs/lab/design.md",
    "tasks.md": ".kiro/specs/lab/tasks.md",
}
GITIGNORE = "experiments/\npictures/\n"


def make_lab(lab: Path) -> list[Path]:
    lab = Path(lab)
    if not lab.is_dir():
        raise FileNotFoundError(f"{lab} is not a folder")
    written = []
    for source, target in BUILDER_FILES.items():
        path = lab / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((FILES / source).read_bytes())
        written.append(path)
    written += install_hooks(lab)
    (lab / "experiments").mkdir(exist_ok=True)
    (lab / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    written.append(lab / ".gitignore")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bench-make-lab", description="Install Dr. Kiro's builder files in a lab."
    )
    parser.add_argument("lab", type=Path)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        for path in make_lab(args.lab):
            print(path)
    except OSError as error:
        print(f"bench-make-lab: {error}", file=sys.stderr)
        return 2
    return 0
