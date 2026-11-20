"""The site checks of task 9.5 (Requirements 3.1-3.4, 3.7, 4.5; design 9, N28), shared by the fixture build
test and the real build test. Each check returns a list of problems, each naming the file, so a failing test
says what is wrong and where.
"""

import re
from html.parser import HTMLParser
from pathlib import Path

from bench.scan.levels import SIDECAR_SUFFIX

from notebook import addresses

TEXT_SUFFIXES = (".html", ".css", ".js")
# Text that no file of the site may hold (3.2, 3.3, N28): a request to another host, an XML namespace, a form
# or an embedded frame. Matched case-insensitively.
FORBIDDEN = (
    "http:",
    "https:",
    "xmlns",
    "<form",
    "<iframe",
    "<input",
    "<textarea",
    "<select",
    "<object",
    "<embed",
)
# The one form control of the site: the radio of a lab tab on the cover. It sits outside any `<form>` (which
# stays forbidden), is named "lab-tab" and has no `value`, so it cannot send anything. Its markup is removed
# before the search for `<input`, so any other input still fails.
TAB_RADIO = re.compile(
    r'<input type="radio" name="lab-tab" id="tab-[a-z0-9-]+" class="tab-radio"( checked="checked")?>'
)
# Script calls that send or fetch data (3.2, 3.3).
FORBIDDEN_SCRIPT = (
    "fetch(",
    "xmlhttprequest",
    "websocket",
    "sendbeacon",
    "eventsource",
    "import(",
    "import ",
)
# The only buttons: the moving picture controls (design 10).
BUTTON_ACTIONS = {"play", "pause", "step", "sheet", "back"}
# The assets of `a/`: the stylesheet, the script, the typefaces and their licence (all served by the site).
ASSETS = {
    addresses.STYLESHEET,
    addresses.SCRIPT,
    addresses.FONT_LICENSE,
    *(f"{addresses.ASSET_DIR}/{name}" for name in addresses.FONT_FILES),
}
_CSS_URL = re.compile(r"url\(\s*['\"]?([^'\")]*)", re.IGNORECASE)
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)


def files(site: Path) -> list[str]:
    return sorted(p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file())


def pages(site: Path) -> list[str]:
    return [f for f in files(site) if f.endswith(".html")]


