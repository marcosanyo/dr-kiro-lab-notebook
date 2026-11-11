"""Append-only session record in the bench state folder (Requirements 9.3-9.5, design 9.1).

The log is opened in append mode only, every write is flushed and synced, and blobs are stored by their
SHA-256. A lock on the folder stops a second process from opening the same session. Wall-clock times go only
to `builder.log`, which is not hashed and not sealed (3.3).
"""

import fcntl
import os
import time
from pathlib import Path
from typing import IO, Any

from bench.record.canonical import canonical_json
from bench.record.chain import (
    AUTHORS,
    BLOB_DIR,
    ENTRY_KINDS,
    GENESIS,
    LOG_NAME,
    VerifyError,
    blob_refs,
    check_blob_ref,
    entry_hash,
    sha256_hex,
    verify,
)


class StoreError(RuntimeError):
    """The record could not be written or opened."""


def authored(author: str, text: str) -> dict[str, str]:
    """A text field in the record, with its author (9.5)."""
    if author not in AUTHORS:
        raise StoreError(f"unknown author {author!r}")
    if not isinstance(text, str):
        raise StoreError(f"text must be a string, got {type(text).__name__}")
    return {"author": author, "text": text}


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Store:
    """The record of one session in `<state_dir>/<session-id>/`. Use `create` or `open`."""

    def __init__(self, folder: Path, lock: IO[bytes], entries: list[dict[str, Any]]) -> None:
        self.folder = folder
        self._lock = lock
        self._entries = entries
        self._closed = False

    @staticmethod
    def _take_lock(folder: Path) -> IO[bytes]:
        lock = open(folder / ".lock", "ab")  # noqa: SIM115 - held for the life of the store
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            lock.close()
            raise StoreError(f"session folder {folder} is in use by another process") from error
        return lock

    @classmethod
    def create(cls, folder: Path) -> "Store":
        folder = Path(folder)
        if folder.exists():
            raise StoreError(f"session folder {folder} already exists")
        if not folder.parent.is_dir():
            raise StoreError(f"state folder {folder.parent} does not exist")
        folder.mkdir()
        (folder / BLOB_DIR).mkdir()
        (folder / LOG_NAME).touch()
        _fsync_dir(folder)
        _fsync_dir(folder.parent)
        return cls(folder, cls._take_lock(folder), [])

    @classmethod
    def open(cls, folder: Path) -> "Store":
        folder = Path(folder)
        if not folder.is_dir():
            raise StoreError(f"session folder {folder} does not exist")
        lock = cls._take_lock(folder)
        try:
            entries = verify(folder, sealed=False)
        except Exception:
            lock.close()
            raise
        return cls(folder, lock, entries)

    @property
    def entries(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._entries)

    @property
    def sealed(self) -> bool:
        return bool(self._entries) and self._entries[-1]["kind"] == "seal"

    def _check_open(self) -> None:
        if self._closed:
            raise StoreError("store is closed")

    def append(self, kind: str, body: dict[str, Any]) -> dict[str, Any]:
        """Append one entry and sync it to disk. Return the entry."""
        self._check_open()
        if kind not in ENTRY_KINDS:
            raise StoreError(f"unknown entry kind {kind!r}")
        if self.sealed:
            raise StoreError("the record is sealed")
        for ref in blob_refs(body):
            try:
                check_blob_ref(ref, kind)
            except VerifyError as error:
                raise StoreError(f"entry would not verify: {error}") from error
            if not (self.folder / BLOB_DIR / ref["blob"]).is_file():
                raise StoreError(f"entry references blob {ref['blob']} that is not stored")
        prev = self._entries[-1]["hash"] if self._entries else GENESIS
        entry: dict[str, Any] = {"seq": len(self._entries) + 1, "kind": kind, "body": body, "prev": prev}
        entry["hash"] = entry_hash(entry)
        line = canonical_json(entry) + b"\n"
        with open(self.folder / LOG_NAME, "ab") as log:
            log.write(line)
            log.flush()
            os.fsync(log.fileno())
        self._entries.append(entry)
        return entry

    def put_blob(self, data: bytes, author: str, media: str) -> dict[str, str]:
        """Store bytes by their SHA-256 and return the reference to put in an entry body."""
        self._check_open()
        if not isinstance(data, bytes):
            raise StoreError("blob data must be bytes")
        if author not in AUTHORS:
            raise StoreError(f"unknown author {author!r}")
        if not media:
            raise StoreError("blob needs a media type")
        digest = sha256_hex(data)
        path = self.folder / BLOB_DIR / digest
        if path.exists():
            if path.read_bytes() != data:
                raise StoreError(f"blob {digest} on disk does not match its content")
        else:
            tmp = path.with_name(f".{digest}.tmp")
            with open(tmp, "xb") as out:
                out.write(data)
                out.flush()
                os.fsync(out.fileno())
            os.rename(tmp, path)
            _fsync_dir(path.parent)
        return {"blob": digest, "author": author, "media": media}

    def read_blob(self, ref: dict[str, str]) -> bytes:
        return (self.folder / BLOB_DIR / ref["blob"]).read_bytes()

    def builder_log(self, text: str) -> None:
        """Write a line with the wall-clock time to the builder-side log. Not hashed, not sealed."""
        self._check_open()
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        with open(self.folder / "builder.log", "a", encoding="utf-8") as log:
            log.write(f"{stamp} {text}\n")

    def close(self) -> None:
        if not self._closed:
            self._lock.close()
            self._closed = True
