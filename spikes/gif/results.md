# GIF reading check

Date: 2026-11-13. Kiro CLI 3.3.0 on macOS (Apple Silicon). Run by the builder with `kiro-cli chat --no-interactive`
from `bench-run/fake/lab`, agent `fake-tester` (tools: read, write, bench), hooks present and firing
(`bench-run/fake/hook-log.jsonl`: `file_search` and `read_file` of `pictures/check.gif`, phases `pre` and `post`,
no `refused` entry). The bench MCP server raised no visible error.

File: `spikes/gif/check.gif`, 12 frames, 480x240, 22,893 bytes (made by `make_gif.py`; frame 1 red with a dot at
the left and the number 1).

## Questions and answers (summary)

1. "What do you see? Are there several frames? How many?": the agent described one still image (red background,
   white dot at the top left, a large 1). It said the file reader returned metadata (GIF, 480x240, 22,893 bytes)
   and one still image, probably the first frame, and that it could not tell whether there are several frames or
   how many.
2. "Table for frames 1 to 12: background colour, dot position, number": frame 1 correct (red, left, 1); frames 2
   to 12 "not visible". It said the tool returned a single image with no frame count or animation data.
3. The question about frame 7 alone was not asked: question 2 already showed that only frame 1 is delivered.

## Verdict

FAIL. Dr. Kiro's file tool delivers the first frame of an animated GIF and the file's size metadata. The motion and
frames 2 to 12 do not reach the agent. Wind-tunnel requirements 9.7 to 9.9 apply: the builder does not switch the
picture format by itself; this goes back to the user and the spec.
