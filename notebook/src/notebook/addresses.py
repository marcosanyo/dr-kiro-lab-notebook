"""Every address of the site, in one place (design 9, N28).

The site is flat: every page is at the site root, and the only folders are `p/` (pictures) and `a/` (the
stylesheet and the script). So every link is relative and none contains `..` or a folder level for a page
(Requirement 3.2). Application and session ids are put into page names only when they match `SITE_ID`, lower
case only, so two addresses cannot differ by case. Ids put in a fragment are checked against the bench's id
patterns (`html.check_id`). `Site` (task 9.2) refuses two files with the same path.
"""

import re

from notebook.errors import NotebookError
from notebook.html import check_id

SITE_ID = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
_DIGEST = re.compile(r"[0-9a-f]{64}")

COVER = "index.html"
HOW = "how.html"
BUILT = "built.html"
LEGEND = "legend.html"
PICTURE_DIR = "p"
ASSET_DIR = "a"
STYLESHEET = f"{ASSET_DIR}/notebook.css"
SCRIPT = f"{ASSET_DIR}/notebook.js"
# The typefaces and their licence, served from the site itself (the stylesheet names them without a folder).
FONT_FILES = (
    "caveat-700.woff2",
    "lora-400.woff2",
    "lora-600.woff2",
    "plex-mono-400.woff2",
    "plex-mono-600.woff2",
)
FONT_LICENSE = f"{ASSET_DIR}/fonts-license.txt"


def site_id(kind: str, text: str, source: str) -> str:
    """`text` if it can be part of a page name; otherwise the build fails, naming the id (design 9)."""
    if not isinstance(text, str) or SITE_ID.fullmatch(text) is None:
        raise NotebookError(
            source, f"the {kind} id {text!r} does not match {SITE_ID.pattern}, so it cannot name a page"
        )
    return text


def lab(application: str, source: str) -> str:
    """The lab page `<app>.html`."""
    return f"{site_id('application', application, source)}.html"


def session(application: str, session_id: str, source: str) -> str:
    """The session page `<app>-<session>.html`."""
    app = site_id("application", application, source)
    return f"{app}-{site_id('session', session_id, source)}.html"


def replay(application: str, session_id: str, step: int, source: str) -> str:
    """Replay step `step` (1-based) of a session, `<app>-<session>-replay-<n>.html`."""
    if not isinstance(step, int) or isinstance(step, bool) or step < 1:
        raise ValueError(f"a replay step is a whole number from 1, got {step!r}")
    app = site_id("application", application, source)
    return f"{app}-{site_id('session', session_id, source)}-replay-{step}.html"


def picture(digest: str, source: str) -> str:
    """A picture, `p/<sha256>.png`."""
    if not isinstance(digest, str) or _DIGEST.fullmatch(digest) is None:
        raise NotebookError(
            source, f"{digest!r} is not a SHA-256 in lower-case hex, so it cannot name a picture"
        )
    return f"{PICTURE_DIR}/{digest}.png"


# Fragments on a session page (design 9, "Anchors").


def row(row_id: str, source: str) -> str:
    """`row-<id>`, the id of a table row."""
    return f"row-{check_id('row', row_id, source)}"


def experiment(experiment_id: str, source: str) -> str:
    """`E<n>`, the id of an experiment entry."""
    return check_id("experiment", experiment_id, source)


def trial(experiment_id: str, trial_id: str, source: str) -> str:
    """`E<n>-T<n>`, a trial inside its experiment entry."""
    return f"{experiment(experiment_id, source)}-{check_id('trial', trial_id, source)}"


def outcome(experiment_id: str, prediction_id: str, source: str) -> str:
    """`E<n>-H<n>.P<n>`, a prediction's outcome inside its experiment entry."""
    return f"{experiment(experiment_id, source)}-{check_id('prediction', prediction_id, source)}"


def experiment_file(experiment_id: str, source: str) -> str:
    """`E<n>-file`, the experiment file inside its experiment entry."""
    return f"{experiment(experiment_id, source)}-file"


def never_run(prediction_id: str, source: str) -> str:
    """`H<n>.P<n>`, a prediction that was never run."""
    return check_id("prediction", prediction_id, source)


def here(fragment: str) -> str:
    """A link to `fragment` on the same page."""
    return f"#{fragment}"


def on_page(page: str, fragment: str) -> str:
    """A link to `fragment` on another page of the site."""
    return f"{page}#{fragment}"
