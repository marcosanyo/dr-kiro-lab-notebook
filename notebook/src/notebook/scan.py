"""The bench Scanner over segments and finished files (design 11, N7; Requirements 12.8, 20.1, 20.2).

The scanner is the bench's own, `bench.scan.scan.Scanner.from_config(scan_configs, stop_list)`; this module
adds no term, pattern or exception of its own. Two passes, both before anything is written:

1. `segment_findings`: every segment at the level of its scan author (`ink.SCAN_AUTHOR`, then the bench's
   `AUTHOR_LEVEL`), named by the segment's source, so a finding names the file and line the text comes from.
2. `file_findings`: every finished text file, cut into the pieces its author ranges describe, exactly as the
   bench's `sidecar_pieces` cuts a file with its `<file>.authors.json` sidecar. So the escaped forms the site
   holds pass the scan the sidecars describe.

Extra segments that are scanned but are not a file of their own: the choice reasons (`choice_segments`) and
Dr. Kiro's fixed words, the verdict word and Dr. Kiro's label of a prediction, at the builder level
(`drkiro_word_segments`, design N29).

`check` runs both passes over a set of files and raises one `ScanFailed` that holds every finding; it never
stops at the first. The command line prints the error in full and exits 1 (design "Error Handling").
"""

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from bench.record.chain import LOG_NAME
from bench.scan.levels import AUTHOR_LEVEL, Piece
from bench.scan.scan import Finding, Scanner
from bench.scan.terms import ScanError

from notebook.choices import Choices, Cover
from notebook.errors import NotebookError
from notebook.ink import SCAN_AUTHOR, Segment, commentary, join, pencil
from notebook.records import RecordModel

WHERE = "blind scan"


class ScanFailed(NotebookError):
    """The blind scan found something. `findings` holds every finding of both passes, in the bench's
    format."""

    def __init__(self, findings: Sequence[Finding]) -> None:
        if not findings:
            raise ValueError("ScanFailed needs at least one finding")
        self.findings = tuple(findings)
        lines = "\n".join(str(f) for f in self.findings)
        super().__init__(WHERE, f"{len(self.findings)} finding(s); nothing was written\n{lines}")


def load(scan_configs: Sequence[Path], stop_list: Path) -> Scanner:
    """The bench scanner for these applications and this stop list. A scan that cannot run fails the build."""
    if not scan_configs:
        raise NotebookError("--scan-config", "the scan needs at least one application's scan_sources.toml")
    try:
        return Scanner.from_config(list(scan_configs), stop_list)
    except ScanError as error:
        raise NotebookError(WHERE, str(error)) from error


def level(segment: Segment) -> str:
    """The scan level of a segment: Dr. Kiro's ink at the Dr. Kiro level, every other ink at the builder
    level."""
    return AUTHOR_LEVEL[SCAN_AUTHOR[segment.ink]]


def segment_findings(scanner: Scanner, segments: Iterable[Segment]) -> list[Finding]:
    """Pass 1: every segment at its author's level, named by its source (Requirement 20.2)."""
    findings: list[Finding] = []
    for segment in segments:
        findings += scanner.scan_text(segment.text, level(segment), segment.source)
    return findings


def file_pieces(path: str, text: str, ranges: Sequence[Mapping[str, int | str]]) -> list[Piece]:
    """The pieces of a finished file through its author ranges, as `sidecar_pieces` builds them from the
    sidecar. The ranges come from `ink.join`; ranges that do not cover the text in order fail the build."""
    pieces: list[Piece] = []
    position = 0
    for item in ranges:
        start, end, author = item["start"], item["end"], item["author"]
        if author not in AUTHOR_LEVEL:
            raise NotebookError(path, f"author range with unknown author {author!r}")
        if start != position or not isinstance(end, int) or end <= start:
            raise NotebookError(path, "author ranges must cover the file in order without gaps")
        pieces.append(Piece(text[start:end], AUTHOR_LEVEL[author], path, text.count("\n", 0, start) + 1))
        position = end
    if position != len(text):
        raise NotebookError(path, f"author ranges cover {position} of {len(text)} characters")
    return pieces


def file_findings(
    scanner: Scanner, path: str, text: str, ranges: Sequence[Mapping[str, int | str]]
) -> list[Finding]:
    """Pass 2: a finished text file through its author ranges."""
    findings: list[Finding] = []
    for piece in file_pieces(path, text, ranges):
        findings += scanner.scan_piece(piece)
    return findings


def choice_segments(chosen: Iterable[Choices], cover: Cover | None = None) -> list[Segment]:
    """Every text a person wrote in the choice files and the cover file as a builder-level segment, so each
    one is scanned whether or not a page shows it (Requirement 12.8)."""
    out: list[Segment] = []
    for choices in chosen:
        file = choices.file
        for key in ("title", "subtitle", "summary", "line", "model", "date"):
            out.append(commentary(getattr(choices, key), f"{file} key {key}"))
        for polaroid in choices.polaroids:
            out.append(commentary(polaroid.heading, f"{polaroid.source} heading"))
            out.append(commentary(polaroid.words, f"{polaroid.source} words"))
    if cover is not None:
        for lab in cover.labs:
            out.append(commentary(lab.case, f"{lab.source} case"))
            out.append(commentary(lab.about, f"{lab.source} about"))
            out.append(commentary(lab.unit, f"{lab.source} unit"))
    return out


def drkiro_word_segments(loaded: Iterable[RecordModel]) -> list[Segment]:
    """Every verdict word and every Dr. Kiro label of a prediction in the records, as builder-level segments
    (pencil, scan author `bench`). Dr. Kiro passed these words to the bench, which recorded them as plain
    strings after checking them, so they carry no author. The pages show them in Dr. Kiro's ink and the scan
    reads them there at Dr. Kiro's level; this adds the builder level, whether or not a page shows them
    (Requirement 4.2, the exception for fixed words; design 8, 11, N29)."""
    out: list[Segment] = []
    for record in loaded:
        log = f"{record.name}/{LOG_NAME}"
        for hypothesis in record.hypotheses:
            for prediction in hypothesis.predictions:
                out.append(pencil(prediction.label, f"{log} line {hypothesis.seq}"))
        for verdict in record.verdicts:
            out.append(pencil(verdict.verdict, f"{log} line {verdict.seq}"))
    return out


def check(
    scanner: Scanner, files: Mapping[str, Sequence[Segment]], extra: Iterable[Segment] = ()
) -> dict[str, tuple[str, list[dict[str, int | str]]]]:
    """Both passes over every file (site path -> segments) and over `extra` segments that are scanned but
    not a file of their own (choice reasons, and Dr. Kiro's fixed words at the builder level). Returns each
    file's joined text and author ranges. Raises one
    `ScanFailed` with every finding of both passes if there is any."""
    findings = segment_findings(scanner, extra)
    joined: dict[str, tuple[str, list[dict[str, int | str]]]] = {}
    for path in sorted(files):
        segments = files[path]
        findings += segment_findings(scanner, segments)
        written, ranges = join(list(segments))
        findings += file_findings(scanner, path, written, ranges)
        joined[path] = (written, ranges)
    if findings:
        raise ScanFailed(findings)
    return joined
