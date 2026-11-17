---
inclusion: always
---

# Structure

Source: `docs/brief.md` section 3. The rules in `rules.md` apply to every folder here.

## Layout

```
/.kiro/            builder specs, steering, hooks (how the lab was built); blind-scan/ holds the reviewed stop list
/bench/            the skeleton
/body-lab/         application 1 (adapter/, model/, lab/)
/wind-tunnel/      application 2 (same shape)
/build-from-spec/  the reader's requests (requests/), its agent files and the script that starts its runs
/notebook/         the lab notebook (static site)
/infra/            AWS CDK
/sessions/         published session records
/discovered/       Dr. Kiro's final spec of each ended session, copied from its sealed record
/bench-run/        builder-side files of a running session (session config, hook log); git-ignored
/docs/brief.md     the brief
/docs/ja/          Japanese reference translations of the specs (see japanese-translations.md)
/docs/status.md    the current step and open questions, for handing over between sessions (handoff.md)
/docs/requests/    the user's requests for specs, from TEMPLATE.md (handoff.md)
/scripts/          repository scripts (ja-check.sh)
/spikes/           scratch area, not part of the product
```

## Application shape

Each application has the same three folders:

- `adapter/`: the code that plugs the application into the bench. An application provides only its knobs, how to
  run one trial, what is measured, one picture, and its budget.
- `model/`: the system itself. Never visible from `lab/`. For wind-tunnel this is the solver setup, which the
  builder writes from the `wind-tunnel` spec.
- `lab/`: the only folder Dr. Kiro opens. It holds Dr. Kiro's own `.kiro/` (agent, steering, hooks, its lab spec)
  and its experiment files. It must pass the blind scan at all times.

Each application runs on its own. body-lab needs no Docker.

## Fixed contents

- `body-lab/model/` is supplied by the user from the earlier prototype. Its two model files,
  `specimen_01.xml` and `specimen_01.wiring.json`, must not be edited, moved or renamed. Code elsewhere reads them.
  The `README.md` in that folder may be updated only when the user asks. It is the only `model/` folder that is
  fixed.
- `docs/brief.md` is the user's input. Kiro edits it only when the user asks for that in chat; never make an unrequested edit. Every edit states what changed in the commit message.

## Two kinds of `.kiro`

- The root `/.kiro/` is how the lab was built (the builder's specs and steering).
- Each `<application>/lab/.kiro/` is Dr. Kiro itself.

Both stay tracked in git (see `.gitignore`). The README must point to both.

## spikes/

A scratch area for throwaway experiments. It is not part of the product: nothing outside `spikes/` may import,
reference, copy from at runtime, or depend on anything in it. Findings from a spike reach the product only through a
spec. Do not edit files in `spikes/` that another session is working on.
