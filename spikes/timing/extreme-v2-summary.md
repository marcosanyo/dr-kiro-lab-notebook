# Extreme cases with the new code (task 14.4 stage 2, measurement only)

Measured on the local Mac, new code (140 s limit over mesh, solver and post-processing; deferred deletion; no
vorticity field written to disk), real Docker, one run at a time, `min_edge = 0.0`, nothing else changed.
Driver: `extreme_v2.py` (plans in `bench-run/wind-tunnel/v2-plan*.json`, results in
`bench-run/wind-tunnel/extreme-progress-v2.jsonl`, git-ignored). Tables: `summarize_v2.py`. Mesh table:
`mesh_sizes.py`. Every number below is read from those files. The machine was not idle and was not controlled;
the same input can differ by 20 s or more between runs (Part B1 margin rule). Times in seconds; "simulated time
reached" is the last `Time =` of the solver log (the run ends at 150); time steps are the `deltaT` lines of the
solver log. "corner arc length" is the length of one corner arc (`-` when the corner is 0); "shortest piece" is
the shortest line or arc of the outline (what `min_edge` is compared with). The old survey column gives the
number, outcome and time of the same knob values in `extreme-progress.jsonl` (old setup).

### Part A

| label | aspect/corner/splitter/angle | outcome | wall-clock run_trial (s) | simulated time reached | smallest time step | last time step | corner arc length | shortest piece | old survey | cause |
|---|---|---|---|---|---|---|---|---|---|---|
| A08 0.5/1/3/30 | 0.5/1/3/30 | did not settle | 61.4 | 150 | 0.00428 | 0.0126 | 0.39270 | 0.08000 | #8 did not settle 120 s | cd rule: the means of the two halves differ by 0.0893125, more than 2% of the whole mean 4.10843 |
| A10 3/0/0/30 | 3/0/0/30 | did not settle | 57.7 | 150 | 0.00371 | 0.0134 | - | 1.00000 | #10 did not settle 107 s | cd rule: the means of the two halves differ by 0.425954, more than 2% of the whole mean 5.2409 |
| A12 3/0/3/30 | 3/0/3/30 | did not settle | 70.4 | 150 | 0.00271 | 0.00972 | - | 0.08000 | #12 did not settle 129 s | cd rule: the means of the two halves differ by 1.52797, more than 2% of the whole mean 7.65749 |
| A14 3/1/0/30 | 3/1/0/30 | did not settle | 56.5 | 150 | 0.00599 | 0.0119 | 0.78540 | 0.78540 | #14 did not settle 105 s | cd rule: the means of the two halves differ by 0.0683333, more than 2% of the whole mean 3.30774 |
| A04 0.5/0/3/30 | 0.5/0/3/30 | did not settle | 78.2 | 150 | 0.00323 | 0.00818 | - | 0.08000 | #4 time limit 140 s | cd rule: the means of the two halves differ by 0.130852, more than 2% of the whole mean 4.7072 |
| A21 1.75/0.001/1.5/15 | 1.75/0.001/1.5/15 | time limit | 140.4 | 5.26667 | 3.11e-05 | 0.00014 | 0.00079 | 0.00079 | #21 time limit 140 s | the solver was still running at the time limit |
| A22 1.75/0.01/1.5/15 | 1.75/0.01/1.5/15 | time limit | 140.5 | 54.7722 | 0.000395 | 0.00179 | 0.00785 | 0.00785 | #22 time limit 140 s | the solver was still running at the time limit |
| A23 1.75/0.999/1.5/15 | 1.75/0.999/1.5/15 | time limit | 140.5 | 65.8658 | 0.000336 | 0.00248 | 0.74507 | 0.00100 | #23 time limit 140 s | the solver was still running at the time limit |
| A31 1.75/0.5/1.5/29.97 | 1.75/0.5/1.5/29.97 | settled | 88.4 | 150 | 0.00446 | 0.00877 | 0.39270 | 0.08000 | #31 time limit 140 s |  |
| A16 3/1/3/30 | 3/1/3/30 | settled | 92.6 | 150 | 0.00306 | 0.00948 | 0.74536 | 0.08000 | #16 settled 150 s |  |
| A24 1.75/0.99/1.5/15 | 1.75/0.99/1.5/15 | settled | 71.7 | 150 | 0.00431 | 0.0122 | 0.74251 | 0.01000 | #24 settled 157 s |  |

### Part B1 (angle)

