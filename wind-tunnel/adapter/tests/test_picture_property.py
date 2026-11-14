"""wind-tunnel task 9.4: property test for the picture sheet.

**Property 14: Picture sheet mapping and file**
**Validates: Requirements 9.1, 9.2, 9.3, 9.4**
"""

import dataclasses
import struct
import zlib

import numpy as np
from bench.pictures import check_picture
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra import numpy as hnp
from wind_tunnel_model.settings import Settings

from wind_tunnel.picture import (
    COLOUR_TABLE,
    GAP_COLOUR,
    MASK_COLOUR,
    colour_index,
    picture_sheet,
    sheet_size,
)

BASE = Settings.load().picture

finite = st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False)
limits = st.floats(min_value=1e-3, max_value=1e4, allow_nan=False, allow_infinity=False)


def decode_png(data: bytes) -> tuple[np.ndarray, list[bytes]]:
    """Test-side decoder: the pixels (height, width, 3) and the chunk types in file order."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, width, height, kinds = 8, b"", 0, 0, []
    while pos < len(data):
        (size,) = struct.unpack(">I", data[pos : pos + 4])
        kind, body = data[pos + 4 : pos + 8], data[pos + 8 : pos + 8 + size]
        kinds.append(kind)
        if kind == b"IHDR":
            width, height = struct.unpack(">II", body[:8])
        elif kind == b"IDAT":
            idat += body
        pos += 12 + size
    raw = zlib.decompress(idat)
    stride = 1 + width * 3
    rows = []
    for y in range(height):
        line = raw[y * stride : (y + 1) * stride]
        assert line[0] == 0
        rows.append(np.frombuffer(line[1:], dtype=np.uint8).reshape(width, 3))
    return np.stack(rows), kinds


@st.composite
def layouts_and_frames(draw):
    rows = draw(st.integers(1, 3))
    columns = draw(st.integers(1, 3))
    picture = dataclasses.replace(
        BASE,
        rows=rows,
        columns=columns,
        frames=rows * columns,
        cell_width=draw(st.integers(1, 6)),
        cell_height=draw(st.integers(1, 6)),
        gap=draw(st.integers(0, 3)),
        vorticity_limit=draw(limits),
    )
    shape = (picture.cell_height, picture.cell_width)
    frames = [
        (draw(hnp.arrays(np.float64, shape, elements=finite)), draw(hnp.arrays(np.bool_, shape)))
        for _ in range(picture.frames)
    ]
    return picture, frames


@settings(max_examples=100, deadline=None)
@given(values=st.lists(finite, min_size=2, max_size=40), limit=limits)
def test_colour_index_is_non_decreasing_and_clipped(values, limit) -> None:
    ordered = np.sort(np.array(values))
    index = colour_index(ordered, limit)
    assert index.min() >= 0
    assert index.max() <= 254
    assert np.all(np.diff(index) >= 0)


def test_mask_and_gap_colours_are_not_in_the_table() -> None:
    entries = {tuple(int(v) for v in e) for e in COLOUR_TABLE}
    assert MASK_COLOUR not in entries
    assert GAP_COLOUR not in entries


@settings(max_examples=100, deadline=None)
@given(case=layouts_and_frames())
def test_sheet_mapping_layout_and_file(case) -> None:
    picture, frames = case
    data = picture_sheet(frames, picture)

    check_picture("image/png", data)
    pixels, kinds = decode_png(data)
    assert set(kinds) <= {b"IHDR", b"IDAT", b"IEND"}

    width = picture.columns * picture.cell_width + (picture.columns - 1) * picture.gap
    height = picture.rows * picture.cell_height + (picture.rows - 1) * picture.gap
    assert sheet_size(picture) == (width, height)
    assert pixels.shape == (height, width, 3)

    covered = np.zeros(pixels.shape[:2], dtype=bool)
    for k, (omega, mask) in enumerate(frames):
        row, column = divmod(k, picture.columns)
        top = row * (picture.cell_height + picture.gap)
        left = column * (picture.cell_width + picture.gap)
        window = (slice(top, top + picture.cell_height), slice(left, left + picture.cell_width))
        limit = picture.vorticity_limit
        index = np.rint(254 * (np.clip(omega, -limit, limit) + limit) / (2 * limit)).astype(int)
        expected = COLOUR_TABLE[index].copy()
        expected[mask] = MASK_COLOUR
        assert np.array_equal(pixels[window], expected)
        covered[window] = True
    assert np.all(pixels[~covered] == GAP_COLOUR)

    assert picture_sheet(frames, picture) == data
