"""The templates of Dr. Kiro's three lab spec files are the builder's text: they pass the builder-level blind
scan with this application's terms (dr-kiro design 6). The lab keeps them in git in this state."""

from pathlib import Path

from bench.scan import scan as scan_module
from bench.scan.scan import Scanner

ADAPTER = Path(__file__).resolve().parents[1]
ROOT = ADAPTER.parents[1]
STOP_LIST = ROOT / ".kiro" / "blind-scan" / "stop-list.txt"


def test_templates_pass_the_builder_level_scan() -> None:
    scanner = Scanner.from_config([ADAPTER / "scan_sources.toml"], STOP_LIST)
    assert len(scan_module.TEMPLATE_BYTES) == 3
    for data in scan_module.TEMPLATE_BYTES:
        assert scanner.scan_text(data.decode("utf-8"), "builder", "template") == []
