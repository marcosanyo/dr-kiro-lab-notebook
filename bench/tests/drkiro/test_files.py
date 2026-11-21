"""dr-kiro task 1: the examples in the lab steering are accepted by the bench's parsers once their
placeholders are filled in, and the agent file is lab-bench design F10 plus the dr-kiro fields (2.1, 7.2)."""

import json
import re
from importlib import resources

from bench.fake.adapter import declaration
from bench.lang.experiment import STEP_BOUND, compute, prepare
from bench.specfiles.discovered import parse_table
from bench.specfiles.hypotheses import parse_hypothesis

FILES = resources.files("bench.drkiro") / "files"
DECL = declaration()


def text(name: str) -> str:
    return (FILES / name).read_text(encoding="utf-8")


def fenced(name: str) -> list[str]:
    """The fenced blocks of a steering file: 4-backtick blocks first, then 3-backtick blocks outside them."""
    source = text(name)
    outer = re.findall(r"^````\w*\n(.*?)^````$", source, re.S | re.M)
    rest = re.sub(r"^````\w*\n.*?^````$", "", source, flags=re.S | re.M)
    return outer + re.findall(r"^```\w*\n(.*?)^```$", rest, re.S | re.M)


def fill(block: str, values: dict[str, str]) -> str:
    for placeholder, value in values.items():
        block = block.replace(placeholder, value)
    assert "<" not in re.sub(r"<=|< ", "", block), block
    return block


def test_hypothesis_example() -> None:
    (block,) = [b for b in fenced("method.md") if "```prediction" in b]
    filled = fill(
        block,
        {
            "H<n>": "H1",
            "<short title>": "amp moves it",
            "<condition>": "amp rises",
            "<response>": "move further",
            "<measurement>": "distance",
            "<low>": "0.1",
            "<high>": "0.9",
            "<condition class>": "outside",
            "<parameter> = <value>": "amp = 0.5",
        },
    )
    hypothesis = parse_hypothesis(filled, "H1", DECL, "requirements.md")
    assert [p.global_id for p in hypothesis.predictions] == ["H1.P1"]


def _experiment(mode: str, values: dict[str, str]) -> None:
    (block,) = [b for b in fenced("method.md") if f'MODE = "{mode}"' in b]
    experiment = compute(prepare(fill(block, values), "experiments/e.py", DECL, step_bound=STEP_BOUND))
    assert experiment.mode == mode and experiment.trials


def test_compare_example_with_a_flag() -> None:
    _experiment(
        "compare",
        {
            "H<n>": "H1",
            "<title>": "two variants",
            "<amplitude>": "amp",
            "<flag>": "second",
            "<number input>": "gain",
            "<input>": "drive",
            "<value 1>": "0.5",
            "<value 2>": "0.25",
            "<value 3>": "1.0",
        },
    )


def test_sweep_example() -> None:
    periods = {f"<period {i}>": str(0.25 * i) for i in range(1, 7)}
    _experiment(
        "sweep",
        {
            "H<n>": "H1",
            "<title>": "period sweep",
            **periods,
            "<period>": "period",
            "<number input>": "gain",
            "<input>": "drive",
            "<value>": "1.0",
            "<level>": "0.5",
        },
    )


def test_discovered_spec_example() -> None:
    (block,) = [b for b in fenced("workflow.md") if "## Discovered spec" in b]
    filled = fill(
        block,
        {
            "<rule>": "a rule",
            "<scope>": "a scope",
            "E<a>": "E1",
            "E<b>": "E2",
            "E<c>": "E3",
            "H<a>": "H1",
            "H<c>": "H3",
        },
    )
    table = parse_table("# Design\n\n" + filled, "design.md")
    assert [r.status for r in table.rows] == ["validated", "rejected", "observed"]


def test_agent_file_is_f10_plus_dr_kiro_fields() -> None:
    agent = json.loads(text("dr-kiro.json"))
    assert {k: agent[k] for k in ("name", "prompt", "resources")} == {
        "name": "dr-kiro",
        "prompt": "file://./dr-kiro-prompt.md",
        "resources": ["file://.kiro/steering/**/*.md"],
    }
    assert agent["mcpServers"] == {"bench": {"command": "bench-mcp", "args": []}}
    assert agent["tools"] == ["read", "write", "@bench"]
    assert agent["includeMcpJson"] is False and agent["includePowers"] is False
    protected = [".kiro/agents/**", ".kiro/hooks/**", ".kiro/steering/**", ".kiro/settings/**"]
    assert agent["permissions"]["rules"] == [
        {"capability": "fs_read", "match": ["./**"], "effect": "allow"},
        {"capability": "fs_write", "match": ["./**"], "effect": "allow"},
        {"capability": "fs_write", "match": protected, "effect": "deny"},
        {"capability": "mcp", "match": ["bench/*"], "effect": "allow"},
    ]
