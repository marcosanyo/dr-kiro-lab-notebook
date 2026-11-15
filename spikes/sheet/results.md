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


# Sheet reading check on a real sheet (wind-tunnel task 14.5)

Date: 2026-11-15 (UTC, 02:33). Kiro CLI on macOS, run once by the builder with the same command line as task 7.1
(`kiro-cli chat --agent fake-tester --no-interactive --trust-workspace --trust-tools=fs_read "<question>"` from
`bench-run/fake/lab`, with `BENCH_SESSION_CONFIG` and `BENCH_HOOK_LOG` exported).

This is a **recorded observation**. The answers are not judged against a ground truth.

## The sheet

One trial of the circle (`aspect` 1, `corner` 1, `splitter` 0, `angle` 0) through `WindAdapter`, default settings,
`vorticity_limit = 5.0` (fixed by task 14.4), seed 2 (the seed is unused by the result; it only names the case
folder). Measured values of that trial: `cd` 1.410, `cl_amp` 0.561, `strouhal` 0.188, `shedding` 1.
It passes `bench.pictures.check_picture` (image/png). Written to `bench-run/fake/lab/pictures/real-sheet.png`
(git-ignored).

- Size: 1208 x 404 pixels, 131,158 bytes (the size of the settings: 3 x 400 + 2 x 4, 2 x 200 + 1 x 4).
- SHA-256: `04c1bedc4c3a35924b0a92ccfb598e6133e7484c4c2a75d3700c67f92b79f4c8`

## Question

"Open the picture file pictures/real-sheet.png. It is one sheet made of six cells in 2 rows of 3. For each of the
six cells in reading order (left to right, top to bottom), say where the vortices are, and say whether the pattern
changes between the cells. Report only what you can see in the file; if you cannot see a cell, say so."
The question does not say what a vortex looks like or what to expect.

## Answer of the agent (verbatim)

> I opened pictures/real-sheet.png. It is 1208x404 and shows six cells in 2 rows of 3, separated by black lines. All six cells are visible.
>
> Each cell shows a grey circular cylinder on the left. Blue (one sign of vorticity) and red (the opposite sign) vortex patches stream off it to the right. The cells have no axis labels or numbers, so positions below are approximate and relative to the cell.
>
> **Row 1**
> 1. **Cell 1 (top left):** Thin blue and red layers hug the top and bottom of the cylinder. A blue patch sits just downstream at about x≈150, above the centerline. A red patch follows at about x≈215, slightly below the centerline. A fainter blue patch is at about x≈295, and a red one is cut off at the right edge at about x≈380.
> 2. **Cell 2 (top middle):** The pattern is the same. A blue patch is at about x≈570 in sheet coordinates, and a red patch is just behind the cylinder, below the centerline. A red patch is at about x≈670, a faint blue patch at about x≈735, and a faint red edge at the far right. The red patch near the cylinder looks stronger here than in cell 1.
> 3. **Cell 3 (top right):** The pattern is again the same. Blue is above and red below near the cylinder. A red patch is at about x≈1085 in sheet coordinates, and a faint blue patch is at about x≈1165. The near-cylinder red patch looks strong.
>
> **Row 2**
> 4. **Cell 4 (bottom left):** A blue patch is above the centerline just behind the cylinder, and a red patch is below it. Farther right there is a faint blue patch at about x≈230, a red patch at about x≈305, and a blue patch at the right edge at about x≈385.
> 5. **Cell 5 (bottom middle):** A strong blue patch is directly behind the cylinder, with red below it. A faint blue patch is at about x≈660 and a red patch at about x≈750. The near-cylinder blue patch looks larger than in the other cells.
> 6. **Cell 6 (bottom right):** A blue patch is just behind the cylinder, with red below and behind it. A blue patch is at about x≈1095 and a red patch at the right edge at about x≈1180.
>
> **Does the pattern change between cells?**
> The overall pattern is the same in all six cells. It is an alternating blue and red wake behind the cylinder, with blue shed from the top and red from the bottom. That is a vortex street.
>
> The phase differs between cells. The downstream blue and red patches sit at slightly different x positions, and the near-cylinder patches differ in size and strength. For example, red is strongest near the cylinder in cells 2 and 3, and blue is strongest there in cell 5. This is what a vortex street looks like at different moments in its shedding cycle.
>
> I judged all of this by eye. I did not measure anything, so the positions are rough.

## Observation

The agent saw all six cells in 2 rows of 3, described vortex positions in each, and said the pattern is alternating
in every cell with differences in phase. Not judged against a ground truth. The picture format, layout and size were
not changed.
