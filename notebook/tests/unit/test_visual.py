"""The visual system: contrast, inks without colour, miss red, decoration (Req. 4.5, 4.6, 6.1-6.5)."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from bench.scan.levels import AUTHOR_LEVEL
from bench.scan.scan import Scanner

from notebook import addresses, ink
from notebook.pages import parts

PROJECT = Path(__file__).resolve().parents[2]
REPO = PROJECT.parent
STEERING = REPO / ".kiro" / "steering" / "notebook-visual.md"
ASSETS = PROJECT / "src" / "notebook" / "assets"
CSS = ASSETS / "notebook.css"
SCRIPT = ASSETS / "notebook.js"


def _decoration() -> str:
    return ink.join(parts.decoration())[0]


def _rules(css: str) -> list[tuple[str, str]]:
    """(selector, declarations) for every style rule, at top level and inside @media blocks."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules: list[tuple[str, str]] = []
    i = 0
    while i < len(css):
        open_at = css.find("{", i)
        if open_at < 0:
            assert css[i:].strip() == "", f"text after the last rule: {css[i:]!r}"
            break
        head = css[i:open_at].strip()
        depth, j = 1, open_at + 1
        while depth:
            if css[j] == "{":
                depth += 1
            elif css[j] == "}":
                depth -= 1
            j += 1
        body = css[open_at + 1 : j - 1]
        if head.startswith("@media"):
            rules.extend(_rules(body))
        else:
            assert "{" not in body, f"nested block in {head!r}"
            rules.append((head, body))
        i = j
    return rules


def _declarations(body: str) -> dict[str, str]:
    out = {}
    for part in body.split(";"):
        if part.strip():
            name, _, value = part.partition(":")
            out[name.strip()] = value.strip()
    return out


def _custom_properties() -> dict[str, str]:
    roots = [
        _declarations(body)
        for selector, body in _rules(CSS.read_text(encoding="utf-8"))
        if selector == ":root"
    ]
    assert len(roots) == 1
    return {k: v for k, v in roots[0].items() if k.startswith("--")}


def _steering_pairs() -> list[tuple[str, str]]:
    text = STEERING.read_text(encoding="utf-8")
    fg = re.findall(r"^foreground:(.*)$", text, flags=re.M)
    bg = re.findall(r"^background:(.*)$", text, flags=re.M)
    assert len(fg) == 1 and len(bg) == 1, "the steering file names one foreground and one background list"
    return [(f, b) for f in fg[0].split() for b in bg[0].split()]


