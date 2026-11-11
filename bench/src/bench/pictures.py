"""Structure check of the pictures an adapter returns (design section 4).

The bench returns pictures and nothing else, so a picture may carry no text or metadata. Each format is
walked chunk by chunk, and only chunks that hold image data are allowed. Anything else, including
trailing bytes after the end of the image, is refused. The pixels themselves are not decoded.
"""

import struct
import zlib

PICTURE_KINDS = frozenset({"image/png", "image/gif", "image/webp"})


class PictureError(ValueError):
    """The picture is malformed or carries something other than image data."""


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# Chunks that hold image data only. iCCP, sPLT, tEXt, zTXt, iTXt, eXIf, tIME and all others are refused.
_PNG_ALLOWED = frozenset(
    {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"gAMA", b"cHRM", b"sRGB", b"sBIT", b"bKGD", b"pHYs"}
    | {b"acTL", b"fcTL", b"fdAT"}
)


def _check_png(data: bytes) -> None:
    if not data.startswith(_PNG_SIGNATURE):
        raise PictureError("not a PNG signature")
    pos = len(_PNG_SIGNATURE)
    first = True
    while True:
        if pos + 8 > len(data):
            raise PictureError("PNG ends inside a chunk header")
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        end = pos + 12 + length
        if end > len(data):
            raise PictureError(f"PNG chunk {kind!r} runs past the end")
        body = data[pos + 8 : pos + 8 + length]
        (crc,) = struct.unpack(">I", data[pos + 8 + length : end])
        if zlib.crc32(kind + body) != crc:
            raise PictureError(f"PNG chunk {kind!r} has a bad CRC")
        if first and kind != b"IHDR":
            raise PictureError("PNG does not start with IHDR")
        first = False
        if kind not in _PNG_ALLOWED:
            raise PictureError(f"PNG chunk {kind.decode('latin-1')!r} is not allowed")
        pos = end
        if kind == b"IEND":
            break
    if pos != len(data):
        raise PictureError("PNG has bytes after IEND")


_GIF_LOOP_APPLICATIONS = frozenset({b"NETSCAPE2.0", b"ANIMEXTS1.0"})


def _skip_sub_blocks(data: bytes, pos: int) -> int:
    while True:
        if pos >= len(data):
            raise PictureError("GIF ends inside a data block")
        size = data[pos]
        pos += 1
        if size == 0:
            return pos
        pos += size


def _check_gif(data: bytes) -> None:
    if data[:6] not in (b"GIF87a", b"GIF89a"):
        raise PictureError("not a GIF signature")
    if len(data) < 13:
        raise PictureError("GIF is too short")
    flags = data[10]
    pos = 13
    if flags & 0x80:
        pos += 3 * (2 ** ((flags & 0x07) + 1))
    while True:
        if pos >= len(data):
            raise PictureError("GIF has no trailer")
        block = data[pos]
        if block == 0x3B:
            pos += 1
            break
        if block == 0x2C:
            if pos + 10 > len(data):
                raise PictureError("GIF ends inside an image descriptor")
            local = data[pos + 9]
            pos += 10
            if local & 0x80:
                pos += 3 * (2 ** ((local & 0x07) + 1))
            pos += 1  # LZW minimum code size
            pos = _skip_sub_blocks(data, pos)
        elif block == 0x21:
            if pos + 2 > len(data):
                raise PictureError("GIF ends inside an extension")
            label = data[pos + 1]
            if label == 0xF9:
                pos = _skip_sub_blocks(data, pos + 2)
            elif label == 0xFF:
                size = data[pos + 2] if pos + 2 < len(data) else 0
                ident = data[pos + 3 : pos + 3 + size]
                if size != 11 or ident not in _GIF_LOOP_APPLICATIONS:
                    raise PictureError("GIF application extension is not allowed")
                pos = _skip_sub_blocks(data, pos + 3 + size)
            else:
                raise PictureError(f"GIF extension 0x{label:02X} is not allowed")
        else:
            raise PictureError(f"GIF block 0x{block:02X} is not allowed")
    if pos != len(data):
        raise PictureError("GIF has bytes after the trailer")


_WEBP_ALLOWED = frozenset({b"VP8 ", b"VP8L", b"VP8X", b"ANIM", b"ANMF", b"ALPH"})
_WEBP_FRAME_ALLOWED = frozenset({b"VP8 ", b"VP8L", b"ALPH"})


def _walk_riff_chunks(data: bytes, pos: int, end: int, allowed: frozenset[bytes]) -> None:
    while pos < end:
        if pos + 8 > end:
            raise PictureError("WebP ends inside a chunk header")
        kind = data[pos : pos + 4]
        (size,) = struct.unpack("<I", data[pos + 4 : pos + 8])
        body_end = pos + 8 + size
        if body_end > end:
            raise PictureError(f"WebP chunk {kind!r} runs past the end")
        if kind not in allowed:
            raise PictureError(f"WebP chunk {kind.decode('latin-1')!r} is not allowed")
        if kind == b"ANMF":
            if size < 16:
                raise PictureError("WebP ANMF chunk is too short")
            _walk_riff_chunks(data, pos + 8 + 16, body_end, _WEBP_FRAME_ALLOWED)
        pos = body_end + (size & 1)
    if pos != end:
        raise PictureError("WebP chunk padding runs past the end")


def _check_webp(data: bytes) -> None:
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise PictureError("not a WebP signature")
    (size,) = struct.unpack("<I", data[4:8])
    if size + 8 != len(data):
        raise PictureError("WebP size does not match the file length")
    _walk_riff_chunks(data, 12, len(data), _WEBP_ALLOWED)


def _png_chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def encode_png(pixels: list[list[tuple[int, int, int]]]) -> bytes:
    """Encode rows of RGB pixels as a PNG with no ancillary chunks. Used by the fake application."""
    if not pixels or not pixels[0]:
        raise PictureError("a PNG needs at least one pixel")
    width = len(pixels[0])
    if any(len(row) != width for row in pixels):
        raise PictureError("all PNG rows must have the same width")
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for r, g, b in row:
            raw += bytes((r, g, b))
    header = struct.pack(">IIBBBBB", width, len(pixels), 8, 2, 0, 0, 0)
    return (
        _PNG_SIGNATURE
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _png_chunk(b"IEND", b"")
    )


def check_picture(kind: str, data: bytes) -> None:
    """Raise PictureError if the picture is malformed or carries anything other than image data."""
    if not data:
        raise PictureError("picture is empty")
    if kind == "image/png":
        _check_png(data)
    elif kind == "image/gif":
        _check_gif(data)
    elif kind == "image/webp":
        _check_webp(data)
    else:
        raise PictureError(f"unknown picture kind {kind!r}")
