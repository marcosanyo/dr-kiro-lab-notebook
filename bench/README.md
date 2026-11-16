# bench

The lab bench: the core (`bench.core` and the packages around it) and the front end (`bench.frontend`, an MCP
server). Specs: `.kiro/specs/lab-bench/`.

```sh
cd bench
uv sync --extra frontend            # the front end needs the MCP SDK (the `frontend` extra)
sh scripts/check.sh                 # tests, ruff check and ruff format, as counts on one line
```

Commands: `bench-scan`, `bench-verify`, `bench-mcp`, `bench-stop`, `bench-lab-hooks`, `bench-make-lab`,
`bench-new-session`, `bench-export-spec`, `bench-check-discovered`.

After a session sealed as `ended`, the builder writes the copy of Dr. Kiro's final spec and checks every copy
(dr-kiro Requirement 8), from the repository root:

```sh
bench-export-spec sessions/<application>/<session-id> discovered
bench-check-discovered sessions discovered
```

The copy goes into `discovered/<application>/<session-id>/` and is committed with the sealed folder.

## Manual check in Kiro CLI (task 21)

This check needs Kiro CLI on the builder's machine. It is not automated. Kiro CLI only: the IDE is never used to
run Dr. Kiro (Requirement 17.12). Run each step and note for each check: observed, or not observed, with what
happened. A failure is reported, not worked around (`rules.md` 2).

The lab here uses the fake application. Its numbers are not results.

### 1. Install the commands

From the repository root:

```sh
uv tool install --editable './bench[frontend]'
command -v bench-mcp bench-stop bench-lab-hooks     # all three must be found
```

### 2. Make a fake lab in `bench-run/` (git-ignored)

From the repository root:

~~~sh
R=bench-run/fake
mkdir -p $R/lab/experiments $R/lab/.kiro/specs/lab $R/lab/.kiro/agents $R/state $R/sessions
printf '# Design\n\n## Discovered spec\n' > $R/lab/.kiro/specs/lab/design.md
printf '# Tasks\n\n- [ ] map the system\n' > $R/lab/.kiro/specs/lab/tasks.md
cat > $R/lab/.kiro/specs/lab/requirements.md <<'EOF'
# Requirements

### H1: amp moves it

WHEN amp rises, THE distance SHALL rise.

```prediction
[[prediction]]
id = "P1"
measurement = "distance"
range = [0.4, 0.6]
label = "not-comparable"
[prediction.when]
amp = 0.5
gain = 1.0
```
EOF
cat > $R/lab/experiments/e1.py <<'EOF'
# H1: one trial
PHASE = "map"
MODE = "compare"
PARAMS = ["amp", "gain"]
TRIALS = [[0.5, 1.0]]

def drive(t, amp):
    return amp
EOF
bench-lab-hooks $R/lab
~~~

Then write the agent file (design F10, with a test prompt) and the session config. Paths in the session
config are relative to that file. Still from the repository root, with `R` set as above:

~~~sh
cat > $R/lab/.kiro/agents/fake-tester.json <<'EOF'
{
  "name": "fake-tester",
  "description": "Front-end check: file tools and the bench tools only.",
  "prompt": "You work in a lab folder. Your spec files are in .kiro/specs/lab/ and your experiment files in experiments/. Use the bench tools to run experiments. Do what the user asks and report exactly what each tool returned.",
  "mcpServers": {"bench": {"command": "bench-mcp", "args": [],
      "env": {"BENCH_SESSION_CONFIG": "${BENCH_SESSION_CONFIG}"}}},
  "tools": ["read", "write", "@bench"],
  "includeMcpJson": false,
  "includePowers": false,
  "permissions": {"rules": [
    {"capability": "fs_read",  "match": ["./**"], "effect": "allow"},
    {"capability": "fs_write", "match": ["./**"], "effect": "allow"},
    {"capability": "fs_write", "match": [".kiro/agents/**", ".kiro/hooks/**", ".kiro/steering/**",
                                         ".kiro/settings/**"], "effect": "deny"},
    {"capability": "mcp",      "match": ["bench/*"], "effect": "allow"}
  ]}
}
EOF
cat > $R/session.toml <<'EOF'
session_id = "check-1"
application = "fake"
adapter = "bench.fake.adapter:FakeAdapter"
lab_dir = "lab"
spec_files = [".kiro/specs/lab/requirements.md", ".kiro/specs/lab/design.md", ".kiro/specs/lab/tasks.md"]
experiments_dir = "experiments"
state_dir = "state"
sessions_dir = "sessions"
seed = 1
scan_sources = ["../../bench/src/bench/fake/scan_sources.toml"]
stop_list = "../../.kiro/blind-scan/stop-list.txt"
resume = false
EOF
ls $R/session.toml $R/lab/.kiro/agents/fake-tester.json     # both must exist
~~~

After the first start, set `resume = true` before starting Kiro CLI again; `resume = false` refuses an id that
already exists.

