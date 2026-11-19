#!/bin/sh
# Build the lab notebook from the sealed records and show it at http://127.0.0.1:<port>/ .
#   sh scripts/view-notebook.sh [--port N] [--open]
# The site is built into a new empty folder under the system temporary folder, every run. A failed check stops the
# script with the build's message; nothing is served then. Stop the server with Ctrl-C.
# Needs `uv` only. The site makes no request outside itself; the server listens on 127.0.0.1 only.
# POSIX sh; runs the same on macOS and Linux.
cd "$(dirname "$0")/.." || exit 2
port=8000
open_browser=no
while [ $# -gt 0 ]; do
    case "$1" in
        --port)
            [ $# -ge 2 ] || { echo "view-notebook: --port needs a number" >&2; exit 2; }
            port="$2"
            shift 2
            ;;
        --open)
            open_browser=yes
            shift
            ;;
        *)
            echo "view-notebook: unknown argument '$1' (use --port N, --open)" >&2
            exit 2
            ;;
    esac
done
case "$port" in
    '' | *[!0-9]*) echo "view-notebook: the port must be a whole number" >&2; exit 2 ;;
esac
out=$(mktemp -d "${TMPDIR:-/tmp}/lab-notebook.XXXXXX") || exit 2
uv run --project notebook notebook-build \
    --sessions sessions \
    --requests build-from-spec/requests \
    --choices notebook/choices \
    --layouts notebook/layouts.toml \
    --words notebook/commentary-words.txt \
    --scan-config body-lab/adapter/scan_sources.toml \
    --scan-config wind-tunnel/adapter/scan_sources.toml \
    --stop-list .kiro/blind-scan/stop-list.txt \
    --display notebook/display \
    --out "$out" || exit 1
echo "view-notebook: built into $out"
echo "view-notebook: open http://127.0.0.1:$port/  (Ctrl-C stops)"
if [ "$open_browser" = yes ]; then
    # The server below starts a moment after this line; the short wait lets it come up first.
    case "$(uname -s)" in
        Darwin) (sleep 1; open "http://127.0.0.1:$port/") & ;;
        *) echo "view-notebook: --open works on macOS only; open the address by hand" >&2 ;;
    esac
fi
exec uv run --project notebook python -m http.server "$port" --bind 127.0.0.1 --directory "$out"
