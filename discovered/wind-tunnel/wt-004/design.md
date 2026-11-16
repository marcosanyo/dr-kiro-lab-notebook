# Design

## Beliefs

Data so far (angle 0 unless noted; a, c, s = aspect, corner, splitter):

| exp | a | c | s | angle | cd | cl_amp | shed |
|---|---|---|---|---|---|---|---|
| E1 | 1 | 0 | 0 | 0 | 1.55 | 0.43 | 1 |
| E1 | 1 | 1 | 0 | 0 | 1.41 | 0.56 | 1 |
| E1 | 1 | 0 | 2 | 0 | 1.39 | 0.63 | 1 |
| E2 | 0.5 | 0 | 0 | 0 | 2.17 | 0.93 | 1 |
| E2 | 2 | 0 | 0 | 0 | 1.34 | 0.21 | 1 |
| E2 | 3 | 0 | 0 | 0 | 1.29 | 0.22 | 1 |
| E3 | 3 | 1 | 0 | 0 | 1.11 | 0.15 | 1 |
| E3 | 3 | 1 | 3 | 0 | 1.02 | 0 | 0 |
| E3 | 3 | 0 | 0 | 8 | 2.01 | 0.98 | 1 |
| E4 | 3 | 1 | 1 | 0 | not settled | | |
| E4 | 3 | 1 | 2 | 0 | 1.03 | 0 | 0 |
| E4 | 2 | 1 | 3 | 0 | 0.99 | 0 | 0 |

- cd falls as aspect rises (2.17, 1.55, 1.34, 1.29), flattening above 2. Shedding amplitude falls with aspect up to 2.
- Rounding corners lowers cd (1.55 to 1.41 at aspect 1; 1.29 to 1.11 at aspect 3) and cl_amp at aspect 3.
- A splitter suppresses shedding only when long enough on a long rounded body (2 works, 1 is near the boundary); on a short square body, 2 did not stop it.
- Angle 8 raises cd, cl_mean and cl_amp strongly. Best point is probably angle 0.
- Steady cd is about 1.0 for the settings found; lowest so far is aspect 2, corner 1, splitter 3 (0.993).

Later data: E5 a1.5 c1 s3: cd 0.994 steady. a1 c1 s3: cd 1.05, sheds (cl_amp 0.41). a2 c1 s3 angle 3: cd 1.012, cl_mean -0.197, steady. E6 (angle 0, c1): a2 s2.2 cd 1.003; a1.7 s3 cd 0.993; a2.5 s3 cd 1.004, all steady.
Best point: aspect 1.7, corner 1, splitter 3, angle 0 (cd 0.993, shedding 0). cd is a plateau of about 1.0 in that region.

## Discovered spec

| id | rule | scope | experiments | predictions | status | replaced by |
|---|---|---|---|---|---|---|
| R1 | With corner 0, splitter 0, angle 0, cd falls as aspect rises (2.17 at 0.5, 1.55 at 1, 1.34 at 2, 1.29 at 3), flattening above 2. | aspect 0.5 to 3 | E1, E2 | H1.P1, H1.P2, H2.P1, H2.P2 | validated | |
| R2 | Full corner rounding lowers cd (about 0.14 at aspect 1, 0.18 at aspect 3) and does not stop shedding alone. | corner 0 to 1, splitter 0, angle 0 | E1, E3 | H3.P1, H3.P2 | validated | |
| R3 | With corner 1 and angle 0, a splitter of 2 or more stops shedding for aspect 1.5 to 3. Splitter 1 at aspect 3 does not settle. Aspect 1 still sheds with splitter 3. | aspect 1.5 to 3, corner 1, splitter 2 to 3, angle 0 | E3, E4, E5, E6 | H3.P3, H4.P1, H5.P1 | validated | |
| R4 | A steady body has cd about 0.99 to 1.03 (plateau), lowest near aspect 1.5 to 2 with splitter 3. | corner 1, angle 0, aspect 1.5 to 3, splitter 2 to 3 | E3, E4, E5, E6 | H4.P2, H4.P3, H5.P2, H6.P1, H6.P2, H6.P3 | validated | |
| R5 | A positive angle raises cd and cl_amp; lift is negative for positive angle. At angle 8 on a square aspect 3 body cd is 2.01 and cl_mean 1.64 (sign positive there). At angle 3 on the plated body cd rises 0.02 and cl_mean is -0.20. | angle 3 to 8 | E3, E5 | H5.P3, H5.P4 | partly | |
| R6 | With the plate, cl_mean sign depends on configuration, so lift sign is not fixed by angle alone. | angle 3 plated, angle 8 square | E3, E5 | | observed | |
