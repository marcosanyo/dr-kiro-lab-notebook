#!/bin/sh
# Append one line per tool call to lab/hook-log.jsonl. Usage: log.sh pre|post (hook JSON on stdin).
# Always exits 0 so that logging can never block a tool call.
LAB="$(cd "$(dirname "$0")/../.." && pwd)"
jq -c --arg phase "$1" '{ts: (now | todate), phase: $phase, tool_name: .tool_name, tool_input: .tool_input}' \
  >> "$LAB/hook-log.jsonl" 2>/dev/null
exit 0
