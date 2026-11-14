# Where the time of one wind-tunnel run goes (task 14.4 (c), measurement only)

Instrument: `timing.py` (wraps the stage functions of the adapter; every wrapper calls the original with the
same arguments and returns its result unchanged; the deadline logic, the 140 s limit, ranges, mesh and setup are
the adapter's own). Raw output: `circle150.json`, `run16a.json`, `run24a.json`. One run per input, one at a
time, on the local Mac. The machine was not idle (load average 6 to 8 during the runs, Kiro and system
processes busy); this was not controlled. Seconds.

| Stage | circle, Re 150 | run 16 (3, 1, 3, 30) | run 24 (1.75, 0.99, 1.5, 15) |
|---|---|---|---|
| outline | 0.00 | 0.00 | 0.00 |
| case rendering | 0.03 | 0.04 | 0.04 |
| mesh | 0.38 | 0.33 | 0.22 |
| container run (`docker run`) | 105.12 | 139.66 (killed at the limit) | 115.98 |
| solver log: simulated time reached | 150.0 | 139.49 | 150.0 |
| solver log: wall-clock of the last step (`ClockTime`) | 103.0 | 139 | 114.0 |
| force-file parse | 0.04 | not reached | 0.03 |
| estimators | 0.12 | not reached | 0.13 |
| settle | 0.00 | not reached | 0.00 |
| vorticity parse (6 files) | 0.62 | not reached | 0.63 |
| picture | 0.30 | not reached | 0.29 |
| remove the case folder (success) | 15.13 | not run | 15.05 |
| prune the case folder (failure) | not run | 20.45 | not run |
| case folder size before removal | 4.90 GB | not measured (disk free fell from 9.6 GB to 3.97 GB during the run) | 5.10 GB |
| instrument overhead (`du`, outside the stages) | about 1.8 | none | 2.4 |
| `run_trial` total | 123.63 | 161.14 | 134.85 |
| outcome | settled | timeout | settled |

- The three container steps before the solver (`gmshToFoam`, `changeDictionary`, `decomposePar`) and the start of
  the solver start in the same second in the log header; container start-up, preparation and exit together are
  about 2 s (container run minus last step: 2.1 s circle, 2.0 s run 24).
- Run 24: the case folder was 5.10 GB, of which `processor0..2` were 1.71, 1.67 and 1.67 GB, the sampled output
  30 MB, the mesh file 1.5 MB.
- Post-processing after the container (force parse, estimators, settle, vorticity, picture): 1.1 s in both
  settled runs.
- The free disk was 9.6 to 9.8 GB before each run, not 100 GB.
