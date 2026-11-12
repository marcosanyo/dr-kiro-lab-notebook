"""The blind scan call and the `bench-scan` command (Requirement 15, design 11).

Builder-level text is scanned for terms, paths and file names, and credentials. Dr. Kiro-level text is
scanned for paths and file names, and credentials only: a guess written by Dr. Kiro is a hypothesis, not a
leak. The term list is derived from the sources at scan time, minus the allow list and the stop list.
"""

import argparse
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from bench.core.outcome import Message, Quote
from bench.pictures import PictureError, check_picture
from bench.scan.levels import LEVELS, SIDECAR_SUFFIX, Piece, record_pieces, sidecar_pieces
from bench.scan.patterns import Patterns
from bench.scan.terms import AppSources, LabLayout, ScanError, load_app, load_stop_list
from bench.scan.tokens import term_tokens, tokenize

PICTURE_SUFFIXES = {".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}

# Files in a bench state folder that are never part of a record and are not scanned as one.
STATE_ONLY = frozenset({"builder.log", ".lock"})


def repository_root(inside: Path) -> Path:
    """The folder holding `.git` above a path in the repository. Fail if there is none."""
    start = inside.resolve()
    for folder in (start, *start.parents):
        if (folder / ".git").exists():
            return folder
    raise ScanError(f"{inside}: not inside a git repository, so the repository path cannot be flagged")


def local_paths(inside_repository: Path) -> tuple[str, ...]:
    """This machine's home folder and the repository's absolute path, flagged wherever they appear."""
    return (str(Path.home().resolve()), str(repository_root(inside_repository)))


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    kind: str  # "term" | "path" | "file name" | "credential"
    match: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.kind}: {self.match}"