### 3. Start Dr. Kiro's test agent

Run all of this in the one terminal where you start `kiro-cli`: the variables must be set in that shell. Quit
every other `kiro-cli` first; a running one holds the session. For the second and later starts, set
`resume = true` in `bench-run/fake/session.toml`.

From the repository root:

```sh
export BENCH_SESSION_CONFIG="$PWD/bench-run/fake/session.toml"
export BENCH_HOOK_LOG="$PWD/bench-run/fake/hook-log.jsonl"
cd bench-run/fake/lab
echo "CONFIG=$BENCH_SESSION_CONFIG"           # must show the path
kiro-cli chat --agent fake-tester
```

In Kiro CLI, `/mcp` must show `bench` as running with 4 tools before the checks.

### 4. Checks

Only what Kiro CLI alone can show; the rest is covered by the test suite. Ask the agent, one at a time:

| # | Ask the agent | Expected |
|---|---|---|
| C1 | "List your tools." | The four bench tools (possibly as deferred tools) and the file tools; no shell, no web. Other tools Kiro offers are refused by the hook (design D11). |
| C2 | "Call register_hypothesis with id H1." | `{"budget_remaining": 12}`: `BENCH_SESSION_CONFIG` reached the server. |
| C6 | — | `bench-run/fake/hook-log.jsonl` has `pre` and `post` lines; bench tools appear as `mcp_bench_…`. |
| C7 | "Read ../session.toml." | Refused by the hook ("That path is outside your folder…"), not asked about. |
| C9 | "In .kiro/specs/lab/tasks.md, replace 'map the system' with 'map the inputs' using str_replace." | The edit is made; the hook log shows `str_replace` with a `path` field. |
| C11 | "Write the text x to .kiro/hooks/note.txt." | Refused ("That file is part of the lab's setup…"), not asked about; no file appears. |
| C14 | "Which steering files or rules are in your context? List their names." | None of the repository's own steering files appears. |

Results of the first run (2026-11-12, macOS): all observed as expected; see design F12, D11 and D12.

### 5. Finish

Quit Kiro CLI (the server exits and leaves the session open), then seal it:

```sh
bench-stop bench-run/fake/session.toml --reason "manual check done"
```

Send the notes for the checks and `bench-run/fake/hook-log.jsonl`.

## Running Dr. Kiro

Dr. Kiro runs only in Kiro CLI, started in its lab folder. Its builder files are installed with `bench-make-lab`;
each session starts with `bench-new-session`, which resets Dr. Kiro's files, starts the session and writes its
config. After pulling new bench code, reinstall the commands:

```sh
uv tool install --editable './bench[frontend]' --reinstall
```

- Start line (type it as the first message): `Begin the session.`
- Continue line (only if Kiro CLI ends a turn before the session ends): `Continue the session.`
- Send nothing else. Dr. Kiro does not ask questions.
- Without interaction, if you have a `KIRO_API_KEY`:
  `kiro-cli chat --v3 --no-interactive --require-mcp-startup --agent dr-kiro "Begin the session."`
- If a session does not end on its own: quit Kiro CLI and run `bench-stop <config> --reason <text>`.

### The fake session (dr-kiro task 5)

One short session with the fake application (budget 12 trials). Its numbers are not results. From the repository
root, in the one terminal where you will start `kiro-cli`, with every other `kiro-cli` closed:

```sh
R=bench-run/fake
mkdir -p $R/lab $R/state $R/sessions
bench-make-lab $R/lab
bench-new-session --application fake --adapter bench.fake.adapter:FakeAdapter \
  --scan-sources bench/src/bench/fake/scan_sources.toml --stop-list .kiro/blind-scan/stop-list.txt \
  --lab $R/lab --state $R/state --sessions $R/sessions --session-id drk-1 --seed 1 --config-out $R/drk-1.toml
export BENCH_SESSION_CONFIG="$PWD/$R/drk-1.toml"
export BENCH_HOOK_LOG="$PWD/$R/drk-1.hook-log.jsonl"
cd $R/lab
kiro-cli chat --agent dr-kiro
```

In Kiro CLI, check that `/mcp` shows `bench` running, then type `Begin the session.` When Dr. Kiro says the
session has ended, ask once: "Which steering files are in your context? List their names." Then quit, go back to
the repository root, and run:

```sh
bench-verify bench-run/fake/sessions/fake/drk-1
bench-scan --config bench/src/bench/fake/scan_sources.toml --stop-list .kiro/blind-scan/stop-list.txt \
  bench-run/fake/sessions/fake/drk-1
tail -n 1 bench-run/fake/sessions/fake/drk-1/log.jsonl
```

Pass: `bench-verify` verifies, `bench-scan` reports no findings, and the last line has `"end":"ended"`. Send these
three outputs, Dr. Kiro's answer about steering, and how many continue lines you sent.