| label | aspect/corner/splitter/angle | outcome | wall-clock run_trial (s) | simulated time reached | smallest time step | last time step | corner arc length | shortest piece | cause |
|---|---|---|---|---|---|---|---|---|---|
| B1 0.5/1/3/25 | 0.5/1/3/25 | settled | 64.2 | 150 | 0.00355 | 0.0128 | 0.39270 | 0.08000 |  |
| B1 3.0/0/0/25 | 3/0/0/25 | did not settle | 91.8 | 150 | 0.00384 | 0.00828 | - | 1.00000 | cd rule: the means of the two halves differ by 0.147549, more than 2% of the whole mean 4.44933 |
| B1 3.0/0/3/25 | 3/0/3/25 | did not settle | 96.0 | 150 | 0.00289 | 0.0112 | - | 0.08000 | cd rule: the means of the two halves differ by 0.155527, more than 2% of the whole mean 6.06709 |
| B1 3.0/1/0/25 | 3/1/0/25 | settled | 78.6 | 150 | 0.00599 | 0.0127 | 0.78540 | 0.78540 |  |
| B1 0.5/0/3/25 | 0.5/0/3/25 | settled | 82.6 | 150 | 0.00374 | 0.0151 | - | 0.08000 |  |
| B1 0.5/1/3/20 | 0.5/1/3/20 | settled | 57.8 | 150 | 0.00495 | 0.013 | 0.39270 | 0.08000 |  |
| B1 3.0/0/0/20 | 3/0/0/20 | did not settle | 74.6 | 150 | 0.00346 | 0.0103 | - | 1.00000 | cd rule: the means of the two halves differ by 0.105059, more than 2% of the whole mean 3.79321 |
| B1 3.0/0/3/20 | 3/0/3/20 | did not settle | 79.4 | 150 | 0.00396 | 0.0112 | - | 0.08000 | cd rule: the means of the two halves differ by 0.340561, more than 2% of the whole mean 4.8749 |
| B1 3.0/1/0/20 | 3/1/0/20 | settled | 69.7 | 150 | 0.0054 | 0.0135 | 0.78540 | 0.78540 |  |
| B1 0.5/0/3/20 | 0.5/0/3/20 | settled | 80.6 | 150 | 0.00375 | 0.0139 | - | 0.08000 |  |
| B1 3.0/0/0/15 | 3/0/0/15 | settled | 54.7 | 150 | 0.00442 | 0.0125 | - | 1.00000 |  |
| B1 3.0/0/3/15 | 3/0/3/15 | settled | 66.7 | 150 | 0.00336 | 0.0119 | - | 0.08000 |  |
| B1 3.0/0/0/10 | 3/0/0/10 | settled | 61.3 | 150 | 0.00505 | 0.0145 | - | 1.00000 |  |
| B1 3.0/0/3/10 | 3/0/3/10 | did not settle | 87.5 | 150 | 0.00444 | 0.011 | - | 0.08000 | cl_amp rule: the amplitudes of the two halves differ by 0.239453, more than the limit 0.235637 |
| B1 0.5/1/3/15 | 0.5/1/3/15 | settled | 50.0 | 150 | 0.00478 | 0.0143 | 0.39270 | 0.08000 |  |
| B1 3.0/1/0/15 | 3/1/0/15 | settled | 52.7 | 150 | 0.00599 | 0.0132 | 0.78540 | 0.78540 |  |
| B1 0.5/0/3/15 | 0.5/0/3/15 | settled | 61.3 | 150 | 0.0039 | 0.0123 | - | 0.08000 |  |

### Part B2 (corner)

