import dataclasses
import math
import struct
import zlib

import pytest

from bench.adapter import (
    Declaration,
    DeclarationError,
    FunctionKnob,
    Measurement,
    NotMeasured,
    NumberKnob,
    Picture,
    ResultError,
    TrialFailure,
    TrialResult,
    check_declaration,
    check_failure,
    check_result,
)
from bench.pictures import PictureError, _png_chunk, check_picture, encode_png

PNG = encode_png([[(0, 0, 0), (255, 255, 255)]])


def decl(**changes: object) -> Declaration:
    base = Declaration(
        knobs=(
            FunctionKnob("drive", -1.0, 1.0, (0.0, 0.5, 1.0), 1.0),
            NumberKnob("gain", 0.0, 3.0),
        ),
        measurements=(
            Measurement("distance", "m", "scalar", ("lost",)),
            Measurement("path", "m", "series"),
        ),
        picture="image/png",
        budget=10,
        fake=True,
    )
    return dataclasses.replace(base, **changes)  # type: ignore[arg-type]


def result(**values: object) -> TrialResult:
    base: dict[str, object] = {"distance": 0.25, "path": (0.0, 0.25)}
    base.update(values)
    return TrialResult(base, Picture("image/png", PNG))  # type: ignore[arg-type]


def test_valid_declaration() -> None:
    check_declaration(decl())


@pytest.mark.parametrize(
    "changes",
    [
        {"knobs": ()},
        {"measurements": ()},
        {"knobs": (NumberKnob("not a name", 0, 1),)},
        {"knobs": (NumberKnob("class", 0, 1),)},
        {"knobs": (NumberKnob("t", 0, 1),)},
        {"knobs": (NumberKnob("PARAMS", 0, 1),)},
        {"knobs": (NumberKnob("g", 1, 1),)},
        {"knobs": (NumberKnob("g", 0, math.inf),)},
        {"knobs": (FunctionKnob("d", -1, 1, (), 1.0),)},
        {"knobs": (FunctionKnob("d", -1, 1, (0.0, 2.0), 1.0),)},
        {"knobs": (FunctionKnob("d", -1, 1, (0.5, 0.5), 1.0),)},
        {"knobs": (FunctionKnob("d", -1, 1, (0.0,), 0.0),)},
        {"knobs": (NumberKnob("g", 0, 1), NumberKnob("g", 0, 2))},
        {"measurements": (Measurement("gain", "1", "scalar"),)},
        {"measurements": (Measurement("m", "", "scalar"),)},
        {"measurements": (Measurement("m", "1", "vector"),)},  # type: ignore[arg-type]
        {"measurements": (Measurement("m", "1", "scalar", ("a", "a")),)},
        {"measurements": (Measurement("m", "1", "scalar", ("not ok",)),)},
        {"picture": "image/jpeg"},
        {"budget": 0},
        {"budget": True},
    ],
)
def test_declaration_problems(changes: dict[str, object]) -> None:
    with pytest.raises(DeclarationError):
        check_declaration(decl(**changes))


def test_valid_results() -> None:
    check_result(decl(), result())
    check_result(decl(), result(distance=NotMeasured("lost", "the marker left the view")))


@pytest.mark.parametrize(
    "bad",
    [
        {"distance": None},
        {"distance": math.nan},
        {"distance": True},
        {"distance": "0.25"},
        {"path": ()},
        {"path": (0.0, math.inf)},
        {"path": [0.0, 1.0]},
        {"distance": NotMeasured("undeclared", "why")},
        {"distance": NotMeasured("lost", "")},
        {"path": NotMeasured("lost", "path declares no not-measured outcome")},
        {"extra": 1.0},
    ],
)
def test_result_problems(bad: dict[str, object]) -> None:
    with pytest.raises(ResultError):
        check_result(decl(), result(**bad))


def test_missing_measurement_without_outcome_is_an_error() -> None:
    with pytest.raises(ResultError, match="missing"):
        check_result(decl(), TrialResult({"path": (0.0,)}, Picture("image/png", PNG)))


def test_result_must_be_a_trial_result_with_one_picture() -> None:
    with pytest.raises(ResultError):
        check_result(decl(), {"distance": 1.0})
    with pytest.raises(ResultError):
        check_result(decl(), TrialResult({"distance": 1.0, "path": (1.0,)}, Picture("image/gif", PNG)))


