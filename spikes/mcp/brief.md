# Brief: can the lab bench be an MCP server?

## Background
We have a Kiro custom agent that runs experiments by calling one command-line program (the "bench"). Today the agent has a shell that is allowed to run only that program, and a pre-tool hook polices everything else. We want to replace this with: **the agent has no shell; the bench is an MCP server; the agent's only tools are file writes inside its folder and the bench's tools.**

This is a spike. Write the least code that answers the questions. No spec, no tests beyond what answers a question.

## Step 1. A toy bench
Build a local MCP server (Python 3.12, run with `uv`, stdio transport) named `bench` with three tools:

| Tool | Input | Behaviour |
|---|---|---|
| `run_experiment` | `path` (a file under `experiments/`) | Refuses unless the file's first line is `# H<n>: …` and `H<n>` appears in `notebook.md`. Refuses a file that already ran. Otherwise sleeps for `delay_s` (a server setting, default 2), returns `{"value": <deterministic number from the file's hash>, "budget_remaining": n}` and one small PNG. Appends a line to `ledger.jsonl` next to the server, outside the agent's folder. |
| `get_budget` | none | Returns the remaining budget (starts at 5). |
| `get_result` | `path` | Returns the stored result of a file that ran. |

A refusal must reach the agent as a clear message it can act on, and must leave the ledger unchanged.

Folder layout:
```
spikes/mcp/bench/     the server and its ledger (the agent must not be able to read this)
spikes/mcp/lab/       the agent's workspace: notebook.md, experiments/
spikes/mcp/lab/.kiro/ the agent definition and hooks for the test
```

## Step 2. A test agent
Create a custom agent `tester` in `lab/.kiro/` with:
- file read and write limited to `lab/`;
- the `bench` MCP server's tools;
- **no shell, no web, nothing else.**

Also add two hooks in `lab/.kiro/hooks/`: a pre-tool hook and a post-tool hook that each append the tool name and input to `lab/hook-log.jsonl`, for all tools.

## Step 3. Answer these questions
Run each check, in Kiro CLI with `--agent tester` and, where possible, in the IDE chat. Write `results.md` with, for each question: yes / no / partly, the exact config or command used, and what was observed. If you cannot run a check yourself, say so and write the steps for the user to run it. **Do not answer from documentation alone; mark any answer that was not observed as "not observed".**

| # | Question | How to check |
|---|---|---|
| Q1 | Can a custom agent be given MCP tools and file access with no shell at all? | Ask the agent to run `ls` and to read `../bench/ledger.jsonl`. Both must fail. Then ask it to call `get_budget`. It must work. |
| Q2 | Do the pre-tool and post-tool hooks fire on MCP tool calls? Can a pre-tool hook block one? | Look at `hook-log.jsonl` after a `run_experiment` call. Then make the pre-tool hook exit with the blocking code for `run_experiment` and see if the call is stopped. |
| Q3 | Can the agent see a picture returned by an MCP tool? | Have `run_experiment` return a PNG with a number drawn in it that is not in the JSON. Ask the agent what number it sees. If image content is not passed through, test the alternative: the server writes the PNG into `lab/` and returns its path, and the agent opens it. |
| Q4 | Does a long call survive? | Set `delay_s` to 120, then 300. Note any timeout and whether it is configurable. |
| Q5 | Does a refusal come back as something the agent can fix? | Run a file with no registered hypothesis. The agent should register it and retry without being told how. |
| Q6 | What does the agent see of the server? | Ask the agent to describe its tools. Only the names, descriptions and input schemas we wrote should appear; nothing about the server's files. |
| Q7 | Can the agent start or reconfigure an MCP server itself? | Ask it to add another MCP server or to change the bench's settings. It must not be able to. |
| Q8 | Are three calls at once possible? | Ask for three `run_experiment` calls in one turn. Note whether they run in parallel or in sequence. |
| Q9 | Does the same setup work in the IDE chat with the custom agent selected? | Repeat Q1 and Q3 there. Note any difference from the CLI. |

## Step 4. Report
End `results.md` with: the working agent definition and MCP configuration, copied in full; everything that surprised you; and what you would change in the plan above. Keep opinions separate from observations.
