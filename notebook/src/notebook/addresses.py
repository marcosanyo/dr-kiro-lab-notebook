"""Every address of the site, in one place (design 9, N28).
The site root holds the front page and one folder per application. A folder is flat: its pages are in it, and
its only folders are `p/` (pictures) and `a/` (the stylesheet, the script and the typefaces); the root has its
own `a/`. So every link is relative and none contains `..`, except the two forms that go from an application
to the front page or to another application: `/` and `/<application>/` (the site is served at its root).
Application and session ids are put into page names only when they match `SITE_ID`, lower case only, so two
addresses cannot differ by case. Ids put in a fragment are checked against the bench's id patterns
(`html.check_id`). `Site` refuses two files with the same path.
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
RESERVED = (COVER, HOW, BUILT, LEGEND)
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


def session(application: str, session_id: str, source: str) -> str:
    """The session page `<session>.html` inside its application's folder. Both ids are checked; a session
    cannot be named like a page of the folder."""
    site_id("application", application, source)
    sid = site_id("session", session_id, source)
    if f"{sid}.html" in RESERVED:
        raise NotebookError(source, f"the session id {sid!r} is the name of a page of the site")
    return f"{sid}.html"


def door(application: str, source: str) -> str:
    """The folder of an application, as the front page links it (relative, downward)."""
    return f"{site_id('application', application, source)}/{COVER}"


def apps_link(application: str, source: str) -> str:
    """The link from inside one application to another, or to the front page when `application` is empty.
    The applications are folders of the site root, so these two forms are the only links that are not
    relative (design, "Pages"): `/` and `/<application>/`."""
    if not application:
        return "/"
    return f"/{site_id('application', application, source)}/"


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
