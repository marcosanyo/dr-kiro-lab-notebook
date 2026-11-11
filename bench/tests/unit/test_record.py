import math
import shutil
from pathlib import Path

import pytest

from bench.record import chain
from bench.record.canonical import CanonicalError, canonical_json
from bench.record.chain import VerifyError, verify
from bench.record.store import Store, StoreError, authored


def test_canonical_json() -> None:
    assert (
        canonical_json({"b": 1, "a": [0.1, (2, 3)], "c": "ü"}) == '{"a":[0.1,[2,3]],"b":1,"c":"ü"}'.encode()
    )
    for bad in (math.nan, math.inf, {1: 2}, {"a": {1, 2}}, b"bytes", object()):
        with pytest.raises(CanonicalError):
            canonical_json(bad)


def _sealed_copy(store: Store, dest: Path) -> Path:
    dest.mkdir()
    shutil.copy2(store.folder / chain.LOG_NAME, dest / chain.LOG_NAME)
    shutil.copytree(store.folder / chain.BLOB_DIR, dest / chain.BLOB_DIR)
    return dest


def _session(tmp_path: Path) -> Store:
    (tmp_path / "state").mkdir()
    store = Store.create(tmp_path / "state" / "s1")
    ref = store.put_blob(b"picture bytes", "bench", "image/png")
    store.append("start", {"note": authored("bench", "started")})
    store.append("experiment", {"file": store.put_blob(b"# H1\n", "dr-kiro", "text/x-python"), "pic": ref})
    store.builder_log("wall-clock detail")
    store.append("seal", {"end": "ended"})
    return store


def test_sealed_record_verifies(tmp_path: Path) -> None:
    store = _session(tmp_path)
    sealed = _sealed_copy(store, tmp_path / "sealed")
    entries = verify(sealed, sealed=True)
    assert [e["kind"] for e in entries] == ["start", "experiment", "seal"]
    assert chain.main([str(sealed)]) == 0


def test_state_folder_verifies_unsealed_with_builder_log(tmp_path: Path) -> None:
    store = _session(tmp_path)
    verify(store.folder, sealed=False)
    with pytest.raises(VerifyError):
        verify(store.folder, sealed=True)  # builder.log and .lock are not part of a sealed record


def test_store_rules(tmp_path: Path) -> None:
    store = _session(tmp_path)
    with pytest.raises(StoreError, match="sealed"):
        store.append("start", {})
    with pytest.raises(StoreError, match="in use"):
        Store.open(store.folder)
    with pytest.raises(StoreError, match="already exists"):
        Store.create(store.folder)
    with pytest.raises(StoreError, match="kind"):
        Store.create(tmp_path / "state" / "s2").append("nonsense", {})
    store.close()
    reopened = Store.open(store.folder)
    assert reopened.sealed
    assert len(reopened.entries) == 3


def test_authored_needs_a_known_author() -> None:
    with pytest.raises(StoreError):
        authored("someone", "text")


def test_verify_finds_problems(tmp_path: Path) -> None:
    store = _session(tmp_path)
    sealed = _sealed_copy(store, tmp_path / "sealed")
    (sealed / "extra.txt").write_text("x")
    with pytest.raises(VerifyError, match="unexpected"):
        verify(sealed, sealed=True)
    (sealed / "extra.txt").unlink()
    planted = sealed / chain.BLOB_DIR / chain.sha256_hex(b"planted")
    planted.write_bytes(b"planted")
    with pytest.raises(VerifyError, match="not referenced"):
        verify(sealed, sealed=True)
    planted.unlink()
    first = sorted((sealed / chain.BLOB_DIR).iterdir())[0]
    first.unlink()
    with pytest.raises(VerifyError, match="missing"):
        verify(sealed, sealed=True)
    assert chain.main([str(sealed)]) == 1
    assert chain.main([]) == 2


def test_unsealed_copy_fails_sealed_check(tmp_path: Path) -> None:
    (tmp_path / "state").mkdir()
    store = Store.create(tmp_path / "state" / "s1")
    store.append("start", {})
    sealed = _sealed_copy(store, tmp_path / "copy")
    with pytest.raises(VerifyError, match="not sealed"):
        verify(sealed, sealed=True)


def test_truncated_log_fails(tmp_path: Path) -> None:
    store = _session(tmp_path)
    sealed = _sealed_copy(store, tmp_path / "sealed")
    log = sealed / chain.LOG_NAME
    lines = log.read_bytes().split(b"\n")
    log.write_bytes(b"\n".join(lines[:2]) + b"\n")
    with pytest.raises(VerifyError):
        verify(sealed, sealed=True)


def test_append_refuses_a_malformed_or_missing_blob_reference(tmp_path: Path) -> None:
    (tmp_path / "state").mkdir()
    store = Store.create(tmp_path / "state" / "s1")
    with pytest.raises(StoreError, match="would not verify"):
        store.append("start", {"x": {"blob": None}})
    with pytest.raises(StoreError, match="not stored"):
        store.append("start", {"x": {"blob": "a" * 64, "author": "bench", "media": "text/plain"}})
    assert store.entries == ()