def _luminance(hex_colour: str) -> float:
    assert re.fullmatch(r"#[0-9a-f]{6}", hex_colour), hex_colour
    channels = [int(hex_colour[k : k + 2], 16) / 255 for k in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def test_wcag_formula_on_known_pairs():
    assert contrast("#000000", "#ffffff") == pytest.approx(21.0)
    assert contrast("#777777", "#ffffff") == pytest.approx(4.48, abs=0.01)


@pytest.mark.parametrize("pair", _steering_pairs(), ids=lambda p: f"{p[0]} on {p[1]}")
def test_every_named_pair_reaches_4_5(pair):
    properties = _custom_properties()
    fg, bg = pair
    assert fg in properties and bg in properties, f"{fg} or {bg} is not a custom property in notebook.css"
    assert contrast(properties[fg], properties[bg]) >= 4.5


def test_steering_colours_equal_the_css_values():
    properties = _custom_properties()
    text = STEERING.read_text(encoding="utf-8")
    named = re.findall(r"`(--[a-z0-9-]+)` `(#[0-9a-f]{6})`", text)
    assert named
    for name, value in named:
        assert properties.get(name) == value, name


def test_each_ink_differs_in_family_or_style():
    rules = {sel: _declarations(body) for sel, body in _rules(CSS.read_text(encoding="utf-8"))}
    properties = _custom_properties()
    looks = {}
    for ink_class in (".ink-k", ".ink-p", ".ink-c"):
        decl = rules[ink_class]
        family = decl["font-family"]
        resolved = re.sub(r"var\((--[a-z-]+)\)", lambda m: properties[m.group(1)], family)
        looks[ink_class] = (resolved, decl.get("font-style", "normal"))
    inks = list(looks)
    for i, a in enumerate(inks):
        for b in inks[i + 1 :]:
            assert looks[a][0] != looks[b][0] or looks[a][1] != looks[b][1], (a, b)


def test_miss_red_is_used_only_by_the_miss_classes():
    users = [
        (sel, body)
        for sel, body in _rules(CSS.read_text(encoding="utf-8"))
        if "--miss-red" in body and sel != ":root"
    ]
    assert users
    for selector, body in users:
        for one in selector.split(","):
            assert re.search(r"\.miss(-value|-mark|-stamp)?$", one.strip()), selector
        assert "var(--miss-red)" in body
    root = [body for sel, body in _rules(CSS.read_text(encoding="utf-8")) if sel == ":root"][0]
    assert "var(--miss-red)" not in root


def test_the_stylesheet_fetches_only_the_typefaces_shipped_with_the_site():
    css = CSS.read_text(encoding="utf-8")
    assert "@import" not in css
    urls = re.findall(r"url\(([^)]*)\)", css)
    assert urls, "the stylesheet names no typeface file"
    # Every url() is one of the shipped typeface files, written without a folder (the stylesheet is in `a/`).
    assert sorted(set(urls)) == sorted(addresses.FONT_FILES)
    for name in addresses.FONT_FILES:
        assert (ASSETS / "fonts" / name).is_file(), name
    # Every @font-face names its file through url() and a face: no other source such as local().
    for selector, body in _rules(css):
        if selector == "@font-face":
            src = _declarations(body)["src"]
            assert re.fullmatch(r"url\([a-z0-9-]+\.woff2\) format\(\"woff2\"\)", src), src


def test_the_typeface_licences_are_shipped_and_named():
    licence = (ASSETS / "fonts" / "LICENSE.txt").read_text(encoding="utf-8")
    for family in ("Caveat", "Lora", "IBM Plex Mono", "SIL Open Font License, Version 1.1"):
        assert family in licence, family


def test_decoration_holds_no_text_and_is_hidden_from_assistive_technology():
    markup = _decoration()
    assert "xmlns" not in markup and "http:" not in markup and "https:" not in markup
    root = ET.fromstring(markup)
    assert root.tag == "svg" and root.get("class") == "deco"
    tags = {element.tag for element in root.iter()}
    assert tags <= {"svg", "g", "path"}, tags
    assert root.get("aria-hidden") == "true"
    assert all(not (element.text or "").strip() for element in root.iter())
    assert all(not (element.tail or "").strip() for element in root.iter())
    # Drawn in currentColor: the stylesheet gives the colour, the markup holds no colour literal.
    assert "#" not in markup


def test_decoration_is_inline_markup_not_a_file():
    assert not (ASSETS / "deco.svg").exists()
    assert {segment.ink for segment in parts.decoration()} == {ink.Ink.MARKUP}


def test_assets_and_decoration_pass_the_builder_level_scan():
    scanner = Scanner.from_config(
        [
            REPO / "body-lab" / "adapter" / "scan_sources.toml",
            REPO / "wind-tunnel" / "adapter" / "scan_sources.toml",
        ],
        REPO / ".kiro" / "blind-scan" / "stop-list.txt",
    )
    level = AUTHOR_LEVEL["bench"]
    for where, content in (
        ("notebook.css", CSS.read_text(encoding="utf-8")),
        ("notebook.js", SCRIPT.read_text(encoding="utf-8")),
        ("decoration", _decoration()),
    ):
        assert scanner.scan_text(content, level, where) == [], where


def test_stylesheet_holds_no_remote_address():
    css = CSS.read_text(encoding="utf-8")
    assert "http:" not in css and "https:" not in css


def test_decoration_shows_only_from_1000px_in_a_reserved_gutter():
    rules = _rules(CSS.read_text(encoding="utf-8"))
    css = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"))
    base = [_declarations(body) for sel, body in rules if sel == ".deco"]
    assert base[0]["display"] == "none" and base[0]["pointer-events"] == "none"
    media = re.search(r"@media \(min-width: 1000px\) \{(.*?)\n\}", css, flags=re.S)
    assert media
    inner = dict((sel, _declarations(body)) for sel, body in _rules(media.group(1)))
    assert inner["body"]["padding-left"] == "96px"
    deco = inner[".deco"]
    assert deco["position"] == "fixed" and deco["width"] == "64px"
    # Left 16px plus 64px wide stays inside the 96px gutter.
    assert deco["left"] == "var(--space-3)" and _custom_properties()["--space-3"] == "16px"


def test_picture_buttons_are_44px_targets_on_a_phone_or_a_touch_screen():
    css = CSS.read_text(encoding="utf-8")
    start = css.index("@media (max-width: 559px), (pointer: coarse) {")
    block = css[start : css.index("\n}\n", start)]
    assert ".photo-controls button {" in block
    assert "min-width: 44px;" in block and "min-height: 44px;" in block


def _declared(selector: str) -> dict[str, str]:
    """The declarations of every rule that lists `selector` among its comma-separated selectors."""
    css = CSS.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for sel, body in _rules(css):
        if selector in [part.strip() for part in sel.split(",")]:
            out.update(_declarations(body))
    assert out, f"no rule for {selector}"
    return out


def test_the_spec_table_header_row_is_clipped_out_of_sight_and_not_removed():
    head = _declared(".spec-table thead")
    assert "display" not in head, "display: none would hide the column names from a screen reader"
    assert head["position"] == "absolute" and head["width"] == "1px" and head["height"] == "1px"
    assert head["clip-path"] == "inset(50%)" and head["overflow"] == "hidden"


def test_each_spec_row_is_a_block_card_and_its_cells_carry_their_header_word_as_a_caption():
    for tag in (".spec-table tbody", ".spec-table tr", ".spec-table td"):
        assert _declared(tag)["display"] == "block", tag
    caption = _declared(".spec-row > tr[id] > td::before")
    assert caption["content"] == "attr(data-label)"
    # Two columns of cards only where the margin column leaves room: from 1000px, and by width, not by count.
    assert _declared(".spec-table")["display"] in {"block", "grid"}
    assert "repeat(auto-fill," in CSS.read_text(encoding="utf-8")


def test_the_strike_through_of_a_rejected_row_leaves_the_status_cell_alone():
    strike = _declared(".row-rejected td:not(.status)")
    assert strike["text-decoration"].startswith("line-through")


def test_the_replaced_by_arrow_is_a_drawn_shape_because_no_typeface_has_the_arrow_character():
    css = CSS.read_text(encoding="utf-8")
    assert "\u2192" not in css and "\\2192" not in css
    for selector in (".cover-replaced::before", ".spec-row .tab > summary::before"):
        shape = _declared(selector)
        assert shape["content"] == '""' and shape["clip-path"].startswith("polygon(")