class Scanner:
    def __init__(
        self, apps: Sequence[AppSources], stop_list: Iterable[str], *, local_paths: Iterable[str]
    ) -> None:
        if not apps:
            raise ScanError("the scan needs at least one application's sources")
        stop = {term_tokens(w) for w in stop_list}
        terms: dict[tuple[str, ...], str] = {}
        for app in apps:
            allow = {term_tokens(a) for a in app.allow}
            derived = list(app.names) + list(app.file_names)
            derived += [f.split(".", 1)[0] for f in app.file_names]
            derived += [f.rsplit(".", 1)[0] for f in app.file_names]
            for name in derived:
                tokens = term_tokens(name)
                if all(t.isdigit() for t in tokens):
                    continue  # a token made only of digits is never a term
                if tokens not in allow and tokens not in stop:
                    terms.setdefault(tokens, name)
        self.terms = terms
        self._single = {t[0] for t in terms if len(t) == 1}
        self._multi: dict[str, list[tuple[str, ...]]] = {}
        for t in terms:
            if len(t) > 1:
                self._multi.setdefault(t[0], []).append(t)
        self.patterns = Patterns(
            [f for a in apps for f in a.file_names],
            [d for a in apps for d in a.solver_dirs],
            local_paths,
        )
        self.labs: list[LabLayout] = [a.lab for a in apps if a.lab is not None]

    @classmethod
    def from_config(cls, configs: Sequence[Path], stop_list: Path) -> "Scanner":
        """The scanner for these applications. The repository is the one that holds the stop list."""
        stop = load_stop_list(stop_list)
        return cls([load_app(c) for c in configs], stop, local_paths=local_paths(Path(stop_list)))

    # Text

    @staticmethod
    def _same(text_token: str, term_token: str, last: bool) -> bool:
        if text_token == term_token:
            return True
        return last and text_token in (term_token + "s", term_token + "es")

    def _base_forms(self, token: str) -> list[str]:
        forms = [token]
        if token.endswith("es"):
            forms.append(token[:-2])
        if token.endswith("s"):
            forms.append(token[:-1])
        return forms

    def find_terms(self, text: str) -> list[tuple[int, int, str]]:
        tokens = tokenize(text)
        found = []
        for i, token in enumerate(tokens):
            if any(form in self._single for form in self._base_forms(token.text)):
                found.append((token.start, token.end, text[token.start : token.end]))
            for term in self._multi.get(token.text, ()):
                window = tokens[i : i + len(term)]
                if len(window) == len(term) and all(
                    self._same(w.text, t, k == len(term) - 1)
                    for k, (w, t) in enumerate(zip(window, term, strict=True))
                ):
                    found.append((window[0].start, window[-1].end, text[window[0].start : window[-1].end]))
        return found

    def scan_piece(self, piece: Piece) -> list[Finding]:
        if piece.level not in LEVELS:
            raise ScanError(f"{piece.where}: unknown level {piece.level!r}")
        findings = [
            Finding(piece.where, piece.line_of(m.start), m.kind, m.text)
            for m in self.patterns.find(piece.text)
        ]
        if piece.level == "builder":
            findings += [
                Finding(piece.where, piece.line_of(start), "term", match)
                for start, _, match in self.find_terms(piece.text)
            ]
        return sorted(findings, key=lambda f: (f.line, f.kind, f.match))

    def scan_text(self, text: str, level: str, where: str, line: int = 1) -> list[Finding]:
        return self.scan_piece(Piece(text, level, where, line))

    def scan_message(self, message: Message, where: str) -> list[Finding]:
        """Bench wording at the builder level; quotes of Dr. Kiro's files at the Dr. Kiro level (15.8)."""
        findings: list[Finding] = []
        for span in message.spans:
            level = "dr-kiro" if isinstance(span, Quote) else "builder"
            findings += self.scan_text(span.text, level, where)
        return findings

    # Files

    def _lab_level(self, path: Path) -> str | None:
        for lab in self.labs:
            level = lab.level(path)
            if level is not None:
                return level
        return None

    def scan_file(self, path: Path) -> list[Finding]:
        level = self._lab_level(path)
        if level is not None and path.suffix.lower() in PICTURE_SUFFIXES:
            # A picture in a lab is checked as a picture, not read as text (15.9).
            try:
                check_picture(PICTURE_SUFFIXES[path.suffix.lower()], path.read_bytes())
            except PictureError as error:
                return [Finding(str(path), 1, "picture", str(error))]
            return []
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise ScanError(f"{path}: not UTF-8 text; the scan cannot read it") from error
        level = self._lab_level(path)
        if level is not None:
            return self.scan_text(text, level, str(path))
        findings: list[Finding] = []
        for piece in sidecar_pieces(path, text):
            findings += self.scan_piece(piece)
        return findings

    def scan_record(self, folder: Path) -> list[Finding]:
        findings: list[Finding] = []
        for piece in record_pieces(folder):
            findings += self.scan_piece(piece)
        return findings

    def scan_paths(self, paths: Iterable[Path]) -> list[Finding]:
        findings: list[Finding] = []
        for path in paths:
            findings += self._scan_path(Path(path))
        return findings

    def _scan_path(self, path: Path) -> list[Finding]:
        if not path.exists():
            raise ScanError(f"{path}: not found")
        if path.is_dir():
            if (path / "log.jsonl").is_file():
                return self.scan_record(path)
            findings: list[Finding] = []
            for child in sorted(path.iterdir()):
                if child.name.endswith(SIDECAR_SUFFIX):
                    continue
                findings += self._scan_path(child)
            return findings
        if path.name in STATE_ONLY and (path.parent / "log.jsonl").is_file():
            return []
        return self.scan_file(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bench-scan", description="Run the blind scan on files and folders."
    )
    parser.add_argument(
        "--config", action="append", required=True, type=Path, help="an application's scan_sources.toml"
    )
    parser.add_argument("--stop-list", required=True, type=Path, help="the reviewed stop list")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        scanner = Scanner.from_config(args.config, args.stop_list)
        findings = scanner.scan_paths(args.paths)
    except ScanError as error:
        print(f"bench-scan: {error}", file=sys.stderr)
        return 2
    for finding in findings:
        print(finding)
    if findings:
        print(f"bench-scan: {len(findings)} finding(s)", file=sys.stderr)
        return 1
    print("bench-scan: no findings")
    return 0
