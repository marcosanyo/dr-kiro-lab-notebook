#!/bin/sh
# Exit 2 (block) when the tool name contains run_experiment. Hook JSON on stdin.
name="$(jq -r '.tool_name // empty')" || exit 1
case "$name" in
  *run_experiment*) echo "Blocked: run_experiment is disabled by this hook." >&2; exit 2 ;;
esac
exit 0
