"""build-from-spec Requirement 12.8 (design 3.14.1): records sealed before the `discovered_table` amendment
stay valid for `bench-verify` and `final_spec`.

The records are the sealed sessions in `sessions/`. Their start entries have no `discovered_table`. The test
only verifies and reads them (`verify`, `final_spec`); it never calls `Session.open`, which refuses a record
without that key. The records are read in place and not changed.

body-1 was sealed as ended before the bench recorded an end snapshot, so it has no final spec. `final_spec`
refuses it for that reason, as `test_records_without_a_final_spec_are_refused` already checks.
"""

from pathlib import Path

import pytest

from bench.record.chain import verify
from bench.record.spec_copy import SpecCopyError, final_spec

REPO = Path(__file__).resolve().parents[3]
SESSIONS = REPO / "sessions"

SEALED_BEFORE_AMENDMENT = ("body-lab/body-1", "body-lab/body-2", "wind-tunnel/wt-004")
WITH_FINAL_SPEC = ("body-lab/body-2", "wind-tunnel/wt-004")


@pytest.mark.parametrize("record", SEALED_BEFORE_AMENDMENT)
def test_bench_verify_passes_on_a_record_sealed_before_the_amendment(record: str) -> None:
    entries = verify(SESSIONS / record, sealed=True)
    assert entries[0]["kind"] == "start"
    assert "discovered_table" not in entries[0]["body"]
    assert entries[-1]["kind"] == "seal"
    assert entries[-1]["body"]["end"] == "ended"


@pytest.mark.parametrize("record", WITH_FINAL_SPEC)
def test_final_spec_reads_the_three_files_of_a_record_sealed_before_the_amendment(record: str) -> None:
    spec = final_spec(SESSIONS / record)
    assert sorted(spec.files) == ["design.md", "requirements.md", "tasks.md"]
    assert all(data for data in spec.files.values())


def test_final_spec_refuses_body_1_for_its_missing_end_snapshot() -> None:
    with pytest.raises(SpecCopyError, match="has no end snapshot"):
        final_spec(SESSIONS / "body-lab" / "body-1")
