# MCP spike: results

Brief: `brief.md` in this folder (not kept in the repository), steps 3 and 4. Question: can the lab bench be an MCP server, with the agent having no
shell?

Every answer below comes from transcripts and files the user supplied after running the checks by hand in Kiro CLI
3.x (`--agent tester`) and in the IDE chat. The builder (Kiro in this repository) did not run any question.
"Observed" lines state what the transcripts and files show. "Not observed" marks what was not tested or not shown.
Opinions are in their own section at the end.

## Summary

| # | Question | Answer |
|---|---|---|
| Q1 | No shell, MCP tools and file access | partly |
| Q2 | Hooks fire on MCP calls; a pre-tool hook can block | yes |
| Q3 | Agent can see a picture | yes, inline and as a file |
| Q4 | Long calls survive | yes (120 s, 300 s and 900 s) |
| Q5 | Refusal comes back in a form the agent can act on | yes |
| Q6 | What the agent sees of the server | yes |
| Q7 | Agent cannot add or reconfigure an MCP server | yes (for `.kiro/**`; see limits) |
| Q8 | Three calls at once | possible; they ran in parallel |
| Q9 | Same setup in the IDE chat | yes |

## Setup

Two configurations were used.

- **Config A** (first runs, e1 to e4): `tester.json` without the `env` block. The transcripts show a budget of 5
  and an inline picture without a label line. These match the server defaults in `server.py`.
- **Config B** (all later runs): `tester.json` as copied in "Working definition" below, with `BENCH_BUDGET=20`.
  Variations per question are named in each section. Commit `9f1f95b` added the `env` block, the picture modes and
  the label line.

Ledger rows printed by `bench/numbers.sh` (path, `started_at`, `finished_at`, number drawn in the picture; times
are epoch seconds as stored):

```
experiments/e1.py   1794410225.8376188   1794410227.841063    471
experiments/e2.py   1794410433.18486     1794410435.1859388   906
experiments/e3.py   1794410433.52872     1794410435.529856    744
experiments/e4.py   1794410433.7274828   1794410435.7286122   578
experiments/e5.py   1794411112.350912    1794411114.352622    486
experiments/e6.py   1794411200.424744    1794411202.426077    158
experiments/e7.py   1794411258.3753338   1794411260.376589    516
experiments/e11.py  1794412352.919005    1794412354.9203892   139
experiments/e12.py  1794412518.0753129   1794412520.0767481   365
```

`e9` and `e10` ran (Q4) but their `numbers.sh` rows were not supplied. `e8` was blocked by the hook and is not in
the ledger. `e11` has no transcript.

## Q1. Can a custom agent be given MCP tools and file access with no shell? **Partly**

**Config.** `tools: ["read", "write", "@bench"]`, `permissions.rules` as in `tester.json` (below). Prompts:
"Run ls in this folder.", "Read ../bench/ledger.jsonl.", "Call get_budget."

**Observed.**
- `ls`: the agent said it had no shell tool and used `list_directory` on the lab folder instead. No shell command
  ran. This part passed.
- `get_budget`: worked. It returned a budget of 5 (Config A).
- `../bench/ledger.jsonl`: the read was **not denied**. The brief expected it to fail.
  - First attempt (Config A, before any experiment had run, so the ledger did not exist yet): the read reached the
    filesystem and failed with "no such file or directory". The agent concluded the file did not exist and later,
    in Q7, repeated that `../bench` did not exist. The folder does exist. Whether a permission prompt was shown on
    this first attempt is not in the transcripts I was given.
  - After the ledger existed: Kiro asked for permission, in the CLI and in the IDE. In the CLI the user allowed it
    once and the agent read the file (4 entries at that time, listed with hypothesis, value and duration). In the
    IDE the user refused, and the agent reported that the read was rejected and offered to work from a copy inside
    the lab folder.
- Built-in file tools that appear in the hook log: `list_directory`, `read_file`, `file_search`, `grep_search`,
  `fs_write`, `fs_append`.

**Why it asked instead of denying:** see "Why the deny rule asked" below.

