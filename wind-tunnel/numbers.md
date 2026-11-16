# Numbers for the README

## Connection time

About 57 hours 30 minutes (the user wrote "57 時間 30 分程度"), **self-reported by the user** (Requirement 16.1).
It is not computed or estimated by the builder. The number is recorded as the user gave it.

- Start: 2026-11-13 23:24:59 +0900, the time of commit `2a8c62a`, which recorded the approval of the requirements.
  The user says the real approval was a few minutes earlier and that no record of the exact time exists, so he aligned
  the start with the commit time.
- End: 2026-11-16 08:55:00 +0900, the creation of session `wt-004` (`builder.log`: "started session wt-004").
- The user reads "the first full session" in Requirement 16.1 as `wt-004`, the session that ran to its end. The
  stopped sessions `wt-001`, `wt-002` and `wt-003` are not counted as the first full session.
- Note: this is wall-clock time. It includes sleep and other work, and is not the sum of working time. The fixes made
  after the three stopped attempts are inside it.

## The recorded session

Source: `sessions/wind-tunnel/wt-004/` (committed as `cbe5d54`). Every figure below is read from that folder.

| Item | Value |
|---|---|
| Session id, seed | `wt-004`, 20261118 |
| End | sealed `ended`: Dr. Kiro ended the session with `end_session` |
| Trials used | 18 of the 24 trials of the budget; budget remaining 6 |
| Experiments, hypotheses | 6 experiments (E1 to E6), 6 hypotheses |
| Record | 69 entries, 41 blobs |
| `bench-verify` | verified (69 entries, 41 blobs) |
| `bench-scan` on `wind-tunnel/lab` and on the sealed folder | no findings |
| Prediction outcomes | 17 outcomes: 16 hits, 1 miss (E5) |
| Trial with all five measurements `not_settled` | 1 (E4, `aspect` 3, `corner` 1, `splitter` 1, `angle` 0) |
| Refusals | 1 (a prediction range with one value, entry 2) |

The pass condition of Requirement 17.3 is the budget used (24 runs) or Dr. Kiro's own `end_session`. This session
passes by the second: 18 of 24 trials were used, and the session ended by Dr. Kiro's own `end_session`. The budget was
not used up.

Stopped attempts before it (not counted as the first full session):

| Session | State | What stopped it |
|---|---|---|
| `wt-001` | not sealed; its state exists only in the git-ignored `bench-run/` state folder | The first `run_experiment` failed because Gmsh ran in a worker thread; the record scan found the words `application` and `image`. |
| `wt-002` | sealed `stopped`, committed `e1c7565`; 3 trials | `bench-mcp` crashed in a new worker thread, in a call 20 s after the previous one. |
| `wt-003` | sealed `stopped`, committed `7c0ab08` | A derived term in a normal refusal stopped it at the first action. |

The fixes: the mesh is made in a child process, 5 words were added to the stop list, and a sweep test scans the
bench's own strings.

## Code size

Non-blank, non-comment lines, counted by `count_lines.py`. Lock files, virtual environments
and caches are not counted.

<!-- code-size:begin -->
- `adapter/`: 1037 lines
- `model/`: 1277 lines
- Total (without test files): 2314 lines
- Test files, counted on their own: `adapter/` 2013 lines, `model/` 1227 lines
<!-- code-size:end -->
