# Random points inside the final ranges (task 14.4 stage 3b, step 5; a measurement for a proposal only)

Question: how often does a point inside the final declared ranges fail to settle? A failure ends a session.
This measures it. No rule, range, limit or setup was changed because of it.

## Method

- Final ranges: `aspect` [0.5, 3], `corner` [0, 1], `splitter` [0, 3], `angle` [0, 15]; the corner rule of
  Requirement 6.11 (`min_arc` 0.0314, `min_line` 0.0025, margin 115 s).
- Seed: `random.Random(20260514)`. Each draw takes `rng.uniform(low, high)` for `aspect`, `corner`, `splitter`,
  `angle` in that order, the ranges read from the declaration. A draw that `check_inputs` of the adapter refuses is
  counted as refused and replaced by the next draw, until 30 accepted draws exist. Result: 31 draws, 30 accepted,
  1 refused (draw 4).
- The 30 accepted points were run one at a time with `WindAdapter.run_trial` (limit 140 s), on the local Mac, new
  code, real Docker, the machine not controlled. Driver: `spikes/timing/random_points.py`; progress file
  `bench-run/wind-tunnel/random-progress.jsonl` (git-ignored; it holds the full-precision values and the first
  attempts). Knob values below have 6 significant digits; the full values are the draws of the seed above.
- A run that does not settle was recorded and the loop went on (measurement mode). Nothing was retried except the
  five runs described under "An environment fault".

## An environment fault in the first pass (not a model result)

Draws 11 to 15 ended each in 0.4 to 0.5 s with "the solver run exited with code 127". The solver log of the kept
case folder says the start script of the case was not found inside the container (`/case/Allrun: No such file or
directory`) although it is written before the container starts. Each of them followed a failed run whose case
folder the driver had renamed (moved aside) before the next run; all other runs of the pass went normally. The cause
is not known. The five points were run again by the same
driver (the same inputs, the same code); all five settled (51.5 to 58.6 s). The table shows the rerun and quotes
the first attempt. If the five first attempts are counted as failures, the count is 7 of 30. This is an open
question in the report (a stale bind mount after the rename is a guess, not a finding).

## Table (draw numbers are 1-based; times are wall-clock of `run_trial`)

