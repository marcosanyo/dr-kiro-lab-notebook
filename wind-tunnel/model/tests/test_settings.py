import re

import pytest

from wind_tunnel_model.settings import (
    ESTIMATOR_MAX_DT,
    SETTINGS_PATH,
    Settings,
    SettingsError,
    frame_times,
)

REAL = SETTINGS_PATH.read_text()


def load_text(tmp_path, text):
    path = tmp_path / "constants.toml"
    path.write_text(text)
    return Settings.load(path)


def replace_line(key, new_line):
    """The real file with the one line that starts with `key =` replaced."""
    text, count = re.subn(rf"^{key} = .*$", new_line, REAL, flags=re.MULTILINE)
    assert count == 1
    return text


def test_real_file_loads():
    s = Settings.load()
    assert s.flow.reynolds == 150.0
    assert (s.domain.ahead, s.domain.behind, s.domain.above_below) == (6.0, 18.0, 7.0)
    assert (s.time.end, s.time.average_from, s.time.max_co) == (150.0, 80.0, 0.8)
    assert s.run.processes == 3 and s.run.timeout_s == 140.0
    assert s.body.thickness == 0.08 and s.body.min_edge == 0.0
    assert s.time.max_delta_t <= ESTIMATOR_MAX_DT


def test_real_file_frame_times():
    assert frame_times(Settings.load()) == (145.0, 146.0, 147.0, 148.0, 149.0, 150.0)


def test_missing_key_is_refused(tmp_path):
    with pytest.raises(SettingsError, match=r"flow\.density"):
        load_text(tmp_path, REAL.replace("density = 1.0\n", ""))


def test_extra_key_is_refused(tmp_path):
    with pytest.raises(SettingsError, match=r"flow\.viscosity"):
        load_text(tmp_path, REAL.replace("[flow]\n", "[flow]\nviscosity = 1.0\n"))


def test_placeholder_string_is_refused(tmp_path):
    with pytest.raises(SettingsError, match=r"image\.tag"):
        load_text(tmp_path, replace_line("tag", 'tag = "<chosen later>"'))


def test_wrong_type_is_refused(tmp_path):
    with pytest.raises(SettingsError, match=r"flow\.reynolds"):
        load_text(tmp_path, replace_line("reynolds", 'reynolds = "150"'))
    with pytest.raises(SettingsError, match=r"run\.processes"):
        load_text(tmp_path, replace_line("processes", "processes = 3.0"))


def test_max_delta_t_above_estimator_limit_is_refused(tmp_path):
    with pytest.raises(SettingsError, match=r"time\.max_delta_t"):
        load_text(tmp_path, replace_line("max_delta_t", "max_delta_t = 0.051  # too large"))


def test_frames_must_equal_rows_times_columns(tmp_path):
    with pytest.raises(SettingsError, match=r"picture\.frames"):
        load_text(tmp_path, replace_line("frames", "frames = 5"))


def test_first_frame_before_average_from_is_refused(tmp_path):
    with pytest.raises(SettingsError, match=r"picture\.frames"):
        load_text(tmp_path, replace_line("average_from", "average_from = 146.0"))


def test_with_reynolds_returns_a_copy():
    original = Settings.load()
    changed = original.with_reynolds(100.0)
    assert changed.flow.reynolds == 100.0
    assert original.flow.reynolds == 150.0
    assert changed.time == original.time
