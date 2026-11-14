"""wind-tunnel task 9.3: the picture sheet (Requirement 9)."""

import dataclasses
import struct
import zlib

import numpy as np
import pytest
from bench.pictures import check_picture
from wind_tunnel_model.settings import Settings

from wind_tunnel.picture import (
    COLOUR_TABLE,
    GAP_COLOUR,
    MASK_COLOUR,
    picture_sheet,
)

PICTURE = Settings.load().picture


def decode_png(data: bytes) -> np.ndarray:
    """Test-side decoder for the 8-bit RGB, filter 0 PNG that encode_png writes."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, width, height = 8, b"", 0, 0
    while pos < len(data):
        (size,) = struct.unpack(">I", data[pos : pos + 4])
        kind, body = data[pos + 4 : pos + 8], data[pos + 8 : pos + 8 + size]
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
    return np.stack(rows)


def make_frames(picture=PICTURE, seed: int = 7):
    rng = np.random.default_rng(seed)
    shape = (picture.cell_height, picture.cell_width)
    frames = []
    for _ in range(picture.frames):
        omega = rng.uniform(-2 * picture.vorticity_limit, 2 * picture.vorticity_limit, shape)
        mask = rng.random(shape) < 0.05
        frames.append((omega, mask))
    return frames


def expected_cell(omega, mask, limit):
    index = np.rint(254 * (np.clip(omega, -limit, limit) + limit) / (2 * limit)).astype(int)
    cell = COLOUR_TABLE[index].copy()
    cell[mask] = MASK_COLOUR
    return cell


def test_sheet_passes_the_picture_check() -> None:
    check_picture("image/png", picture_sheet(make_frames(), PICTURE))


def test_sheet_size_with_the_settings_file() -> None:
    pixels = decode_png(picture_sheet(make_frames(), PICTURE))
    assert pixels.shape == (404, 1208, 3)


def test_cell_k_equals_the_colours_of_frame_k_and_gaps_are_the_gap_colour() -> None:
    frames = make_frames()
    pixels = decode_png(picture_sheet(frames, PICTURE))
    covered = np.zeros(pixels.shape[:2], dtype=bool)
    for k, (omega, mask) in enumerate(frames):
        row, column = divmod(k, PICTURE.columns)
        top = row * (PICTURE.cell_height + PICTURE.gap)
        left = column * (PICTURE.cell_width + PICTURE.gap)
        window = (slice(top, top + PICTURE.cell_height), slice(left, left + PICTURE.cell_width))
        assert np.array_equal(pixels[window], expected_cell(omega, mask, PICTURE.vorticity_limit))
        covered[window] = True
    assert np.all(pixels[~covered] == GAP_COLOUR)
    assert (~covered).sum() == 404 * 1208 - 6 * 400 * 200


def test_colour_table_has_255_distinct_entries_without_gap_or_mask_colour() -> None:
    assert COLOUR_TABLE.shape == (255, 3)
    entries = {tuple(int(v) for v in e) for e in COLOUR_TABLE}
    assert GAP_COLOUR not in entries
    assert MASK_COLOUR not in entries
    assert tuple(COLOUR_TABLE[127]) == (255, 255, 255)


def test_same_field_gives_the_same_bytes() -> None:
    assert picture_sheet(make_frames(), PICTURE) == picture_sheet(make_frames(), PICTURE)


def test_gap_zero_gives_1200_by_400() -> None:
    picture = dataclasses.replace(PICTURE, gap=0)
    pixels = decode_png(picture_sheet(make_frames(picture), picture))
    assert pixels.shape == (400, 1200, 3)


def test_wrong_frame_count_or_shape_is_refused() -> None:
    with pytest.raises(ValueError, match="frames"):
        picture_sheet(make_frames()[:-1], PICTURE)
    frames = make_frames()
    frames[2] = (np.zeros((3, 3)), np.zeros((3, 3), dtype=bool))
    with pytest.raises(ValueError, match="frame 2"):
        picture_sheet(frames, PICTURE)
