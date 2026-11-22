---
inclusion: always
---

# Method

## The loop

1. Add the experiment to `.kiro/specs/lab/tasks.md` as one task line under its phase:
   `- [ ] E<n> / H<n>: <what it tests>`. The bench numbers experiments in the order they run (E1, E2, ...), so
   `E<n>` is one more than the last experiment that ran.
2. Write its hypothesis in `.kiro/specs/lab/requirements.md`.
3. Register it with `register_hypothesis`.
4. Write one experiment file in `experiments/` at the root of the lab (next to `.kiro/`, not inside `.kiro/specs/`)
   that names it.
5. Run it with `run_experiment`, and open each picture it returns.
6. Tick its task line and update `design.md`.
7. Record a verdict with `record_verdict`. The bench keeps a copy of your spec files at each run, verdict and end,
   so a box ticked before the verdict shows in that copy. Then start the next loop.

## Hypotheses

- A hypothesis is one EARS sentence and a `prediction` block. Each prediction names a measurement, the parameter
  values it is about, and a range that a measurement can fall outside.
- Label each prediction with the condition class you believe it has: `inside`, `new-combination`, `outside` or
  `not-comparable`.
- Once registered, never edit the heading, the sentence or the block. Write notes and results below the block.

````markdown
### H<n>: <short title>

WHEN <condition>, THE system SHALL <response>.

```prediction
[[prediction]]
id = "P1"
measurement = "<measurement>"
range = [<low>, <high>]
label = "<condition class>"
[prediction.when]
<parameter> = <value>
```

Notes and results go here, below the block.
````

## Experiments

- First line `# H<n>: <title>`, naming a registered hypothesis. Then `PHASE`, `MODE`, `PARAMS`, `TRIALS`, and in
  sweep mode `SWEEP`.
- Each function-of-time input is a function `def <input>(t, <parameters>)`. Each number input is listed in `PARAMS`
  or computed by a function of the same name.
- Plain math only: functions, local variables, `if`, `for` over a list or `range`, lists, arithmetic, and `math`.
  No other import.
- `compare` runs 1 to 3 variants; `sweep` runs exactly 6 points over 1 or 2 parameters.
- Keep parameter names the same across experiments. A renamed parameter makes a prediction not comparable.
- For a structurally different compare variant, add a flag parameter and branch on it with `if`.
- Each set of inputs runs once. An exact repeat is refused.

```python
# H<n>: <title>
import math

PHASE = "map"
MODE = "compare"
PARAMS = ["<amplitude>", "<flag>", "<number input>"]
TRIALS = [
    [<value 1>, 1, <value 3>],
    [<value 2>, 0, <value 3>],
]


def <input>(t, <amplitude>, <flag>):
    if <flag> == 1:
        return <amplitude> * math.sin(2 * math.pi * t)
    return 0
```

```python
# H<n>: <title>
import math

PHASE = "rules"
MODE = "sweep"
PARAMS = ["<period>", "<number input>"]
SWEEP = ["<period>"]
TRIALS = [
    [<period 1>, <value>],
    [<period 2>, <value>],
    [<period 3>, <value>],
    [<period 4>, <value>],
    [<period 5>, <value>],
    [<period 6>, <value>],
]


def <input>(t, <period>):
    return <level> * math.sin(2 * math.pi * t / <period>)
```

## Pictures

Each trial's picture is a file whose path `run_experiment` returns. Open it with the file tool.

## Paths

Write only paths relative to your folder in your files. Never write an absolute path.

## When the bench says no

- A refusal says what to fix. Fix it and continue.
- A bench failure ends the session. Stop.
