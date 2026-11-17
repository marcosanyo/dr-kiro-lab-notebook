"""The site's addresses (design 9, N28): flat pages at the root, checked ids, no `..`."""

import pytest

from notebook import addresses
from notebook.errors import NotebookError

DIGEST = "0" * 63 + "a"


def test_pages_are_at_the_site_root() -> None:
    assert addresses.lab("body-lab", "s") == "body-lab.html"
    assert addresses.session("wind-tunnel", "wt-004", "s") == "wind-tunnel-wt-004.html"
    assert addresses.replay("body-lab", "body-2", 3, "s") == "body-lab-body-2-replay-3.html"
    assert addresses.picture(DIGEST, "s") == f"p/{DIGEST}.png"
    assert (addresses.COVER, addresses.LEGEND, addresses.STYLESHEET) == (
        "index.html",
        "legend.html",
        "a/notebook.css",
    )


@pytest.mark.parametrize("bad", ["Body-lab", "..", "a/b", "a--b", "-a", "", "a_b"])
def test_an_id_outside_the_pattern_cannot_name_a_page(bad) -> None:
    with pytest.raises(NotebookError) as caught:
        addresses.session("body-lab", bad, "sessions/body-lab")
    assert caught.value.where == "sessions/body-lab"


def test_fragments_are_checked_bench_ids() -> None:
    assert addresses.here(addresses.row("R13", "s")) == "#row-R13"
    assert addresses.outcome("E5", "H4.P1", "s") == "E5-H4.P1"
    assert addresses.trial("E5", "T12", "s") == "E5-T12"
    assert addresses.experiment_file("E5", "s") == "E5-file"
    assert addresses.on_page("body-lab-body-2.html", "E5") == "body-lab-body-2.html#E5"
    with pytest.raises(NotebookError):
        addresses.row('R1" onclick="x', "s")
    with pytest.raises(NotebookError):
        addresses.picture("../x", "s")
    with pytest.raises(ValueError):
        addresses.replay("body-lab", "body-2", 0, "s")
