---
inclusion: always
---

# Tech

The rules in `rules.md` apply to every choice here. Anything not listed is decided in the spec that needs it, and
asked about if it is a real choice.

## Python

- Python 3.12 through `uv` only: `uv run`, `uv add`, `uv sync`, locked with `uv.lock`. No `pip`, no `conda`, no
  system Python, no `requirements.txt` as the source of truth.
- Tests: `pytest`. Property-based tests: `hypothesis` (the bench gates are tested over random sequences of agent
  actions).
- Lint and format: `ruff`.
- No type checker for now.

## Applications

- **body-lab**: MuJoCo. Renders without a display. Installs with `uv` only. Needs no Docker.
- **wind-tunnel**: OpenFOAM, run in Docker. Settings that worked in the prototype are in `docs/brief.md` 4.3; the
  `wind-tunnel` spec decides what to keep.
- Each application runs on its own, without the other installed.

## Bench interface

Decided in the `lab-bench` spec (Requirement 17), after the MCP spike (`spikes/mcp/results.md`): the bench is an
MCP server over stdio, and Dr. Kiro has no shell. Dr. Kiro's tools are file read and write, limited to its lab by a
pre-tool hook, and the four bench tools. Pictures are returned as files in the lab. Parallel calls are queued.

Dr. Kiro runs only in Kiro CLI, started in its lab folder. The Kiro IDE is for the builder and for showing the specs.

The MCP SDK (`mcp==2.3.0`) is the one runtime dependency outside the standard library. It is allowed only in the
bench front end, in the optional dependency group `frontend` (`lab-bench` design, F12, approved by the user).

## Session records

Sealed, immutable, hashed, and the sole input to the notebook. The format is decided in the `lab-bench` spec.

## Notebook

- Plain HTML, CSS and JavaScript, produced by a small Python build step (run through `uv`).
- No Node for the site. No third-party requests at runtime: no CDNs, remote fonts, analytics or embeds; every asset
  is served from the site itself.
- Everything else is decided in the `lab-notebook` spec.

## Infrastructure

- AWS CDK in TypeScript, in `infra/`. Node is used only there.
- Deployed from a developer machine with short-lived credentials. No long-lived keys anywhere.

## Secrets

Never in code, specs, logs, records or the notebook. See `.gitignore`.
