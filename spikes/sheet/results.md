# Sheet reading check (wind-tunnel task 7.1)

Date: 2026-11-14 (hook log time, UTC). Kiro CLI 3.3.0 on macOS. Run once by the builder with
`kiro-cli chat --agent fake-tester --no-interactive --trust-workspace --trust-tools=fs_read "<question>"` from
`bench-run/fake/lab`, with `BENCH_SESSION_CONFIG` and `BENCH_HOOK_LOG` exported (as in `spikes/gif/results.md`).

The sheet is a **synthetic test fixture, not a result**: it shows no measurement and no flow. It is made by
`spikes/sheet/make_sheet.py`; the PNG was copied to `bench-run/fake/lab/pictures/check-sheet.png` (git-ignored).

## Layout and size

6 cells in 2 rows of 3, each cell 400 x 200, 4 pixel black gaps between cells. Sheet 1208 x 404 PNG, 4,987 bytes.
Each cell has its own background colour, a white dot at its own position, and a number 1 to 6 drawn with a bitmap
font in the script.

## Question

"Open the picture file pictures/check-sheet.png. It is one sheet made of six cells in 2 rows of 3. For each of the six
cells in reading order (left to right, top to bottom), report the background colour, the position of the white dot in
the cell, and the number drawn in the cell. Report only what you can see in the file; if you cannot see a cell, say
so." The question gives none of the expected values.

## Answers and expected values

| Cell | Answer: background | Answer: dot | Answer: number | Expected (script) | Correct |
|---|---|---|---|---|---|
| 1 (top left) | Red | Top-left corner | 1 | red, top-left, 1 | yes |
| 2 (top middle) | Green | Lower right, near the bottom-right corner | 2 | green, bottom-right, 2 | yes |
| 3 (top right) | Blue | Top-right corner | 3 | blue, top-right, 3 | yes |
| 4 (bottom left) | Yellow/gold | Bottom-left corner | 4 | yellow, bottom-left, 4 | yes |
| 5 (bottom middle) | Purple | Top centre, just above the number | 5 | purple, top-centre, 5 | yes |
| 6 (bottom right) | Gray | Bottom centre, just below the number | 6 | grey, bottom-centre, 6 | yes |

The agent said all six cells are visible, that the file reader returned the image and its metadata (png, 1208x404,
4987 bytes), and that it ran no other tools.

## Hook log lines for the read (`bench-run/fake/hook-log.jsonl`)

```
{"ts": "2026-11-14T00:00:28Z", "phase": "pre", "tool_name": "read_file", "tool_input": {"path": ".../bench-run/fake/lab/pictures/check-sheet.png", "offset": null, "limit": null}}
{"ts": "2026-11-14T00:00:28Z", "phase": "post", "tool_name": "read_file", "tool_input": {"path": ".../bench-run/fake/lab/pictures/check-sheet.png", "offset": null, "limit": null}}
```

No `refused` entry. (The path prefix is shortened here.)

## Verdict

PASS. All six cells correct (colour, dot position and number). The layout and the size are unchanged.
