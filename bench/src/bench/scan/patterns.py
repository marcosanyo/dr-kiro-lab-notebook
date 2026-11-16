"""Path, file name and credential patterns of the blind scan (design 11.2). Scanned at both levels.

Absolute paths are recognised by their root folder, not by any `/x/y`, so that division in experiment code
(`(t + a)/period/2`) is not mistaken for a path.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from bench.scan.tokens import term_tokens


@dataclass(frozen=True)
class Match:
    start: int
    end: int
    kind: str  # "path" | "file name" | "credential"
    text: str


ROOTS = (
    "home", "root", "etc", "tmp", "usr", "var", "opt", "mnt", "srv", "dev", "proc", "sys", "bin", "lib",
    "private", "projects", "workspace", "app", "Users", "Volumes",
)  # fmt: skip

_PATHS = [
    re.compile(r"(?<![\w.])\.\.(?=[/\\])"),
    re.compile(rf"(?<![\w.~/:-])/(?:{'|'.join(ROOTS)})(?=/|\b)[\w./-]*"),
    re.compile(r"(?<![\w/])~/[\w./-]*"),
    re.compile(r"(?<![\w])[A-Za-z]:\\[\w.\\ -]*"),
    re.compile(r"(?i)(?<![\w-])(?:model|adapter)[/\\]"),
]

_CREDENTIALS = [
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}"),
    re.compile(
        r"(?i)(?<![A-Za-z0-9])(?:api[_-]?key|secret|token|password|passwd|access[_-]?key)(?![A-Za-z0-9])"
        r"[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9/+=_-]{16,}"
    ),
]


def redact(text: str) -> str:
    return text[:4] + "…" if len(text) > 4 else "…"


class Patterns:
    def __init__(
        self,
        file_names: Iterable[str],
        solver_dirs: Iterable[str],
        local_paths: Iterable[str],
        stop_list: Iterable[str] = (),
    ) -> None:
        """`local_paths` are absolute paths of this machine (the home folder, the repository) that are flagged
        wherever they appear, whatever their root.

        A file name is matched in full, always. Its stem (the part before the first dot) is matched too,
        unless the stem is one character, or is on the stop list (compared as the stop list is compared for
        terms: in token form, so case does not matter). A name without a dot has no separate stem: it is a
        full name and is always matched, even when it is one character or on the stop list (design C1)."""
        stop = {term_tokens(w) for w in stop_list}
        paths = sorted({p.rstrip("/") for p in local_paths if len(p.rstrip("/")) > 1}, key=len, reverse=True)
        self._local = [re.compile(rf"{re.escape(p)}(?![\w-])") for p in paths]
        names: set[str] = set()
        for name in file_names:
            names.add(name)
            stem = name.split(".", 1)[0]
            if stem != name and len(stem) > 1 and term_tokens(stem) not in stop:
                names.add(stem)
        self._names = [
            re.compile(rf"(?i)(?<![\w.-]){re.escape(n)}(?![\w-])")
            for n in sorted(names, key=len, reverse=True)
            if n
        ]
        self._dirs = [re.compile(rf"(?i)(?<![\w-]){re.escape(d)}[/\\]") for d in sorted(set(solver_dirs))]

    def find(self, text: str) -> list[Match]:
        found: list[Match] = []
        spans = {
            (m.start(), m.end())
            for pattern in _PATHS + self._dirs + self._local
            for m in pattern.finditer(text)
        }
        # One path is reported once: drop a span that lies inside a longer span found by another pattern.
        for start, end in sorted(spans):
            inside = any(s <= start and end <= e and (s, e) != (start, end) for s, e in spans)
            if not inside:
                found.append(Match(start, end, "path", text[start:end]))
        for pattern in self._names:
            found += [Match(m.start(), m.end(), "file name", m.group()) for m in pattern.finditer(text)]
        for pattern in _CREDENTIALS:
            found += [
                Match(m.start(), m.end(), "credential", redact(m.group())) for m in pattern.finditer(text)
            ]
        return sorted(found, key=lambda m: (m.start, m.kind))