class _Page(HTMLParser):
    """Links, buttons, scripts, stylesheets and the text outside scripts of one page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str, str]] = []  # (tag, attribute, value)
        self.buttons: list[dict[str, str | None]] = []
        self.scripts: list[dict[str, str | None]] = []
        self.script_text: list[str] = []
        self.styles: list[str] = []
        self.text: list[str] = []
        self.row_ids: list[str] = []
        self.tables = 0
        self._in: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for name in ("href", "src", "srcset", "action", "formaction", "poster", "data"):
            if name in a:
                self.links.append((tag, name, a[name] or ""))
        if tag == "button":
            self.buttons.append(a)
        if tag == "script":
            self.scripts.append(a)
        if tag == "link":
            self.styles.append(a.get("href") or "")
        if tag == "table":
            self.tables += 1
        if tag == "tr" and (a.get("id") or "").startswith("row-"):
            self.row_ids.append(a["id"][len("row-") :])
        if tag == "li" and (a.get("id") or "").startswith("row-"):
            self.row_ids.append(a["id"][len("row-") :])
        if tag in ("script", "style"):
            self._in.append(tag)

    def handle_endtag(self, tag):
        if self._in and self._in[-1] == tag:
            self._in.pop()

    def handle_data(self, data):
        if self._in and self._in[-1] == "script":
            self.script_text.append(data)
        elif not self._in:
            self.text.append(data)


def parse(site: Path, page: str) -> _Page:
    parser = _Page()
    parser.feed((site / page).read_text(encoding="utf-8"))
    parser.close()
    return parser


def layout_problems(site: Path) -> list[str]:
    """The root holds the front page and one folder per application; each has its pages, `a/` and `p/` and
    nothing else (3.2, N28)."""
    out = []
    for f in files(site):
        base = f.removesuffix(SIDECAR_SUFFIX)
        parts = base.split("/")
        scope = (
            parts[0] + "/"
            if len(parts) > 1 and parts[0] not in (addresses.ASSET_DIR, addresses.PICTURE_DIR)
            else ""
        )
        rest = base[len(scope) :]
        if "/" not in rest:
            if not rest.endswith(".html"):
                out.append(f"{f}: a file that is not a page, at a page's place")
        elif rest.startswith(f"{addresses.ASSET_DIR}/"):
            if rest not in ASSETS or rest.count("/") != 1:
                out.append(f"{f}: an asset that is not the stylesheet, the script, a typeface or the licence")
        elif not re.fullmatch(r"p/[0-9a-f]{64}\.png", rest) or f.endswith(SIDECAR_SUFFIX):
            out.append(f"{f}: a file in a subfolder that is not a picture or an asset")
    return out


def text_problems(site: Path) -> list[str]:
    """No text file holds a forbidden item (3.2, 3.3, N28)."""
    out = []
    for f in files(site):
        if not f.endswith(TEXT_SUFFIXES + (SIDECAR_SUFFIX,)):
            continue
        content = TAB_RADIO.sub("", (site / f).read_text(encoding="utf-8")).lower()
        for item in FORBIDDEN:
            if item in content:
                out.append(f"{f}: holds {item!r}")
        if f.endswith(".js"):
            for item in FORBIDDEN_SCRIPT:
                if item in content:
                    out.append(f"{f}: holds {item!r}")
    return out


def _link_problem(value: str) -> str | None:
    target = value.split("#", 1)[0].split("?", 1)[0]
    if value.startswith("//"):
        return "starts with //"
    if _SCHEME.match(value):
        return "names a scheme"
    if re.fullmatch(r"/([a-z0-9-]+/)?index\.html", value):
        return None  # to the front page or to another application (design, "Pages")
    if value.startswith("/") or value.startswith("\\"):
        return "is absolute"
    if ".." in value:
        return "contains .."
    if target and not (
        re.fullmatch(r"[a-z0-9-]+\.html|[a-z0-9-]+/index\.html", target)
        or target in (addresses.STYLESHEET, addresses.SCRIPT)
        or re.fullmatch(r"p/[0-9a-f]{64}\.png", target)
    ):
        return "names no page, asset or picture of the flat site"
    return None


def link_problems(site: Path) -> list[str]:
    """Every link of every page and every `url()` of the stylesheet is relative into the flat site (3.2)."""
    out = []
    for page in pages(site):
        for tag, name, value in parse(site, page).links:
            problem = _link_problem(value)
            if problem is not None:
                out.append(f"{page}: <{tag} {name}={value!r}> {problem}")
    for f in files(site):
        if f.endswith(".css"):
            for match in _CSS_URL.finditer((site / f).read_text(encoding="utf-8")):
                if match.group(1) in addresses.FONT_FILES:
                    continue  # a typeface file beside the stylesheet, in `a/`
                problem = _link_problem(match.group(1))
                if problem is not None:
                    out.append(f"{f}: url({match.group(1)!r}) {problem}")
    return out


def page_problems(site: Path) -> list[str]:
    """Per page: the one stylesheet and the one script of the site, no inline script, buttons only for the
    moving pictures, a link to the ink legend (3.1, 3.3, 3.4, 4.5) and a link to how the lab works (footer,
    user 2026-11-17)."""
    out = []
    for page in pages(site):
        p = parse(site, page)
        sources = [s.get("src") for s in p.scripts]
        if sources != [addresses.SCRIPT]:
            out.append(f"{page}: scripts {sources}, expected only {addresses.SCRIPT}")
        if "".join(p.script_text).strip():
            out.append(f"{page}: holds an inline script")
        if p.styles != [addresses.STYLESHEET]:
            out.append(f"{page}: stylesheets {p.styles}, expected only {addresses.STYLESHEET}")
        for b in p.buttons:
            if b.get("type") == "button" and b.get("class") == "mode-toggle":
                continue  # the night and day switch
            if b.get("type") != "button" or b.get("data-action") not in BUTTON_ACTIONS:
                out.append(f"{page}: a button that is not a moving picture control: {b}")
        anchors = {v for tag, name, v in p.links if tag == "a" and name == "href"}
        if page == addresses.COVER:
            continue  # the front page has no footer links
        for target in (addresses.LEGEND, addresses.HOW):
            if target not in anchors:
                out.append(f"{page}: no link to {target}")
        if not "".join(p.text).strip():
            out.append(f"{page}: no text outside scripts")
    return out


def all_problems(site: Path) -> list[str]:
    return layout_problems(site) + text_problems(site) + link_problems(site) + page_problems(site)
