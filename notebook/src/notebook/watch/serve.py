"""The loopback server of the watch (Requirement 23.3, 23.4; design Component 13, N33, N36).

This is the only module of the notebook that may import `http` (Open question 3, approved by the user;
`pyproject.toml` has a per-file exception for this file alone). It binds 127.0.0.1 only and answers GET
only, on fixed routes: the session page at `/` and at `/<app>-<session>.html`, `/version`, the files in
`static` (the legend and the assets) and `/p/<sha256>.png` for each picture the current version names.
When the watch was given a built site (`--site`), `/site/<path>` answers with that file of the site, read
when asked and only from inside that folder, so the link to the session's finished page works (23.14).
Every other path gets 404 and every other method 405. It writes no file; the assets were read at start and
the latest version is held in memory. `Server.run` polls the watch every 500 ms in the calling thread.
"""

import json
import threading
from collections.abc import Mapping
from http import HTTPStatus
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from notebook import addresses
from notebook.watch.versions import Version, Watch

HOST = "127.0.0.1"
POLL_SECONDS = 0.5  # N36: the builder's choice, not a requirement
ASSETS = Path(__file__).resolve().parent / "assets"
HTML = "text/html; charset=utf-8"
_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
    ".png": "image/png",
    ".html": HTML,
    ".json": "application/json",
}
SITE = "/site/"
Static = Mapping[str, tuple[bytes, str]]


def content_type(name: str) -> str:
    return _TYPES[Path(name).suffix]


def load_assets(site_assets: Path) -> dict[str, tuple[bytes, str]]:
    """Read the files of `a/` once, at start: the stylesheet, the script, the typefaces with their licence,
    and `watch.js` when the package has it (task 26.3 writes it). A file that is named and missing fails."""
    out: dict[str, tuple[bytes, str]] = {}
    for path, name in ((addresses.STYLESHEET, "notebook.css"), (addresses.SCRIPT, "notebook.js")):
        out["/" + path] = ((site_assets / name).read_bytes(), content_type(name))
    for name in addresses.FONT_FILES:
        out[f"/{addresses.ASSET_DIR}/{name}"] = (
            (site_assets / "fonts" / name).read_bytes(),
            content_type(name),
        )
    out["/" + addresses.FONT_LICENSE] = (
        (site_assets / "fonts" / "LICENSE.txt").read_bytes(),
        content_type("a.txt"),
    )
    refresh = ASSETS / "watch.js"
    if refresh.is_file():
        out[f"/{addresses.ASSET_DIR}/watch.js"] = (refresh.read_bytes(), content_type("watch.js"))
    return out


class _Handler(BaseHTTPRequestHandler):
    server: "_Http"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """No access log: the watch writes nothing and prints nothing about requests."""

    def _send(self, status: int, body: bytes, kind: str, extra: Mapping[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        found = self.server.owner.route(self.path)
        if found is None:
            self._send(HTTPStatus.NOT_FOUND, b"not found\n", "text/plain; charset=utf-8")
        else:
            self._send(HTTPStatus.OK, *found)

    def _refuse(self) -> None:
        self._send(
            HTTPStatus.METHOD_NOT_ALLOWED, b"GET only\n", "text/plain; charset=utf-8", {"Allow": "GET"}
        )

    do_HEAD = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _refuse


class _Http(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int, owner: "Server") -> None:
        self.owner = owner
        super().__init__((HOST, port), _Handler)


class Server:
    """The server and its poll loop. `static` maps a path to (bytes, type)."""

    def __init__(self, watch: Watch, static: Static, port: int, site: Path | None = None) -> None:
        self.watch = watch
        self.static = dict(static)
        self.site = None if site is None else site.resolve()
        self.version = watch.poll()  # the first pass, before anything is served
        self._page_path = ""
        self._index(self.version)
        self._stop = threading.Event()
        self._http = _Http(port, self)
        self.port = self._http.server_address[1]
        self._thread = threading.Thread(target=self._http.serve_forever, daemon=True)

    def _index(self, version: Version) -> None:
        if version.number:
            start = self.watch.entries[0]["body"]
            self._page_path = f"/{start['application']}-{start['session']}.html"
        self.version = version  # one immutable version at a time, so a reader never sees a mix

    def route(self, path: str) -> tuple[bytes, str] | None:
        version = self.version
        if path in self.static:
            return self.static[path]
        if path == "/version":
            body = json.dumps(
                {"version": version.number, "stop": None if version.stop is None else str(version.stop)}
            )
            return body.encode("utf-8"), "application/json"
        if version.number and path in ("/", self._page_path):
            return version.page, HTML
        data = {"/" + p.path: p.data for p in version.pictures}.get(path)
        if data is not None:
            return data, content_type(path)
        if self.site is not None and path.startswith(SITE):
            wanted = (self.site / path[len(SITE) :]).resolve()
            if wanted.is_relative_to(self.site) and wanted.is_file() and wanted.suffix in _TYPES:
                return wanted.read_bytes(), content_type(wanted.name)
        return None

    def start(self) -> None:
        self._thread.start()

    def run(self) -> None:
        """Poll every 500 ms until `stop`. A failure of the watch ends the loop, closes the server and is
        raised here (rules.md 2)."""
        self.start()
        try:
            while not self._stop.wait(POLL_SECONDS):
                self._index(self.watch.poll())
        finally:
            self.close()

    def stop(self) -> None:
        self._stop.set()

    def close(self) -> None:
        if self._thread.is_alive():
            self._http.shutdown()
            self._thread.join()
        self._http.server_close()


def fetch(port: int, path: str, method: str = "GET") -> tuple[int, dict[str, str], bytes]:
    """One request to the server on 127.0.0.1, for the tests. It is here because no other file of the
    notebook may import `http`."""
    connection = HTTPConnection(HOST, port, timeout=10)
    try:
        connection.request(method, path)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()
