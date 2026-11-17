"""PNG decoding and encoding for the picture sheets, with the standard library only (`zlib`, `struct`).

Used for the enlarged picture of a trial (lab-notebook Requirement 7.9, design N32). Only what the
recorded sheets use is read: 8-bit RGB (colour type 2) or RGBA (colour type 6), without interlacing,
with the five row filters. Any other PNG fails with a NotebookError naming the sheet; nothing is
converted or guessed (rules.md 2). The encoder writes 8-bit RGB or RGBA with filter type 0 on every
row, so the same pixels always give the same bytes.
"""

import struct
import zlib
from dataclasses import dataclass

from notebook.errors import NotebookError

SIGNATURE = b"\x89PNG\r\n\x1a\n"
# Colour type -> channels per pixel. Only 8-bit depth is read.
CHANNELS = {2: 3, 6: 4}


@dataclass(frozen=True)
class Image:
    """Decoded pixels: row-major, `width * channels` bytes per row, no filter bytes."""

    width: int
    height: int
    colour_type: int
    pixels: bytes

    @property
    def channels(self) -> int:
        return CHANNELS[self.colour_type]


def _chunks(data: bytes, where: str) -> list[tuple[bytes, bytes]]:
    """Every chunk of the file as (type, body), with each CRC checked."""
    if data[:8] != SIGNATURE:
        raise NotebookError(where, "the picture is not a PNG file (the signature is wrong)")
    chunks: list[tuple[bytes, bytes]] = []
    position = 8
    while True:
        if position + 8 > len(data):
            raise NotebookError(where, "the PNG file ends inside a chunk header")
        length, kind = struct.unpack(">I4s", data[position : position + 8])
        end = position + 12 + length
        if end > len(data):
            raise NotebookError(where, f"the PNG chunk {kind!r} is longer than the file")
        body = data[position + 8 : position + 8 + length]
        (crc,) = struct.unpack(">I", data[position + 8 + length : end])
        if zlib.crc32(kind + body) != crc:
            raise NotebookError(where, f"the CRC of the PNG chunk {kind!r} does not match")
        chunks.append((kind, body))
        position = end
        if kind == b"IEND":
            return chunks


def _unfilter(raw: bytes, height: int, stride: int, bpp: int, where: str) -> bytes:
    """Undo the row filters (PNG specification, filter types 0 to 4)."""
    out = bytearray(height * stride)
    previous = bytes(stride)
    for y in range(height):
        start = y * (stride + 1)
        kind = raw[start]
        line = raw[start + 1 : start + 1 + stride]
        row = bytearray(stride)
        if kind == 0:
            row[:] = line
        elif kind == 1:
            for i in range(stride):
                left = row[i - bpp] if i >= bpp else 0
                row[i] = (line[i] + left) & 0xFF
        elif kind == 2:
            for i in range(stride):
                row[i] = (line[i] + previous[i]) & 0xFF
        elif kind == 3:
            for i in range(stride):
                left = row[i - bpp] if i >= bpp else 0
                row[i] = (line[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif kind == 4:
            for i in range(stride):
                a = row[i - bpp] if i >= bpp else 0
                b = previous[i]
                c = previous[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                if pa <= pb and pa <= pc:
                    predictor = a
                elif pb <= pc:
                    predictor = b
                else:
                    predictor = c
                row[i] = (line[i] + predictor) & 0xFF
        else:
            raise NotebookError(where, f"picture row {y} has filter type {kind}, which PNG does not have")
        out[y * stride : (y + 1) * stride] = row
        previous = bytes(row)
    return bytes(out)


def decode(data: bytes, where: str) -> Image:
    """Decode a PNG sheet. `where` names the sheet in errors."""
    chunks = _chunks(data, where)
    kind, header = chunks[0]
    if kind != b"IHDR" or len(header) != 13:
        raise NotebookError(where, "the PNG file does not start with its IHDR chunk")
    width, height, depth, colour, compression, method, interlace = struct.unpack(">IIBBBBB", header)
    if depth != 8 or colour not in CHANNELS or compression != 0 or method != 0 or interlace != 0:
        raise NotebookError(
            where,
            f"the picture is {width} x {height} with bit depth {depth}, colour type {colour} and "
            f"interlace {interlace}; only 8-bit RGB or RGBA without interlacing is read",
        )
    if width < 1 or height < 1:
        raise NotebookError(where, f"the picture has no pixels ({width} x {height})")
    compressed = b"".join(body for kind, body in chunks if kind == b"IDAT")
    try:
        raw = zlib.decompress(compressed)
    except zlib.error as error:
        raise NotebookError(where, f"the picture data does not decompress: {error}") from error
    channels = CHANNELS[colour]
    stride = width * channels
    if len(raw) != height * (stride + 1):
        expected = height * (stride + 1)
        raise NotebookError(
            where, f"the picture data holds {len(raw)} bytes, expected {expected} for {width} x {height}"
        )
    return Image(width, height, colour, _unfilter(raw, height, stride, channels, where))


def _chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def encode(image: Image) -> bytes:
    """Encode `image` as a PNG: 8-bit, no interlacing, filter type 0 on every row."""
    stride = image.width * image.channels
    if len(image.pixels) != image.height * stride:
        raise ValueError(f"{len(image.pixels)} pixel bytes do not fill {image.width} x {image.height}")
    raw = b"".join(b"\x00" + image.pixels[y * stride : (y + 1) * stride] for y in range(image.height))
    header = struct.pack(">IIBBBBB", image.width, image.height, 8, image.colour_type, 0, 0, 0)
    return SIGNATURE + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")
