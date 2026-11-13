"""Spike: make a 12-frame GIF whose frames differ clearly, to check that Dr. Kiro's file tool shows an animation
and not only its first frame. Scratch file: nothing outside spikes/ uses it.

    uv run --with pillow python spikes/gif/make_gif.py [output-path]

Each frame has a background colour (4 colours in turn), a white dot that moves from left to right, and the frame
number written in the middle. Frame 1 and frame 12 differ in colour, dot position and number.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FRAMES = 12
WIDTH, HEIGHT = 480, 240
COLOURS = [(200, 40, 40), (40, 160, 60), (40, 80, 200), (220, 180, 30)]
COLOUR_NAMES = ["red", "green", "blue", "yellow"]
DURATION_MS = 200


def frame(index: int) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), COLOURS[index % len(COLOURS)])
    draw = ImageDraw.Draw(image)
    x = 30 + index * (WIDTH - 60) // (FRAMES - 1)
    draw.ellipse((x - 14, 30, x + 14, 58), fill=(255, 255, 255))
    draw.text((WIDTH // 2, HEIGHT // 2 + 20), str(index + 1), fill=(255, 255, 255),
              font=ImageFont.load_default(size=80), anchor="mm")
    return image


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("check.gif")
    images = [frame(i) for i in range(FRAMES)]
    images[0].save(out, save_all=True, append_images=images[1:], duration=DURATION_MS, loop=0)
    print(f"wrote {out}: {FRAMES} frames")
    for i in range(FRAMES):
        print(f"  frame {i + 1}: {COLOUR_NAMES[i % len(COLOUR_NAMES)]} background")


if __name__ == "__main__":
    main()
