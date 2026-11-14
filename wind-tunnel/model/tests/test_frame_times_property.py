import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from wind_tunnel_model.settings import SETTINGS_PATH, Settings, SettingsError, frame_times

REAL = SETTINGS_PATH.read_text()


def with_lines(**lines):
    """The real file with the line of each key replaced by `key = value`."""
    text = REAL
    for key, value in lines.items():
        text, count = re.subn(rf"^{key} = .*$", f"{key} = {value}", text, flags=re.MULTILINE)
        assert count == 1
    return text


def load(tmp_path, **lines):
    path = tmp_path / "constants.toml"
    path.write_text(with_lines(**lines))
    return Settings.load(path)


# Multiples of 0.25 are exact in binary floating point, so the checks below compare exactly.
quarters = st.integers(min_value=0, max_value=1200).map(lambda n: n / 4)
positive_quarters = st.integers(min_value=1, max_value=40).map(lambda n: n / 4)
counts = st.integers(min_value=1, max_value=6)


# Feature: wind-tunnel, Property 16: Frame times follow the settings
# Validates: Requirements 9.3, 9.4
@settings(max_examples=200, deadline=None)
@given(rows=counts, columns=counts, spacing=positive_quarters, end=quarters, average_from=quarters)
def test_frame_times_follow_the_settings(tmp_path_factory, rows, columns, spacing, end, average_from):
    tmp_path = tmp_path_factory.mktemp("settings")
    frames = rows * columns
    lines = {
        "rows": rows,
        "columns": columns,
        "frames": frames,
        "spacing": spacing,
        "end": end,
        "average_from": average_from,
    }
    first = end - (frames - 1) * spacing
    if first < average_from:
        with pytest.raises(SettingsError, match=r"picture\.frames"):
            load(tmp_path, **lines)
        return
    times = frame_times(load(tmp_path, **lines))
    assert len(times) == frames
    assert times[-1] == end
    assert times[0] >= average_from
    assert all(b - a == spacing for a, b in zip(times, times[1:], strict=False))
    assert all(a < b for a, b in zip(times, times[1:], strict=False))


# Feature: wind-tunnel, Property 16: Frame times follow the settings
# Validates: Requirements 9.3, 9.4
@settings(max_examples=100, deadline=None)
@given(rows=counts, columns=counts, frames=st.integers(min_value=1, max_value=40))
def test_frames_not_rows_times_columns_is_refused(tmp_path_factory, rows, columns, frames):
    if frames == rows * columns:
        return
    tmp_path = tmp_path_factory.mktemp("settings")
    with pytest.raises(SettingsError, match=r"picture\.frames"):
        load(tmp_path, rows=rows, columns=columns, frames=frames)
