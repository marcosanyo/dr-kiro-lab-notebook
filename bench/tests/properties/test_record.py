"""P15: a sealed record verifies, and flipping any byte of any file makes verification fail and names the
entry or blob that does not match (Requirements 13.3, 13.4, 16.4)."""

import shutil
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from bench.record import chain
from bench.record.chain import VerifyError, verify
from bench.record.store import Store, authored

json_leaf = (
    st.none()
    | st.booleans()
    | st.integers(min_value=-(2**53), max_value=2**53)
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=20)
)
json_value = st.recursive(
    json_leaf,
    # "blob" is the key of a blob reference, so plain values never use it.
    lambda inner: (
        st.lists(inner, max_size=4)
        | st.dictionaries(st.text(max_size=8).filter(lambda k: k != "blob"), inner, max_size=4)
    ),
    max_leaves=12,
)
author = st.sampled_from(["bench", "dr-kiro"])
entry_spec = st.tuples(
    st.sampled_from(sorted(chain.ENTRY_KINDS - {"seal"})),
    json_value,
    st.lists(st.tuples(st.binary(max_size=40), author), max_size=2),
    st.tuples(author, st.text(max_size=30)),
)


def _build(folder: Path, specs: list) -> Path:
    state = folder / "state"
    state.mkdir()
    store = Store.create(state / "session")
    for kind, value, blobs, (text_author, text) in specs:
        refs = [store.put_blob(data, a, "application/octet-stream") for data, a in blobs]
        store.append(kind, {"value": value, "blobs": refs, "text": authored(text_author, text)})
    store.append("seal", {"end": "ended"})
    store.close()
    sealed = folder / "sealed"
    sealed.mkdir()
    shutil.copy2(store.folder / chain.LOG_NAME, sealed / chain.LOG_NAME)
    shutil.copytree(store.folder / chain.BLOB_DIR, sealed / chain.BLOB_DIR)
    return sealed


@settings(max_examples=150, deadline=None)
@given(
    specs=st.lists(entry_spec, min_size=1, max_size=6),
    pick=st.floats(min_value=0, max_value=1, exclude_max=True),
    where=st.floats(min_value=0, max_value=1, exclude_max=True),
    mask=st.integers(min_value=1, max_value=255),
)
def test_any_flipped_byte_is_found(specs: list, pick: float, where: float, mask: int) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        sealed = _build(Path(tmp), specs)
        verify(sealed, sealed=True)

        files = [sealed / chain.LOG_NAME] + sorted((sealed / chain.BLOB_DIR).iterdir())
        files = [f for f in files if f.stat().st_size > 0]
        target = files[int(pick * len(files))]
        data = bytearray(target.read_bytes())
        offset = int(where * len(data))
        data[offset] ^= mask
        target.write_bytes(bytes(data))

        try:
            verify(sealed, sealed=True)
        except VerifyError as error:
            if target.name == chain.LOG_NAME:
                line = bytes(data[:offset]).count(b"\n") + 1
                assert error.where == f"{chain.LOG_NAME} line {line}"
            else:
                assert error.where == f"{chain.BLOB_DIR}/{target.name}"
        else:
            raise AssertionError(f"flipped byte {offset} of {target.name} was not found")