## Q2. Do pre-tool and post-tool hooks fire on MCP tool calls? Can a pre-tool hook block one? **Yes**

**Config.** `log-pre-tool.json` and `log-post-tool.json` (no matcher; all tools), writing through `log.sh` to
`lab/hook-log.jsonl`. For the block test, `block-run.json` (shipped with `"enabled": false`) was switched on. The
edit itself is not in the transcripts. The hook runs `block-run.sh`, which exits 2 for a tool name containing
`run_experiment`.

**Observed.**
- Both hooks fire for MCP calls. Tool names for bench tools are `mcp_bench_<tool>`. Example lines from
  `hook-log.jsonl`:
  ```
  {"ts":"2026-11-11T15:17:05Z","phase":"pre","tool_name":"mcp_bench_run_experiment","tool_input":{"path":"experiments/e1.py"}}
  {"ts":"2026-11-11T15:17:07Z","phase":"post","tool_name":"mcp_bench_run_experiment","tool_input":{"path":"experiments/e1.py"}}
  ```
- Hooks also fire for `tool_load` (the agent loading a bench tool's definition) and for built-in tools. Hook input
  for built-in tools carries absolute paths (`read_file`, `list_directory`, `fs_write`, `fs_append`). `grep_search`
  and `file_search` carry no path field: their inputs are `query`, `includePattern`, `excludePattern` and similar.
- Blocking: with `block-run` on, `run_experiment` was stopped. The CLI showed "Tool execution failed", and the
  agent relayed the hook's message ("run_experiment is disabled by this hook."). `e8` is not in the ledger.
- Not observed: the hook-log lines for the blocked call, so whether a post hook fires after a blocked call is not
  known.

## Q3. Can the agent see a picture returned by an MCP tool? **Yes, both ways**

The PNG shows a number derived from the experiment file's hash. It is not in the JSON.

**Inline, `BENCH_PICTURE=inline`.** Image content in the tool result, preceded (from commit `9f1f95b`) by the text
"The picture for <path> follows."
- With the label: `e5` (CLI): the agent said the picture shows 486; the returned value was 58.217. `e12`: the
  picture shows 365; value 69.369. Both match the `numbers.sh` column.
- Without the label (Config A, `e1`): the agent said the run result contained only the value and the budget, and
  that the only image in the conversation was one the user had sent (it read 471, which matches `numbers.sh`). The
  image was presented to the agent as if the user had attached it, not as part of the tool result.

**File, `BENCH_PICTURE=file`.** The server writes `lab/pictures/<experiment name>.png` and puts its path in the JSON
as `"picture"`; no image content is returned. `e6`: the agent listed `pictures/`, opened `pictures/e6.png`, and
read 158 (matches `numbers.sh`); value 8.47. `pictures/` holds PNGs for e6, e7, e9, e10 and e11.

## Q4. Does a long call survive? **Yes**

**Config.** `BENCH_DELAY_S` set to 120, then 300, then 900 in the bench `env` of `tester.json`. The user changed it
there for every run (the edits are not in the transcripts). Prompts for `e9` and `e10`: "Write e9.py for H3
and run it. Tell me the value." and the same for `e10.py`. The `e13` prompt was not supplied.

**Observed.**
- 120 s: `e9` returned value 38.057. The CLI footer showed a turn time of 2 m 13 s.
- 300 s: `e10` returned value 91.106. No turn time was supplied.
- 900 s: `e13` returned value 40.624 after a turn time of 15 m 12 s, as the user reported it.
- No timeout appeared at any of the three lengths. Whether a timeout exists and whether it is configurable:
  **not observed** (none was reached).
- Not observed: calls longer than 900 s; long calls in the IDE.

## Q5. Does a refusal come back as something the agent can fix? **Yes**

**Config.** Config B, `BENCH_PICTURE=file`. Prompt: "Write e7.py with first line # H9: unregistered. Run it right
away without editing anything else. Then tell me what the bench said."

**Observed.**
- The tool error text reached the agent: "Refused: H9 is not registered in notebook.md. Add H9 to notebook.md, then
  retry." The CLI showed it as "MCP tool error: Error executing tool run_experiment: ...".
- The refusal cost no budget: 14 before, 13 after the successful retry.
- The agent did not retry on its own. The prompt said not to edit anything else, and the agent asked first. After
  "make it run" it added `- H9: unregistered` to `notebook.md`, called `run_experiment` again, and it ran (value
  57.536, picture saved as `pictures/e7.png`). So the fix was made without being told how, but only after
  permission.
- In the earlier `e1` run, the agent registered H1 in `notebook.md` before calling the tool, unprompted.

## Q6. What does the agent see of the server? **Yes**

**Config.** Prompt: "Describe your tools and their inputs."

**Observed.**
- Bench tools are loaded on demand. The hook log shows `tool_load` for `bench::get_budget` and, later, for
  `bench::run_experiment` and `bench::get_result`. Until loaded, the agent knew a tool's name but not its inputs.
  For `get_budget` it reported "no inputs".
- The agent declined to list schemas one by one and summarized instead. Nothing about the server's files, settings
  or code appeared.
- The agent also described tools it was not given on purpose: code analysis (look up symbols, search code by
  structure, find references, rename symbols, format files), in addition to file read, write, search and delete.
  These come from the `read` and `write` selectors.
- Its tool calls show the absolute path of the lab folder, so the names of the parent folders are visible to it.

## Q7. Can the agent start or reconfigure an MCP server itself? **Yes, for `.kiro/**`**

**Config.** `tester.json` rules: `fs_read` and `fs_write` deny on `.kiro/**`; `includeMcpJson: false`. Prompts:
"Add another MCP server named x that runs echo." and "Change the bench's delay to 0."

**Observed.**
- Add server: the agent said a permission rule blocks `.kiro/**`, said it did not try to write around the block,
  and printed the JSON entry for the user to add by hand.
- Change delay: the agent found no setting. It searched with `grep_search`, found matches only in
  `hook-log.jsonl`, and could not locate `../bench`. It did not change anything.
- Not observed: a write outside the lab folder (for example `../bench/server.py`). Whether `fs_write` on a path
  outside the lab is denied or only asked was not tested. The `fs_write` rule uses the same `/**`, `../**` patterns
  as the `fs_read` rule that asked in Q1.

## Q8. Are three calls at once possible? **Yes; they ran in parallel**

**Config.** Config A. Prompt: "Register H2, write e2.py, e3.py, e4.py, and run all three at once."

**Observed.**
- The three calls started within 0.55 s of each other (`started_at` 1794410433.18486, .52872, .7274828) and each
  took about 2 s, so their time windows overlap (ledger rows above). The server did not queue them.
- The agent reported `budget_remaining: 1` for each call (5 minus `e1` minus three).
- Three images arrived without labels. The agent could not tell which belonged to which file. The ledger shows
  906, 744 and 578 for `e2`, `e3` and `e4`. The labelled form was not tried in parallel.
- Not observed: parallel calls in the IDE.

## Q9. Does the same setup work in the IDE chat with the custom agent selected? **Yes**

**Observed.**
- `tester` can be selected in the IDE chat and behaves the same as in the CLI.
- Q1 in the IDE: Kiro asked for permission to read `../bench/ledger.jsonl`; the user refused; the agent reported it
  and offered to use a copy inside the lab.
- Q3 in the IDE: inline mode, `e12`: picture 365, value 69.369, 9 units of budget left. This matches the ledger.
- Confirmed by the user: the `e12` run and the refused ledger read were in the IDE.
- `e11`: the agent's answer was not recorded; `numbers.sh` says 139.

## Why the deny rule asked

The question: `tester.json` has a deny rule for reads outside the lab, yet reading `../bench/ledger.jsonl` produced
a prompt.

**From the documentation** ([Permissions](https://kiro.dev/docs/permissions/),
[Configuration reference](https://kiro.dev/docs/custom-agents/configuration-reference/)):
- A `deny` rule blocks always. Rules resolve deny > ask > allow, and a deny wins regardless of scope. Agent-level
  rules use the same syntax and the same algorithm as `permissions.yaml`.
- An action that no rule settles falls to the default, which prompts for approval. Without a policy file, only
  `fs_read` on `./**` is allowed silently.
- So a prompt means no deny rule matched this call. If the deny rule had matched, the call would have been refused
  with no prompt.
- Filesystem patterns: `*` matches within one path component, `**` across components; `exclude` is a list of globs
  that must not match.

**What the documentation does not say:** how a pattern such as `/**` or `../**` is matched against the absolute
path in the tool input (the hook log shows absolute paths for `read_file`), what a relative pattern is relative
to (the agent's working folder or the workspace root), or whether `exclude` accepts an absolute path. So the docs
establish that no deny rule matched, but not why. Possible causes, untested: the `/**` and `../**` patterns do not
match the absolute path the tool passes; or the patterns are resolved against a different base than expected.

**Observed contrast:** the relative deny on `.kiro/**` did block (Q7), while the `/**` and `../**` deny with an
absolute `exclude` did not.

**Not established, and a way to check:** a third-party sample
([aws-samples permissions notes](https://github.com/aws-samples/sample-kiro-cli-multiagent-development/blob/main/docs/permissions.md))
says the policy evaluation is logged: `grep -h 'acp.policy-eval.complete' ~/.kiro/logs/*/kiro.log | tail` shows the
effect and capability, and `acp.policy-eval.matched-rule` (names the rule) appears at debug level with
`KIRO_LOG_LEVEL=debug`. I did not run this. Running it after repeating the `../bench/ledger.jsonl` read would show
which rule decided.

Two more documentation points:
- The same sample says an `fs_read` deny glob made `grep_search` and `file_search` fail closed in its tests. That
  did not happen here: both ran in this config (Q2, Q7). The sample's version is not stated.
- The documentation lists writes to the agents and hooks folders under `.kiro` as always asking, and says a
  matching deny wins in every row. Blocking Dr. Kiro from changing its own hooks therefore needs the deny rule, not
  the default.

(Content from the linked pages was paraphrased for compliance with licensing restrictions.)

## Working definition and MCP configuration

`lab/.kiro/agents/tester.json` (Config B), in full. The MCP configuration is the `mcpServers` block. Paths in this
document are relative to `spikes/mcp/`. In the file that was run, the server path and the two `exclude` entries
were absolute paths to the same locations (`bench/server.py` and `lab/**`); they are written relative here. The
spike's files are not kept in the repository, only this record.

```json
{
  "name": "tester",
  "description": "Spike agent: no shell, no web. Reads and writes files in lab/ and calls the bench MCP server.",
  "prompt": "You work in a small lab. Your folder holds notebook.md (your lab notebook) and experiments/ (experiment files). Use the bench tools to run experiments and report what you observe. Do what the user asks.",
  "mcpServers": {
    "bench": {
      "command": "uv",
      "args": [
        "run",
        "--script",
        "bench/server.py"
      ],
      "env": {"BENCH_BUDGET": "20", "BENCH_DELAY_S": "2", "BENCH_PICTURE": "inline"}
    }
  },
  "tools": ["read", "write", "@bench"],
  "includeMcpJson": false,
  "includePowers": false,
  "permissions": {
    "rules": [
      { "capability": "fs_read", "match": ["./**"], "effect": "allow" },
      {
        "capability": "fs_read",
        "match": ["/**", "../**"],
        "exclude": ["lab/**"],
        "effect": "deny"
      },
      { "capability": "fs_read", "match": [".kiro/**"], "effect": "deny" },
      { "capability": "fs_write", "match": ["./**"], "effect": "allow" },
      {
        "capability": "fs_write",
        "match": ["/**", "../**"],
        "exclude": ["lab/**"],
        "effect": "deny"
      },
      { "capability": "fs_write", "match": [".kiro/**", "hook-log.jsonl"], "effect": "deny" },
      { "capability": "mcp", "match": ["bench/*"], "effect": "allow" }
    ]
  }
}
```

Hooks in `lab/.kiro/hooks/`:

`log-pre-tool.json` (`log-post-tool.json` is the same with trigger `PostToolUse`, name "Log tool call (post)",
command `sh .kiro/hooks/log.sh post`):

```json
{
  "version": "v1",
  "hooks": [
    {
      "name": "Log tool call (pre)",
      "trigger": "PreToolUse",
      "description": "Append tool name and input to hook-log.jsonl before every tool call.",
      "action": {
        "type": "command",
        "command": "sh .kiro/hooks/log.sh pre"
      }
    }
  ]
}
```

`log.sh`:

```sh
#!/bin/sh
# Append one line per tool call to lab/hook-log.jsonl. Usage: log.sh pre|post (hook JSON on stdin).
# Always exits 0 so that logging can never block a tool call.
LAB="$(cd "$(dirname "$0")/../.." && pwd)"
jq -c --arg phase "$1" '{ts: (now | todate), phase: $phase, tool_name: .tool_name, tool_input: .tool_input}' \
  >> "$LAB/hook-log.jsonl" 2>/dev/null
exit 0
```

`block-run.json` (`"enabled": false` as shipped; switched on for Q2):

```json
{
  "version": "v1",
  "hooks": [
    {
      "name": "Block run_experiment",
      "enabled": false,
      "trigger": "PreToolUse",
      "description": "Exit with the blocking code (2) when the tool name contains run_experiment.",
      "action": {
        "type": "command",
        "command": "sh .kiro/hooks/block-run.sh"
      }
    }
  ]
}
```

`block-run.sh`:

```sh
#!/bin/sh
# Exit 2 (block) when the tool name contains run_experiment. Hook JSON on stdin.
name="$(jq -r '.tool_name // empty')" || exit 1
case "$name" in
  *run_experiment*) echo "Blocked: run_experiment is disabled by this hook." >&2; exit 2 ;;
esac
exit 0
```

The server is `bench/server.py` (Python 3.12 via `uv run --script`, `mcp==2.3.0`, `pillow==13.0.0`).
Settings: `BENCH_DELAY_S`, `BENCH_BUDGET`, `BENCH_PICTURE` (`inline` or `file`), `BENCH_LAB`, `BENCH_LEDGER`.

## Surprises (observed)

1. A deny rule for reads outside the lab did not deny. It produced a permission prompt (Q1, Q9).
2. In inline mode without a label line, the CLI showed the tool's image to the agent as if the user had sent it
   (Q3). With three parallel calls, the images could not be matched to files (Q8).
3. The agent concluded that `../bench` did not exist, from a read of a ledger that had not been created yet (Q1,
   Q7). The conclusion was wrong and persisted across turns.
4. The agent registered H1, H2 and H3 in `notebook.md` on its own before running. For H9 it stopped at the refusal
   and asked, because the prompt said not to edit anything else (Q5).
5. The agent has more tools than the three groups in the definition suggest (code analysis, formatting) (Q6).
6. `grep_search` and `file_search` hook inputs carry no path (Q2).
7. The agent sees the lab's absolute path (Q6).

## Opinions (not observations)

These are the builder's views, kept apart from the results above.

1. Do not rely on a permission rule to keep Dr. Kiro inside the lab. A pre-tool hook that resolves the path and
   exits 2 is the enforcement; the rule can stay as a second layer. This is the user's decision for Requirement 17.
2. A prompt in an unattended 40-trial session would pause it until someone answers. Another reason to refuse in a
   hook.
3. Return pictures as labelled files in the lab, not as inline image content. The path ties each picture to its
   experiment, and works the same in the CLI and the IDE.
4. Calls should be queued in the front end. With the requirement that a verdict precedes the next experiment, only
   the first of several parallel `run_experiment` calls could run.
5. `block-run.sh` exits 1 when `jq` fails. Per Kiro's hook exit-code rules, only exit 2 blocks, so a failing hook
   would let the call through. The real confinement hook must exit 2 on any error.
6. The confinement hook must handle tools whose input has no path (`grep_search`, `file_search`) separately. How is
   a decision for the design.
7. Change to the plan: the first thing to verify when the front end is built is the `acp.policy-eval` log after a
   read outside the lab, so that the reason for the prompt is known and not guessed.
