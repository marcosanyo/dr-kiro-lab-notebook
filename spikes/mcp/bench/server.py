# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["mcp==2.3.0", "pillow==13.0.0"]
# ///
"""Toy lab bench: an MCP server (stdio) for the MCP spike. See ../brief.md, step 1.

Settings (environment variables):
  BENCH_DELAY_S   seconds run_experiment sleeps before answering (default 2)
  BENCH_BUDGET    number of experiments allowed (default 5)
  BENCH_PICTURE   "inline" (default): the PNG is returned as image content, preceded by a line naming the
                  experiment. "file": the PNG is written to lab/pictures/<experiment name>.png and its
                  path (relative to the lab) is returned in the JSON as "picture".
  BENCH_LAB       the agent's folder (default ../lab next to this file)
  BENCH_LEDGER    ledger file (default ledger.jsonl next to this file)
"""

import base64
import hashlib
import io
import json
import os
import re
import time
from pathlib import Path

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import CallToolResult, ImageContent, TextContent
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
DELAY_S = float(os.environ.get("BENCH_DELAY_S", "2"))
BUDGET = int(os.environ.get("BENCH_BUDGET", "5"))
PICTURE = os.environ.get("BENCH_PICTURE", "inline")
if PICTURE not in ("inline", "file"):
    raise SystemExit(f"BENCH_PICTURE must be 'inline' or 'file', got {PICTURE!r}")
LAB = Path(os.environ.get("BENCH_LAB", HERE.parent / "lab")).resolve()
LEDGER = Path(os.environ.get("BENCH_LEDGER", HERE / "ledger.jsonl")).resolve()
EXPERIMENTS = LAB / "experiments"
HEADER = re.compile(r"^# (H\d+): \S")

mcp = MCPServer("bench")
_lock = anyio.Lock()
_running: set[str] = set()  # experiments accepted but not yet in the ledger


def _ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]


def _resolve(path: str, must_exist: bool = True) -> tuple[Path, str]:
    """Return the absolute file and its path relative to the lab, or refuse."""
    file = (LAB / path).resolve()
    if not file.is_relative_to(EXPERIMENTS):
        raise ToolError(f"Refused: {path!r} is not under experiments/. Pass a path like 'experiments/<name>'.")
    rel = file.relative_to(LAB).as_posix()
    if must_exist and not file.is_file():
        raise ToolError(f"Refused: {rel} does not exist. Write the file first, then call run_experiment.")
    return file, rel


def _result(entry: dict, budget_remaining: int | None = None) -> CallToolResult:
    data = {"value": entry["value"]}
    if budget_remaining is not None:
        data["budget_remaining"] = budget_remaining
    # The PNG shows a second number derived from the hash. It is not in the JSON (brief, Q3).
    number = int(entry["sha256"][8:16], 16) % 900 + 100
    img = Image.new("RGB", (160, 80), "white")
    ImageDraw.Draw(img).text((80, 40), str(number), fill="black", anchor="mm", font=ImageFont.load_default(size=48))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    if PICTURE == "file":
        picture = LAB / "pictures" / f"{Path(entry['path']).stem}.png"
        picture.parent.mkdir(exist_ok=True)
        picture.write_bytes(buf.getvalue())
        data["picture"] = picture.relative_to(LAB).as_posix()
        return CallToolResult(content=[TextContent(text=json.dumps(data))])
    png = base64.b64encode(buf.getvalue()).decode()
    return CallToolResult(
        content=[
            TextContent(text=json.dumps(data)),
            TextContent(text=f"The picture for {entry['path']} follows."),
            ImageContent(data=png, mime_type="image/png"),
        ]
    )


@mcp.tool()
async def run_experiment(path: str) -> CallToolResult:
    """Run one experiment file and return its measured value and a picture.

    `path` is relative to the lab folder, e.g. 'experiments/e1.py'. The file's first line must be
    '# H<n>: <statement>', and H<n> must already be registered in notebook.md. Each file runs once.
    Each run uses one unit of budget.
    """
    file, rel = _resolve(path)
    async with _lock:
        first = file.read_text().splitlines()[:1]
        m = HEADER.match(first[0]) if first else None
        if not m:
            raise ToolError(
                f"Refused: the first line of {rel} must be '# H<n>: <statement>' (for example '# H1: ...')."
            )
        hyp = m.group(1)
        notebook = LAB / "notebook.md"
        if not notebook.exists() or not re.search(rf"\b{hyp}\b", notebook.read_text()):
            raise ToolError(f"Refused: {hyp} is not registered in notebook.md. Add {hyp} to notebook.md, then retry.")
        ledger = _ledger()
        if rel in _running or any(e["path"] == rel for e in ledger):
            raise ToolError(f"Refused: {rel} has already run. Use get_result to read its result.")
        if len(ledger) + len(_running) >= BUDGET:
            raise ToolError("Refused: the budget is used up. No more experiments can run.")
        _running.add(rel)
        content = file.read_bytes()
    try:
        started = time.time()
        await anyio.sleep(DELAY_S)
        sha = hashlib.sha256(content).hexdigest()
        entry = {
            "path": rel,
            "hypothesis": hyp,
            "sha256": sha,
            "value": round(int(sha[:8], 16) / 0xFFFFFFFF * 100, 3),
            "started_at": started,
            "finished_at": time.time(),
        }
        async with _lock:
            with LEDGER.open("a") as f:
                f.write(json.dumps(entry) + "\n")
            remaining = BUDGET - len(_ledger()) - (len(_running) - 1)
    finally:
        _running.discard(rel)
    return _result(entry, remaining)


@mcp.tool()
async def get_budget() -> str:
    """Return how many experiments can still be run."""
    async with _lock:
        return json.dumps({"budget_remaining": BUDGET - len(_ledger()) - len(_running)})


@mcp.tool()
async def get_result(path: str) -> CallToolResult:
    """Return the stored result of an experiment file that has already run. `path` as for run_experiment."""
    _, rel = _resolve(path, must_exist=False)
    for entry in _ledger():
        if entry["path"] == rel:
            return _result(entry)
    raise ToolError(f"Refused: {rel} has not run yet.")


if __name__ == "__main__":
    mcp.run("stdio")
