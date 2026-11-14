# Form-knowledge review of wind-tunnel (task 13.2; Requirement 12.3-12.5)

This is a builder-side checklist. It is not automated and it is not a guarantee: the blind scan checks terms and
paths only, so a person reads every text Dr. Kiro can read. Each line below says that the text was read and
states no effect of the body's shape or of a knob value on the flow or on a measurement.

Reviewer: builder (Kiro in this repository), by reading each text in full. The user may check it.

## Builder-written files of `wind-tunnel/lab/`

| Text | Result | Reviewed by |
|---|---|---|
| `.gitignore` | reviewed, no form knowledge | builder |
| `.kiro/agents/dr-kiro-prompt.md` | reviewed, no form knowledge | builder |
| `.kiro/agents/dr-kiro.json` | reviewed, no form knowledge | builder |
| `.kiro/steering/method.md` | reviewed, no form knowledge | builder |
| `.kiro/steering/workflow.md` | reviewed, no form knowledge | builder |
| `.kiro/hooks/calllog.py` | reviewed, no form knowledge | builder |
| `.kiro/hooks/calllog-pre-tool.json` | reviewed, no form knowledge | builder |
| `.kiro/hooks/calllog-post-tool.json` | reviewed, no form knowledge | builder |
| `.kiro/hooks/confine.py` | reviewed, no form knowledge | builder |
| `.kiro/hooks/confine-pre-tool.json` | reviewed, no form knowledge | builder |

## Told set

| Text | Result | Reviewed by |
|---|---|---|
| The told set as a whole (the text of `wind-tunnel-told-set`: the knob lines, the measurement lines, the picture line, the budget line) | reviewed, no form knowledge | builder |
| `measured_by` | reviewed, no form knowledge | builder |
| The goal | reviewed, no form knowledge | builder |

## Knob texts

| Knob | Which sentences are geometry definitions | Result | Reviewed by |
|---|---|---|---|
| `aspect` | Both sentences: the length of the body in body heights; the height is 1. | reviewed, no sentence states an effect | builder |
| `corner` | Both sentences: the radius of each corner arc as a fraction of half of the shorter side; 0 gives square corners and 1 the largest radius that fits. | reviewed, no sentence states an effect | builder |
| `splitter` | All sentences: the length of the plate; where the length is counted from; the line it lies along, the attachment with no gap and the thickness; 0 means no plate. | reviewed, no sentence states an effect | builder |
| `angle` | All sentences: the angle between the length direction and the oncoming flow; 0 means the same direction; the centre of the turn and that the plate turns with the body; the sense of a positive angle. | reviewed, no sentence states an effect | builder |

## Public reasons of `failures.py`

| Reason | Result | Reviewed by |
|---|---|---|
| `NOT_SETTLED`: "the trial did not settle" | reviewed, no form knowledge | builder |
| `INCOMPLETE`: "the trial could not be completed" | reviewed, no form knowledge | builder |
| `TIMEOUT`: "the trial took too long" | reviewed, no form knowledge | builder |

## Other

| Text | Result | Reviewed by |
|---|---|---|
| The body-lab told text (the declaration sentences, `measured_by`, the errors), including sentences filled in at run time, is reviewed by a person for sentences that name the engine, a library or a version. No automatic check is added for it. | to be reviewed by a person; not part of this task | |
