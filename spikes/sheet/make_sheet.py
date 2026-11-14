"""Spike (wind-tunnel task 7.1): make a synthetic picture sheet to check that Dr. Kiro's file tool shows all cells of
a PNG sheet. Scratch file: nothing outside spikes/ uses it.

    uv run --project bench python spikes/sheet/make_sheet.py [output-path]

THE PNG IS A SYNTHETIC TEST FIXTURE, NOT A RESULT. It shows no measurement and no flow.

Layout (the proposed one): 6 cells in 2 rows of 3, each cell 400 x 200, 4 pixel black gaps between cells
(sheet 1208 x 404). Each cell has its own background colour, a white dot at its own position and a number 1 to 6
drawn with the small bitmap font below (for this check only). The expected content of each cell, in reading order
(left to right, top to bottom), is printed.
"""
import sys
from pathlib import Path

from bench.pictures import encode_png

CELL_W, CELL_H, GAP, COLS, ROWS = 400, 200, 4, 3, 2
SHEET_W = COLS * CELL_W + (COLS - 1) * GAP
SHEET_H = ROWS * CELL_H + (ROWS - 1) * GAP
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DOT_RADIUS = 18
SCALE = 10  # each font pixel is SCALE x SCALE pixels: digits are 50 x 70

# (colour name, rgb, dot position name, dot centre inside the cell)
CELLS = [
    ("red", (200, 40, 40), "top-left", (50, 45)),
    ("green", (40, 160, 60), "bottom-right", (350, 155)),
    ("blue", (40, 80, 200), "top-right", (350, 45)),
    ("yellow", (220, 180, 30), "bottom-left", (50, 155)),
    ("purple", (140, 50, 170), "top-centre", (200, 40)),
    ("grey", (120, 120, 120), "bottom-centre", (200, 160)),
]

FONT = {
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["####.", "....#", "....#", ".###.", "....#", "....#", "####."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": [".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."],
}


def cell_origin(index: int) -> tuple[int, int]:
    row, col = divmod(index, COLS)
    return col * (CELL_W + GAP), row * (CELL_H + GAP)


def build() -> list[list[tuple[int, int, int]]]:
    pixels = [[BLACK] * SHEET_W for _ in range(SHEET_H)]
    for i, (_, rgb, _, (dx, dy)) in enumerate(CELLS):
        ox, oy = cell_origin(i)
        for y in range(CELL_H):
            for x in range(CELL_W):
                colour = rgb
                if (x - dx) ** 2 + (y - dy) ** 2 <= DOT_RADIUS**2:
                    colour = WHITE
                pixels[oy + y][ox + x] = colour
        glyph = FONT[str(i + 1)]
        gx, gy = ox + (CELL_W - 5 * SCALE) // 2, oy + (CELL_H - 7 * SCALE) // 2
        for r, line in enumerate(glyph):
            for c, ch in enumerate(line):
                if ch == "#":
                    for y in range(SCALE):
                        for x in range(SCALE):
                            pixels[gy + r * SCALE + y][gx + c * SCALE + x] = WHITE
    return pixels


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("check-sheet.png")
    out.write_bytes(encode_png(build()))
    print(f"wrote {out}: {SHEET_W}x{SHEET_H}, {len(CELLS)} cells (synthetic test fixture, not a result)")
    for i, (name, _, dot, _) in enumerate(CELLS):
        print(f"  cell {i + 1}: {name} background, white dot {dot}, number {i + 1}")


if __name__ == "__main__":
    main()