| label | aspect/corner/splitter/angle | outcome | wall-clock run_trial (s) | simulated time reached | smallest time step | last time step | corner arc length | shortest piece | cause |
|---|---|---|---|---|---|---|---|---|---|
| B2 1.75/0.005/1.5/15 | 1.75/0.005/1.5/15 | time limit | 140.4 | 23.3669 | 0.000183 | 0.000999 | 0.00393 | 0.00393 | the solver was still running at the time limit |
| B2 1.75/0.02/1.5/15 | 1.75/0.02/1.5/15 | time limit | 140.4 | 134.508 | 0.000917 | 0.00523 | 0.01571 | 0.01571 | the solver was still running at the time limit |
| B2 1.75/0.05/1.5/15 | 1.75/0.05/1.5/15 | settled | 80.7 | 150 | 0.00253 | 0.0102 | 0.03927 | 0.03927 |  |
| B2 1.75/0.95/1.5/15 | 1.75/0.95/1.5/15 | settled | 65.3 | 150 | 0.00599 | 0.0141 | 0.73113 | 0.05000 |  |
| B2 1.75/0.98/1.5/15 | 1.75/0.98/1.5/15 | settled | 70.8 | 150 | 0.00595 | 0.0118 | 0.73967 | 0.02000 |  |
| B2 1.75/0.995/1.5/15 | 1.75/0.995/1.5/15 | settled | 74.5 | 150 | 0.00218 | 0.0123 | 0.74394 | 0.00500 |  |
| B2 0.5/0.02/1.5/15 | 0.5/0.02/1.5/15 | time limit | 140.4 | 55 | 0.000409 | 0.0019 | 0.00785 | 0.00785 | the solver was still running at the time limit |
| B2 3/0.02/1.5/15 | 3/0.02/1.5/15 | time limit | 140.4 | 124.676 | 0.000858 | 0.00427 | 0.01571 | 0.01571 | the solver was still running at the time limit |
| B2 0.5/0.98/1.5/15 | 0.5/0.98/1.5/15 | settled | 68.5 | 150 | 0.00218 | 0.0116 | 0.38485 | 0.01000 |  |
| B2 3/0.98/1.5/15 | 3/0.98/1.5/15 | settled | 69.6 | 150 | 0.00595 | 0.0119 | 0.73967 | 0.02000 |  |
| B2 1.75/0.03/1.5/15 | 1.75/0.03/1.5/15 | time limit | 140.3 | 136.066 | 0.00137 | 0.00549 | 0.02356 | 0.02356 | the solver was still running at the time limit |
| B2 1.75/0.998/1.5/15 | 1.75/0.998/1.5/15 | time limit | 140.3 | 145.029 | 0.000693 | 0.00485 | 0.74479 | 0.00200 | the solver was still running at the time limit |
| B2 0.5/0.05/1.5/15 | 0.5/0.05/1.5/15 | settled | 102.9 | 150 | 0.00119 | 0.00578 | 0.01963 | 0.01963 |  |
| B2 0.5/0.1/1.5/15 | 0.5/0.1/1.5/15 | settled | 85.2 | 150 | 0.00272 | 0.00901 | 0.03927 | 0.03927 |  |
| B2 0.5/0.995/1.5/15 | 0.5/0.995/1.5/15 | settled | 111.6 | 150 | 0.000394 | 0.00699 | 0.39074 | 0.00250 |  |


## Mesh: smallest cell edge against the shortest piece (aspect/corner as listed, splitter 1.5, angle 15)

Made by the model's own mesher with the settings unchanged; no solver run.

| aspect | corner | shortest piece | cells | smallest cell edge |
|---|---|---|---|---|
| 1.75 | 0.001 | 0.00079 | 10311 | 0.00038 |
| 1.75 | 0.005 | 0.00393 | 10285 | 0.00191 |
| 1.75 | 0.01 | 0.00785 | 10341 | 0.00383 |
| 1.75 | 0.02 | 0.01571 | 10303 | 0.00765 |
| 1.75 | 0.03 | 0.02356 | 10319 | 0.01148 |
| 1.75 | 0.05 | 0.03927 | 10360 | 0.01913 |
| 1.75 | 0.5 | 0.08000 | 10267 | 0.02697 |
| 1.75 | 0.95 | 0.05000 | 10230 | 0.02500 |
| 1.75 | 0.98 | 0.02000 | 10217 | 0.02000 |
| 1.75 | 0.99 | 0.01000 | 10233 | 0.01000 |
| 1.75 | 0.995 | 0.00500 | 10225 | 0.00500 |
| 1.75 | 0.998 | 0.00200 | 10217 | 0.00200 |
| 1.75 | 0.999 | 0.00100 | 10231 | 0.00100 |
| 0.5 | 0.02 | 0.00785 | 10103 | 0.00383 |
| 3 | 0.02 | 0.01571 | 10571 | 0.00765 |
| 0.5 | 0.98 | 0.01000 | 10031 | 0.01000 |
| 3 | 0.98 | 0.02000 | 10541 | 0.02000 |

## Readings (from the tables above)

- Angle 30: the five combinations of the old angle-30 failures do not time out any more (the four that did not
  settle stop after 56 to 78 s; run 4 now fails to settle in 78.2 s instead of the time limit; run 31 at 29.97
  settles in 88.4 s). Runs 16 and 24 settle in 92.6 s and 71.7 s.
- Angle at the five worst combinations (aspect/corner/splitter): 3/0/0 and 3/0/3 do not settle at 30, 25 and 20,
  settle at 15 (54.7 s, 66.7 s) and 3/0/0 settles at 10 (61.3 s). 3/0/3 does not settle at 10 (cl_amp rule, 0.239453
  against the limit 0.235637, 87.5 s); the old survey settled it at angle 0 (92 s, old setup). 0.5/1/3, 3/1/0 and
  0.5/0/3 settle at 25, 20 and 15 (all at most 82.6 s). Settling is therefore not monotonic in the angle.
- Corner, aspect 1.75, splitter 1.5, angle 15: time limit at corner 0.001, 0.005, 0.01, 0.02, 0.03 and at 0.998,
  0.999; settled at 0.05 (80.7 s) and at 0.95, 0.98, 0.99, 0.995 (65.3 to 74.5 s). The solver's smallest time step
  at the limit runs falls with the smallest cell edge of the mesh (mesh table), while the cell count stays near
  10 000 in every case.
