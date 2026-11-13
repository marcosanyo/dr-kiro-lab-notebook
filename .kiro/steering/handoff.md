---
inclusion: always
---

# Working across Kiro Web and the local Kiro

The user works in two places: Kiro Web (no hooks, no OpenGL, no Docker, no Kiro CLI) and the local Kiro on the
user's Mac (everything runs). Git is the shared state. `docs/status.md` carries what git does not.

## At the start of every session

1. Read `docs/status.md`: the current step, open questions, and notes per environment.
2. Run `git fetch` and check the open pull requests before choosing a branch.

## At the end of every session, or before handing over

1. Commit and push everything the next session needs. Nothing stays only on one machine: session records,
   results of manual checks, and notes go into git.
2. Update `docs/status.md`: what was done, the next step, open questions, and anything learned that applies to
   one environment only. Keep it short; history lives in git and in each spec's tasks and decisions.

## Division of work

- Kiro Web: writing and reviewing specs, translations, code that needs no simulator.
- Local Kiro: implementing and verifying, simulator and Docker work, Dr. Kiro sessions in Kiro CLI.

## Starting a spec

If `docs/requests/<spec>.md` exists, read it first: it is the user's request for that spec, filled in from
`docs/requests/TEMPLATE.md`. Ask only what it leaves open, including every `[DECIDE]` item of the brief.

## Language

Reports and questions to the user are in Japanese (`rules.md` 5). Code, commits, specs and steering are in English.
`docs/status.md` and `docs/requests/` are written in Japanese for the user.
