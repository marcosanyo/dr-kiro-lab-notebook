"""The watch's versions (Requirement 23.1, 23.4, 23.6; design Component 13, N36, N37).
`Watch.poll` reads the complete lines the reader accepts; when there is a new entry it makes one
version: the model of the record so far (`records.from_entries`), its session page in `at_bench` mode
(`pages.shelf.at_bench_page`, the same page code as the build), the picture check of every trial's sheet
(`layouts.check_sheet`) and both passes of the build's blind scan (`scan.check`, the same scanner). The
version is held in memory and nothing is written. A finding stops the watch at the entry it belongs to and
the stop names the entry number and the kind of finding, never the text. A stopped watch keeps the last
version that passed and makes no new one.
"""

import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from bench.scan.scan import Scanner

from notebook import layouts, records, scan, text
from notebook.choices import App
from notebook.errors import NotebookError
from notebook.pages import shelf
from notebook.pages.photo import PictureFile
from notebook.watch.reader import Reader, ReplayReader, Stop

_FINDING_TEXT = {
    "term": text.WATCH_FOUND_TERM,
    "path": text.WATCH_FOUND_PATH,
    "file name": text.WATCH_FOUND_FILE_NAME,
    "credential": text.WATCH_FOUND_CREDENTIAL,
}
_ENTRY = re.compile(r"log\.jsonl line (\d+)$")


@dataclass(frozen=True)
class Version:
    """One version the server can read. `number` is 0 until a version has passed; `page` is the page's HTML as
    UTF-8; `pictures` are the pictures it names; `stop` is the stop of the watch, or None."""

    number: int
    page: bytes
    pictures: tuple[PictureFile, ...]
    stop: Stop | None


class Watch:
    def __init__(
        self,
        folder: Path,
        app: App,
        table: dict[str, layouts.Layout],
        scanner: Scanner,
        *,
        allow_fake: bool = False,
        replay: float | None = None,
        finished: str | None = None,
    ) -> None:
        self.reader: Reader | ReplayReader = (
            Reader(folder) if replay is None else ReplayReader(folder, replay)
        )
        self.replay, self.finished = replay is not None, finished
        self.app, self.table, self.scanner, self.allow_fake = app, table, scanner, allow_fake
        self.entries: list[dict[str, Any]] = []
        self.version = Version(0, b"", (), None)

    def poll(self) -> Version:
        """One pass: the version after it. A pass that accepts no entry returns the version as it was."""
        if self.version.stop is not None:
            return self.version
        new = self.reader.poll()
        if new:
            self.entries += new
            self._make()
        if self.version.stop is None and self.reader.stop is not None:
            self.version = replace(self.version, stop=self.reader.stop)
        return self.version

    def _stop(self, line: int, problem: str) -> None:
        self.version = replace(self.version, stop=Stop(line, problem))

    def _make(self) -> None:
        newest = self.entries[-1]["seq"]
        folder = self.reader.folder
        # A record so far that does not replay into a page stops the watch at the newest entry with a fixed
        # text (design N37); the error's own words may quote the record, so they are not shown.
        try:
            record = records.from_entries(folder, folder.name, list(self.entries), allow_fake=self.allow_fake)
            layout = layouts.layout_for(self.table, record.application, record.name)
        except NotebookError:
            self._stop(newest, text.WATCH_NO_PAGE)
            return
        # The bench's flag counts the predictions it did not run (23.10): at the flag, the hypothesis must
        # have exactly that many predictions with no outcome entry before it.
        for flag in record.flags:
            hypothesis = next(e.hypothesis for e in record.experiments if e.id == flag.experiment)
            owner = next(h for h in record.hypotheses if h.id == hypothesis)
            done = {o.prediction for o in record.outcomes if o.seq < flag.seq}
            waiting = sum(1 for p in owner.predictions if p.id not in done)
            if waiting != dict(flag.counts)["not-run"]:
                self._stop(flag.seq, text.WATCH_NOT_RUN_COUNT)
                return
        for trial in record.trials:
            try:
                layouts.check_sheet(layout, record.name, trial.id, trial.picture.media, trial.picture.data)
            except NotebookError:
                self._stop(trial.seq, text.WATCH_FOUND_PICTURE)
                return
        try:
            finished = self.finished if record.seal is not None else None
            segments, pictures = shelf.at_bench_page(
                record, self.app, self.table, {}, replay=self.replay, finished=finished
            )
        except NotebookError:
            self._stop(newest, text.WATCH_NO_PAGE)
            return
        path = f"{self.app.slug}-{record.session}.html"
        try:
            joined = scan.check(self.scanner, {path: segments}, scan.drkiro_word_segments([record]))
        except scan.ScanFailed as failed:
            # A pass 1 finding belongs to the entry its source names; a pass 2 finding, or one of builder
            # text that is no entry's, belongs to the newest entry of this pass.
            found = [(_entry_of(f.file, newest), f) for f in failed.findings]
            line, first = min(found, key=lambda pair: pair[0])
            kind = _FINDING_TEXT.get(first.kind)
            if kind is None:
                raise NotebookError("blind scan", "a finding of a kind the watch does not know") from None
            self._stop(line, kind)
            return
        self.version = Version(self.version.number + 1, joined[path][0].encode("utf-8"), pictures, None)


def _entry_of(source: str, newest: int) -> int:
    found = _ENTRY.search(source)
    return int(found.group(1)) if found else newest
