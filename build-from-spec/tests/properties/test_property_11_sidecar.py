# Feature: build-from-spec, Property 11: The sidecar gives every character one author
"""For any run file content, the sidecar's ranges cover the run file's text in order without gaps, the
`dr-kiro` ranges are exactly the JSON string tokens of the relied-on ids, and the bench accepts the pair.

**Validates: Requirements 14.4, 16.5**
"""

import json
import tempfile
from pathlib import Path

from bench.scan.levels import sidecar_pieces
from hypothesis import given, settings

from build_from_spec.runfile import run_file_texts
from support import run_file_contents


@settings(max_examples=100)
@given(run_file_contents())
def test_sidecar_gives_every_character_one_author(data):
    text, sidecar = run_file_texts(data)
    ranges = json.loads(sidecar)["ranges"]

    position = 0
    for item in ranges:
        assert item["start"] == position
        assert item["end"] > item["start"]
        assert item["author"] in ("bench", "dr-kiro")
        position = item["end"]
    assert position == len(text)

    ids = data["relied_on"]["ids"] or []
    reader_tokens = [text[item["start"] : item["end"]] for item in ranges if item["author"] == "dr-kiro"]
    assert reader_tokens == [json.dumps(identifier, ensure_ascii=False) for identifier in ids]

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "probe-none-1.run.json"
        path.write_text(text, encoding="utf-8", newline="")
        Path(f"{path}.authors.json").write_text(sidecar, encoding="utf-8", newline="")
        pieces = sidecar_pieces(path, text)
    assert "".join(piece.text for piece in pieces) == text
    levels = ["dr-kiro" if item["author"] == "dr-kiro" else "builder" for item in ranges]
    assert [piece.level for piece in pieces] == levels