def test_failure_needs_a_public_reason() -> None:
    check_failure(TrialFailure("the run did not settle", "trace"))
    with pytest.raises(ResultError):
        check_failure(TrialFailure("", "trace"))


# Pictures


def _with_chunk_before_iend(png: bytes, kind: bytes, body: bytes) -> bytes:
    iend = png.rindex(b"IEND") - 4
    return png[:iend] + _png_chunk(kind, body) + png[iend:]


def test_png_without_text_passes() -> None:
    check_picture("image/png", PNG)


@pytest.mark.parametrize("kind", [b"tEXt", b"zTXt", b"iTXt", b"eXIf", b"iCCP", b"tIME", b"abCD"])
def test_png_with_metadata_chunk_fails(kind: bytes) -> None:
    with pytest.raises(PictureError):
        check_picture("image/png", _with_chunk_before_iend(PNG, kind, b"Comment\x00hello"))


def test_png_with_trailing_bytes_or_bad_crc_fails() -> None:
    with pytest.raises(PictureError):
        check_picture("image/png", PNG + b"hidden")
    broken = bytearray(PNG)
    broken[-5] ^= 0xFF
    with pytest.raises(PictureError):
        check_picture("image/png", bytes(broken))


# A 1x1 GIF: header, screen descriptor with a 2-colour table, graphic control, image, trailer.
GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff"
    b"\x21\xf9\x04\x01\x00\x00\x00\x00"
    b"\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00"
    b"\x3b"
)
LOOP = b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"


def test_gif_passes_with_loop_extension() -> None:
    check_picture("image/gif", GIF)
    check_picture("image/gif", GIF[:19] + LOOP + GIF[19:])


@pytest.mark.parametrize(
    "block",
    [
        b"\x21\xfe\x05hello\x00",  # comment
        b"\x21\x01\x0c" + b"\x00" * 12 + b"\x02hi\x00",  # plain text
        b"\x21\xff\x0bXMP DataXMP\x02hi\x00",  # other application
    ],
)
def test_gif_with_text_fails(block: bytes) -> None:
    with pytest.raises(PictureError):
        check_picture("image/gif", GIF[:19] + block + GIF[19:])


def _riff(chunks: bytes) -> bytes:
    body = b"WEBP" + chunks
    return b"RIFF" + struct.pack("<I", len(body)) + body


def _chunk(kind: bytes, body: bytes) -> bytes:
    return kind + struct.pack("<I", len(body)) + body + (b"\x00" if len(body) % 2 else b"")


def test_webp_containers() -> None:
    check_picture("image/webp", _riff(_chunk(b"VP8L", b"\x2f\x00\x00\x00\x00")))
    frame = _chunk(b"ANMF", b"\x00" * 16 + _chunk(b"VP8L", b"\x00\x00"))
    check_picture("image/webp", _riff(_chunk(b"VP8X", b"\x00" * 10) + _chunk(b"ANIM", b"\x00" * 6) + frame))


@pytest.mark.parametrize("kind", [b"EXIF", b"XMP ", b"ICCP", b"abcd"])
def test_webp_with_metadata_fails(kind: bytes) -> None:
    with pytest.raises(PictureError):
        check_picture("image/webp", _riff(_chunk(b"VP8L", b"\x00\x00") + _chunk(kind, b"text")))


def test_webp_metadata_inside_a_frame_fails() -> None:
    frame = _chunk(b"ANMF", b"\x00" * 16 + _chunk(b"EXIF", b"text"))
    with pytest.raises(PictureError):
        check_picture("image/webp", _riff(frame))


def test_wrong_signatures_fail() -> None:
    for kind in ("image/png", "image/gif", "image/webp"):
        with pytest.raises(PictureError):
            check_picture(kind, b"not a picture")
    with pytest.raises(PictureError):
        check_picture("image/png", b"")


def test_encode_png_is_deterministic_and_plain() -> None:
    pixels = [[(10, 20, 30)] * 3] * 2
    assert encode_png(pixels) == encode_png(pixels)
    assert zlib.decompress(encode_png(pixels)[33 + 8 : -12 - 4])[:1] == b"\x00"
