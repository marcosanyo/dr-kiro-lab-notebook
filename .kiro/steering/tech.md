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

Open: `[DECIDE after the MCP spike: the bench is an MCP server and Dr. Kiro has no shell; or the bench is one
command and Dr. Kiro's shell allows only that.]` Do not build either until the user decides in the `lab-bench` spec.

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