| draw | aspect | corner | splitter | angle | outcome | wall-clock run_trial (s) | note |
|---|---|---|---|---|---|---|---|
| 1 | 0.882194 | 0.180558 | 0.0791917 | 3.278 | settled | 51.8 |  |
| 2 | 2.49727 | 0.557337 | 0.979711 | 6.02366 | settled | 51.0 |  |
| 3 | 0.928682 | 0.666028 | 1.34903 | 11.5696 | settled | 51.2 |  |
| 4 | 2.93587 | 0.0380798 | 0.0841124 | 12.2793 | refused | - | corner 0.0380798471658 is not accepted: corner must be 0, 1, or between 0.04 and 0.997 when aspect is 2.9358734547 |
| 5 | 1.44955 | 0.541957 | 2.5009 | 11.4827 | settled | 52.8 |  |
| 6 | 1.38841 | 0.989332 | 1.69833 | 7.08178 | settled | 49.7 |  |
| 7 | 0.67073 | 0.892694 | 0.892786 | 8.15377 | settled | 68.9 |  |
| 8 | 2.42323 | 0.957437 | 2.49385 | 0.946208 | settled | 42.4 |  |
| 9 | 1.3402 | 0.895145 | 2.82657 | 10.67 | settled | 70.3 |  |
| 10 | 2.57819 | 0.953007 | 1.241 | 0.83314 | did not settle | 52.3 | cl_amp rule: the amplitudes of the two halves differ by 0.0105601, more than the limit 0.00446251 |
| 11 | 2.71747 | 0.0785035 | 0.433703 | 10.5066 | settled | 57.6 | first attempt: solver failed in 0.5 s, the solver run exited with code 127; this row is the rerun |
| 12 | 1.53812 | 0.580723 | 0.247516 | 8.27772 | settled | 51.5 | first attempt: solver failed in 0.5 s, the solver run exited with code 127; this row is the rerun |
| 13 | 1.58897 | 0.928344 | 1.32645 | 9.31842 | settled | 53.4 | first attempt: solver failed in 0.4 s, the solver run exited with code 127; this row is the rerun |
| 14 | 2.66655 | 0.93238 | 0.440241 | 4.35666 | settled | 57.2 | first attempt: solver failed in 0.5 s, the solver run exited with code 127; this row is the rerun |
| 15 | 1.89863 | 0.216988 | 1.55404 | 6.72231 | settled | 58.6 | first attempt: solver failed in 0.5 s, the solver run exited with code 127; this row is the rerun |
| 16 | 2.81477 | 0.824776 | 0.539555 | 14.3808 | settled | 58.9 |  |
| 17 | 2.64063 | 0.119374 | 2.53738 | 11.5277 | settled | 63.0 |  |
| 18 | 0.706798 | 0.361135 | 0.64795 | 5.25167 | settled | 69.8 |  |
| 19 | 2.31717 | 0.491406 | 1.58972 | 13.8931 | settled | 56.7 |  |
| 20 | 1.77247 | 0.112132 | 0.258448 | 1.04773 | settled | 60.9 |  |
| 21 | 2.07597 | 0.542703 | 1.05023 | 8.86702 | settled | 54.3 |  |
| 22 | 2.53486 | 0.643322 | 1.15868 | 1.07201 | did not settle | 56.0 | cl_amp rule: the amplitudes of the two halves differ by 0.00682206, more than the limit 0.00648588 |
| 23 | 1.48304 | 0.960782 | 1.01807 | 1.83156 | settled | 56.3 |  |
| 24 | 1.04656 | 0.319976 | 1.90127 | 3.79205 | settled | 57.1 |  |
| 25 | 0.911197 | 0.71995 | 2.57921 | 5.82283 | settled | 73.6 |  |
| 26 | 1.87661 | 0.0834919 | 2.20306 | 3.00213 | settled | 68.8 |  |
| 27 | 0.816488 | 0.706639 | 1.97513 | 14.9268 | settled | 58.0 |  |
| 28 | 1.96577 | 0.101331 | 0.533973 | 8.35757 | settled | 59.5 |  |
| 29 | 2.48462 | 0.804052 | 0.0438422 | 3.84326 | settled | 54.2 |  |
| 30 | 1.28794 | 0.0960521 | 2.77431 | 13.8897 | settled | 64.6 |  |
| 31 | 1.87286 | 0.0556764 | 0.723459 | 2.60604 | settled | 82.5 |  |

## Counts

| | count | rate |
|---|---|---|
| draws | 31 | |
| refused by `check_inputs` | 1 | 1 of 31 draws (3.2%) |
| accepted and run | 30 | |
| settled | 28 | 28 of 30 (93.3%) |
| did not settle | 2 (draws 10 and 22) | 2 of 30 = 6.7%, Wilson 95% interval 1.8% to 21.3% |
| time limit, mesh failed, solver failed (final rows) | 0 | 0 of 30 |
| solver failed in the first attempt (exit code 127, environment fault, rerun settled) | 5 (draws 11 to 15) | would give 7 of 30 = 23.3% if counted |
| runs above 115 s | 0 | 0 of 30 (the slowest 82.5 s at draw 31; the fastest 42.4 s; the mean 58.8 s) |

## Failures (final rows), with the settle-rule numbers

- Draw 10: aspect 2.57819, corner 0.953007, splitter 1.241, angle 0.83314. Did not settle (52.3 s): cl_amp rule,
  the amplitudes of the two halves differ by 0.0105601, more than the limit 0.00446251.
- Draw 22: aspect 2.53486, corner 0.643322, splitter 1.15868, angle 1.07201. Did not settle (56.0 s): cl_amp rule,
  the amplitudes of the two halves differ by 0.00682206, more than the limit 0.00648588.

Both failures have `aspect` above 2.5 and `angle` near 1 degree, and both are by the `cl_amp` rule with small
amplitudes. Two points are too few to say more, and nothing here is a claim about where the failures lie. Earlier
measurements (`extreme-v2-summary.md`) found 3/0/0 and 3/0/3 failing by the `cd` rule at angles 20 to 30, and 3/0/3
failing by the `cl_amp` rule at angle 10, so this kind of failure is known at large `aspect`.
