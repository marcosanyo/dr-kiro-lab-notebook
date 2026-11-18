"""Unit tests for the turn loop and the headless command (design 3.10, Requirements 9.6 and 11.6)."""

import hashlib
import re
from pathlib import Path

import pytest
from bench.scan.scan import Scanner

from build_from_spec.apps import APPS
from build_from_spec.turns import (
    CONTINUE_LINE,
    IDLE_REASON,
    START_LINE,
    TurnsError,
    exit_reason,
    kiro_command,
    line_for,
    run_turns,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "build-from-spec" / "README.md"
STOP_LIST = REPO_ROOT / ".kiro" / "blind-scan" / "stop-list.txt"
TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class FakeBench:
    """A state record and a reader. Each turn adds `added` entries, seals or not, and exits with `code`."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.turn = 0
        self.count = 0
        self.sealed = False
        self.kinds: list[str] = []
        self.saves: list[tuple] = []

    def launch(self, kind):
        self.kinds.append(kind)
        code, added, sealed = self.outcomes[self.turn]
        self.turn += 1
        self.count += added
        self.sealed = sealed
        return code

    def entries(self):
        return (self.count, self.sealed)

    def save(self, prompts):
        self.saves.append(prompts)


def run(*outcomes):
    bench = FakeBench(outcomes)
    end = run_turns(bench.launch, bench.entries, bench.save)
    return bench, end


def test_first_command_has_no_resume_and_sends_the_start_line():
    command = kiro_command("start", "model-x", "high")
    assert "--resume" not in command
    assert command[-1] == START_LINE
    assert command[command.index("--model") + 1] == "model-x"
    assert command[command.index("--effort") + 1] == "high"
    assert command[command.index("--agent") + 1] == "reader"
    assert "--trust-tools=" in command
    assert "--no-interactive" in command


def test_effort_default_omits_the_effort_flag():
    command = kiro_command("start", "model-x", "default")
    assert "--effort" not in command
    assert command[command.index("--model") + 1] == "model-x"
    assert command[-1] == START_LINE


def test_effort_default_still_resumes_on_a_continue_turn():
    command = kiro_command("continue", "model-x", "default")
    assert "--effort" not in command
    assert "--resume" in command
    assert command[-1] == CONTINUE_LINE


def test_a_named_effort_other_than_default_is_passed_as_given():
    for effort in ("low", "medium", "high", "xhigh", "max"):
        command = kiro_command("start", "model-x", effort)
        assert command[command.index("--effort") + 1] == effort


def test_later_command_resumes_and_sends_the_continue_line():
    command = kiro_command("continue", "model-x", "high")
    assert "--resume" in command
    assert command[-1] == CONTINUE_LINE
    assert command[:-1] == kiro_command("start", "model-x", "high")[:-1] + ["--resume"]


@pytest.mark.parametrize("model, effort", [("", "high"), ("model-x", "")])
def test_an_empty_model_or_effort_is_refused(model, effort):
    with pytest.raises(TurnsError):
        kiro_command("start", model, effort)


def test_an_unknown_kind_is_refused():
    with pytest.raises(TurnsError, match="'retry'"):
        line_for("retry")


def test_the_lines_are_the_ones_written_in_the_readme():
    text = README.read_text(encoding="utf-8")
    assert f"`{START_LINE}`" in text
    assert f"`{CONTINUE_LINE}`" in text


def test_stop_reasons_and_lines_hold_no_forbidden_term():
    scanner = Scanner.from_config([REPO_ROOT / APPS["body-lab"].scan_sources], STOP_LIST)
    text = "\n".join(
        [START_LINE, CONTINUE_LINE, IDLE_REASON, exit_reason(7), *kiro_command("continue", "m", "e")]
    )
    assert scanner.scan_text(text, "builder", "turns.py") == []


def test_a_sealing_first_turn_ends_the_run_sealed():
    bench, end = run((0, 1, True))
    assert end.sealed is True
    assert end.stop_reason is None
    assert bench.kinds == ["start"]


def test_a_sealing_turn_with_a_non_zero_exit_is_still_sealed():
    _, end = run((3, 1, True))
    assert end.sealed is True
    assert end.stop_reason is None


def test_a_non_zero_exit_stops_at_once_with_the_exit_reason():
    bench, end = run((2, 1, False))
    assert end.sealed is False
    assert end.stop_reason == "the reader's Kiro CLI exited with code 2"
    assert bench.kinds == ["start"]


def test_a_silent_first_turn_is_followed_by_a_continue_line():
    bench, end = run((0, 0, False), (0, 1, True))
    assert bench.kinds == ["start", "continue"]
    assert end.sealed is True


def test_two_silent_turns_in_a_row_stop_with_the_idle_reason():
    bench, end = run((0, 0, False), (0, 0, False), (0, 1, True))
    assert bench.kinds == ["start", "continue"]
    assert end.stop_reason == IDLE_REASON
    assert end.sealed is False


def test_a_silent_turn_after_an_active_turn_is_followed_by_a_continue_line():
    bench, end = run((0, 2, False), (0, 0, False), (0, 1, True))
    assert bench.kinds == ["start", "continue", "continue"]
    assert end.sealed is True


def test_an_active_turn_after_a_silent_one_resets_the_idle_count():
    bench, end = run((0, 0, False), (0, 1, False), (0, 0, False), (0, 0, False))
    assert bench.kinds == ["start", "continue", "continue", "continue"]
    assert end.stop_reason == IDLE_REASON


def test_the_recorded_prompts_match_the_turns_and_the_lines_sent():
    bench, end = run((0, 0, False), (0, 2, False), (4, 1, False))
    assert len(end.prompts) == 3
    assert [p.kind for p in end.prompts] == ["start", "continue", "continue"]
    assert [p.exit for p in end.prompts] == [0, 0, 4]
    assert [(p.entries_before, p.entries_after) for p in end.prompts] == [(0, 0), (0, 2), (2, 3)]
    assert [p.sha256 for p in end.prompts] == [
        hashlib.sha256(START_LINE.encode("utf-8")).hexdigest(),
        hashlib.sha256(CONTINUE_LINE.encode("utf-8")).hexdigest(),
        hashlib.sha256(CONTINUE_LINE.encode("utf-8")).hexdigest(),
    ]
    assert all(TIME.match(p.time) for p in end.prompts)


def test_save_receives_the_prompts_so_far_after_every_turn():
    bench, end = run((0, 1, False), (0, 1, True))
    assert [len(s) for s in bench.saves] == [1, 2]
    assert bench.saves[-1] == end.prompts


def test_an_error_from_launch_is_not_swallowed():
    def launch(kind):
        raise RuntimeError("the launch failed")

    with pytest.raises(RuntimeError, match="the launch failed"):
        run_turns(launch, lambda: (0, False), lambda prompts: None)
