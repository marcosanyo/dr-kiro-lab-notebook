#!/bin/sh
# Run the bench tests and ruff, and report the counts on one line.
# Used by the Kiro hook .kiro/hooks/bench-check-after-task.json after each spec task; also runs by hand:
#   sh bench/scripts/check.sh
# POSIX sh, so it runs the same on macOS and Linux. Needs uv on PATH. Exits 1 if anything fails.

cd "$(dirname "$0")/.." || exit 2

tests_out=$(uv run --quiet pytest -q -p no:cacheprovider 2>&1)
tests_status=$?
tests_line=$(printf '%s\n' "$tests_out" | grep -E '[0-9]+ (passed|failed|error)' | tail -n 1 | sed 's/=//g; s/^ *//; s/ *$//')
[ -n "$tests_line" ] || tests_line="no test summary (pytest exit $tests_status)"

lint_out=$(uv run --quiet ruff check --quiet --output-format=concise . 2>&1)
lint_status=$?
lint_count=$(printf '%s\n' "$lint_out" | grep -c ':[0-9]*:[0-9]*: ')

format_out=$(uv run --quiet ruff format --check --quiet . 2>&1)
format_status=$?
format_count=$(printf '%s\n' "$format_out" | grep -c '^Would reformat')

summary="bench check: tests: $tests_line | ruff check: $lint_count problem(s) | ruff format: $format_count file(s) to reformat"

if [ "$tests_status" -eq 0 ] && [ "$lint_status" -eq 0 ] && [ "$format_status" -eq 0 ]; then
    echo "$summary"
    exit 0
fi

# On failure the details go to stderr, which Kiro passes to the agent.
{
    echo "$summary"
    [ "$tests_status" -eq 0 ] || printf '%s\n' "$tests_out" | grep -E '^(FAILED|ERROR)' | head -n 20
    [ "$lint_status" -eq 0 ] || printf '%s\n' "$lint_out" | head -n 20
    [ "$format_status" -eq 0 ] || printf '%s\n' "$format_out" | head -n 20
} >&2
exit 1
