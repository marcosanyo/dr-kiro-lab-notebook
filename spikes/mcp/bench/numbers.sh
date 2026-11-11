#!/bin/bash
# For each ledger entry print: path, started_at, finished_at, number drawn in its picture (tab-separated).
# Usage: numbers.sh [ledger]   (default: BENCH_LEDGER, else ledger.jsonl next to this script)
set -eu
LEDGER="${1:-${BENCH_LEDGER:-$(dirname "$0")/ledger.jsonl}}"
[ -f "$LEDGER" ] || { echo "ledger not found: $LEDGER" >&2; exit 1; }
jq -r '[.path, .started_at, .finished_at, .sha256[8:16]] | @tsv' "$LEDGER" |
while IFS=$'\t' read -r path started finished hex; do
  printf '%s\t%s\t%s\t%d\n' "$path" "$started" "$finished" $((16#$hex % 900 + 100))
done
