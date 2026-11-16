"""The visual system: contrast, inks without colour, miss red, decoration (Req. 4.5, 4.6, 6.1-6.5)."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]
REPO = PROJECT.parent
STEERING = REPO / ".kiro" / "steering" / "notebook-visual.md"
ASSETS = PROJECT / "src" / "notebook" / "assets"
CSS = ASSETS / "notebook.css"
DECO = ASSETS / "deco.svg"


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
    for ink in (".ink-k", ".ink-p", ".ink-c"):
        decl = rules[ink]
        family = decl["font-family"]
        resolved = re.sub(r"var\((--[a-z-]+)\)", lambda m: properties[m.group(1)], family)
        looks[ink] = (resolved, decl.get("font-style", "normal"))
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
            assert re.search(r"\.miss(-value|-mark)?$", one.strip()), selector
        assert "var(--miss-red)" in body
    root = [body for sel, body in _rules(CSS.read_text(encoding="utf-8")) if sel == ":root"][0]
    assert "var(--miss-red)" not in root


def test_no_remote_or_font_file_in_the_stylesheet():
    css = CSS.read_text(encoding="utf-8")
    assert "url(" not in css and "@import" not in css and "@font-face" not in css


def test_decoration_holds_no_text_and_is_hidden_from_assistive_technology():
    root = ET.fromstring(DECO.read_text(encoding="utf-8"))
    tags = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
    assert not tags & {"text", "title", "desc", "tspan", "textPath", "foreignObject", "image", "use", "a"}
    assert root.get("aria-hidden") == "true"
    assert all(not (element.text or "").strip() for element in root.iter())


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
