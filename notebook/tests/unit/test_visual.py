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
        if head.startswith(("@media", "@supports")):
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


DARK_QUERY = "@media (prefers-color-scheme: dark) {"


def _dark_block(css: str) -> str:
    """The body of the one `prefers-color-scheme: dark` block (the night lab's custom properties)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    assert css.count(DARK_QUERY) == 1
    start = css.index(DARK_QUERY) + len(DARK_QUERY)
    depth, j = 1, start
    while depth:
        depth += {"{": 1, "}": -1}.get(css[j], 0)
        j += 1
    return css[start : j - 1]


def _custom_properties() -> dict[str, str]:
    """The day values: the one `:root` rule outside the dark block."""
    css = CSS.read_text(encoding="utf-8")
    css = css.replace(_dark_block(css), "")
    roots = [_declarations(body) for selector, body in _rules(css) if selector == ":root"]
    assert len(roots) == 1
    return {k: v for k, v in roots[0].items() if k.startswith("--")}


def _dark_properties() -> dict[str, str]:
    """The night values: every custom property of the day palette, overridden where the night lab differs."""
    rules = _rules(_dark_block(CSS.read_text(encoding="utf-8")))
    assert [selector for selector, _ in rules] == [":root"], "the dark block holds one :root rule only"
    night = {k: v for k, v in _declarations(rules[0][1]).items() if k.startswith("--")}
    return {**_custom_properties(), **night}


def _steering_pairs() -> list[tuple[str, str]]:
    text = STEERING.read_text(encoding="utf-8")
    fg = re.findall(r"^foreground:(.*)$", text, flags=re.M)
    bg = re.findall(r"^background:(.*)$", text, flags=re.M)
    assert len(fg) == 1 and len(bg) == 1, "the steering file names one foreground and one background list"
    return [(f, b) for f in fg[0].split() for b in bg[0].split()]


def _steering_dark_pairs() -> list[tuple[str, str]]:
    text = STEERING.read_text(encoding="utf-8")
    fg = re.findall(r"^foreground-dark:(.*)$", text, flags=re.M)
    bg = re.findall(r"^background-dark:(.*)$", text, flags=re.M)
    assert len(fg) == 1 and len(bg) == 1, "the steering file names one dark foreground and background list"
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


@pytest.mark.parametrize("pair", _steering_dark_pairs(), ids=lambda p: f"night {p[0]} on {p[1]}")
def test_every_named_pair_reaches_4_5_in_the_night_lab(pair):
    properties = _dark_properties()
    fg, bg = pair
    assert fg in properties and bg in properties, f"{fg} or {bg} is not a custom property in notebook.css"
    assert contrast(properties[fg], properties[bg]) >= 4.5


def test_the_night_lab_covers_the_same_text_pairs_as_the_day():
    assert _steering_dark_pairs() == _steering_pairs()


def test_the_night_lab_values_equal_the_steering_values():
    night = _dark_properties()
    named = re.findall(r"`(--[a-z0-9-]+)` night: `(#[0-9a-f]{6})`", STEERING.read_text(encoding="utf-8"))
    assert named
    for name, value in named:
        assert night.get(name) == value, name
    # Every custom property the dark block changes is named in the steering file.
    block = _declarations(_rules(_dark_block(CSS.read_text(encoding="utf-8")))[0][1])
    changed = {k for k, v in block.items() if k.startswith("--") and v.startswith("#")}
    assert changed <= {name for name, _ in named}, changed - {name for name, _ in named}


def test_the_night_lab_changes_only_colours_and_defines_each_one_the_day_defines():
    day, night = _custom_properties(), _dark_properties()
    block = _declarations(_rules(_dark_block(CSS.read_text(encoding="utf-8")))[0][1])
    assert all(name in day for name in block), [n for n in block if n not in day]
    assert all(re.fullmatch(r"#[0-9a-f]{6}|rgba?\([0-9., ]+\)", v) for v in block.values())
    # The ink colours stay four different words of the lab: no two inks share a colour at night.
    assert len({night[k] for k in ("--ink-drkiro", "--ink-pencil", "--ink-commentary")}) == 3


def test_the_page_follows_the_system_colour_scheme_with_no_switch_and_no_script():
    css = CSS.read_text(encoding="utf-8")
    assert "color-scheme: light dark;" in css
    assert "prefers-color-scheme: light" not in css
    script = SCRIPT.read_text(encoding="utf-8")
    assert "prefers-color-scheme" not in script and "localStorage" not in script


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


def _wide_block(css: str) -> re.Match[str]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    found = list(re.finditer(r"@media \(min-width: 1000px\) \{(.*?)\n\}", css, flags=re.S))
    assert len(found) == 1
    return found[0]


def _declared_wide(selector: str) -> dict[str, str]:
    """The declarations of the rules for `selector` inside the `@media (min-width: 1000px)` block only."""
    out: dict[str, str] = {}
    for sel, body in _rules(_wide_block(CSS.read_text(encoding="utf-8")).group(1)):
        if selector in [part.strip() for part in sel.split(",")]:
            out.update(_declarations(body))
    assert out, f"no rule for {selector} from 1000px"
    return out


def _declared_below_wide(selector: str) -> dict[str, str]:
    """The declarations of the rules for `selector` outside the `@media (min-width: 1000px)` block."""
    css = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)
    css = css.replace(_wide_block(css).group(0), "")
    out: dict[str, str] = {}
    for sel, body in _rules(css):
        if selector in [part.strip() for part in sel.split(",")]:
            out.update(_declarations(body))
    assert out, f"no rule for {selector} below 1000px"
    return out


def test_the_cover_top_row_places_its_parts_in_grid_columns_only_when_it_has_a_magnified_sheet():
    css = CSS.read_text(encoding="utf-8")
    rules = _rules(_wide_block(css).group(1))
    placed = [sel for sel, body in rules if re.search(r"grid-(column|row)\s*:", body)]
    assert sorted(placed) == [".cover-top.with-sheet .cover-claim", ".cover-top.with-sheet .photo-magnified"]
    assert _declared_wide(".cover-top.with-sheet")["grid-template-columns"].startswith("clamp(")
    # Nothing places a part of the top row for a top row without a sheet: it keeps its one column.
    assert not [sel for sel, _ in rules if ".cover-top" in sel and "with-sheet" not in sel]


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
    # One column of cards below 1000px; two or more only where the margin column leaves room (from 1000px),
    # and by width, not by count: as many columns as are at least 21rem wide.
    assert _declared_below_wide(".spec-table")["display"] == "block"
    wide = _declared_wide(".spec-table")
    assert wide["display"] == "grid"
    assert wide["grid-template-columns"] == "repeat(auto-fill, minmax(21rem, 1fr))"


def test_the_strike_through_of_a_rejected_row_is_on_the_rule_sentence_only():
    strike = _declared('.row-rejected td[data-label="rule"]')
    assert strike["text-decoration"].startswith("line-through")


def test_a_card_hides_scope_experiments_and_predictions_until_its_details_is_open():
    css = CSS.read_text(encoding="utf-8")
    closed = ".spec-row:not(:has(details.evidence[open]))"
    for label in ("scope", "experiments", "predictions"):
        selector = f'{closed} > tr[id] > td[data-label="{label}"]'
        assert _declared(selector)["display"] == "none"
    # Only where `:has` is known; elsewhere the whole card stays drawn.
    assert "@supports selector(:has(a))" in css
    assert '"id status"' in _declared(f"{closed} > tr[id]")["grid-template-areas"]


def test_the_replaced_by_arrow_is_a_drawn_shape_because_no_typeface_has_the_arrow_character():
    css = CSS.read_text(encoding="utf-8")
    assert "\u2192" not in css and "\\2192" not in css
    for selector in (".cover-replaced::before", ".spec-row .tab > summary::before"):
        shape = _declared(selector)
        assert shape["content"] == '""' and shape["clip-path"].startswith("polygon(")
