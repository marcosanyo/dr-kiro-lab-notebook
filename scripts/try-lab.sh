#!/bin/sh
# Try Dr. Kiro on body-lab yourself, in Kiro IDE.
#   sh scripts/try-lab.sh start    install the tools, start a new session, show its live notes
#   sh scripts/try-lab.sh stop     seal the open session as stopped, then reset the lab's spec to the template
# Needs `uv` and Kiro IDE. Trial files live in bench-run/try/, which git ignores; sealed records in sessions/
# are never written here. The live notes are at http://127.0.0.1:8770/ (127.0.0.1 only). Run from anywhere.
# POSIX sh; runs the same on macOS and Linux.
#
# The session is started with the variant `a` and the seed 1; the seed is kept in the record.
# Stop before the next start: start refuses while a trial session is recorded as open.
cd "$(dirname "$0")/.." || exit 2
ROOT=$(pwd -P)
TRY=bench-run/try
STATE=$TRY/state
SESSIONS=$TRY/sessions
CURRENT=$TRY/current-session
WATCH_PID=$TRY/notebook-watch.pid
WATCH_LOG=$TRY/notebook-watch.log
LAB=body-lab/lab
APP=body-lab
PORT=8770
TEMPLATES=bench/src/bench/drkiro/files
SPEC_DIR=$LAB/.kiro/specs/lab
SPECS="requirements.md design.md tasks.md"
# Dr. Kiro's experiment files and pictures of the last session. start refuses while any is left; stop removes them.
DR_KIRO_FILES="$LAB/experiments $LAB/pictures"

die() {
    echo "try-lab: $*" >&2
    exit 1
}

# The process id of every running bench-mcp whose working folder is the lab.
lab_mcp_pids() {
    for pid in $(ps -axo pid=,command= | awk '/[b]ench-mcp/ { print $1 }'); do
        if [ -d "/proc/$pid/cwd" ]; then
            cwd=$(readlink "/proc/$pid/cwd")
        else
            cwd=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1)
        fi
        [ "$cwd" = "$ROOT/$LAB" ] && echo "$pid"
    done
    return 0
}

# Remove the files (not the folders) of Dr. Kiro's experiments and pictures.
clear_dr_kiro_files() {
    for folder in $DR_KIRO_FILES; do
        for file in "$folder"/*; do
            [ -f "$file" ] && { rm -f -- "$file" || die "cannot remove $file"; }
        done
    done
}

# Send TERM to the given process ids and wait until they are gone.
end_processes() {
    for pid in "$@"; do
        kill -TERM "$pid" 2>/dev/null
    done
    for pid in "$@"; do
        waited=0
        while kill -0 "$pid" 2>/dev/null; do
            [ "$waited" -ge 10 ] && die "process $pid did not stop after 10 seconds"
            sleep 1
            waited=$((waited + 1))
        done
    done
}

start() {
    command -v uv >/dev/null 2>&1 || die "uv is not installed; see https://docs.astral.sh/uv/"
    [ -e "$CURRENT" ] && die "trial session $(cat "$CURRENT") is recorded as open; run 'sh scripts/try-lab.sh stop' first"
    [ -e "$WATCH_PID" ] && die "the live notes are still recorded as running; run 'sh scripts/try-lab.sh stop' first"
    [ -d "$LAB" ] || die "$LAB is not a folder; run this from the repository"

    for name in $SPECS; do
        cmp -s "$SPEC_DIR/$name" "$TEMPLATES/$name" ||
            die "$SPEC_DIR/$name differs from the template; the script does not overwrite it. Restore the lab's spec files or move them aside, then start again"
    done

    if curl -fsS "http://127.0.0.1:$PORT/version" >/dev/null 2>&1; then
        die "port $PORT already answers; another live-notes server is running there. Stop it, then start again"
    fi

    for folder in $DR_KIRO_FILES; do
        [ -d "$folder" ] || continue
        [ -n "$(ls -A "$folder")" ] &&
            die "$folder still has files from an earlier session; run 'sh scripts/try-lab.sh stop' first, or remove them yourself"
    done

    echo "try-lab: installing the tools (uv tool install)"
    uv tool install --editable './bench[frontend]' --with-editable ./body-lab/adapter \
        --with-editable ./wind-tunnel/adapter --with-editable ./build-from-spec --with-editable ./notebook \
        --with-executables-from build-from-spec --with-executables-from lab-notebook --reinstall ||
        die "uv tool install failed"
    command -v bench-mcp >/dev/null 2>&1 ||
        die "bench-mcp is not on PATH; add $(uv tool dir --bin) to PATH, then start again"
    bench-mcp --check >/dev/null || die "bench-mcp --check failed"

    mkdir -p "$STATE" "$SESSIONS" || die "cannot create $TRY"
    id="try-$(date +%Y%m%d-%H%M%S)"
    config="$TRY/$id.toml"

    bench-make-lab "$LAB" >/dev/null || die "bench-make-lab failed"
    bench-new-session --application "$APP" --adapter body_lab.adapter:BodyAdapter \
        --scan-sources body-lab/adapter/scan_sources.toml --stop-list .kiro/blind-scan/stop-list.txt \
        --lab "$LAB" --state "$STATE" --sessions "$SESSIONS" --session-id "$id" --seed 1 --variant a \
        --config-out "$config" || die "bench-new-session failed; nothing is open"
    printf '%s\n' "$id" > "$CURRENT"

    nohup notebook-watch --record "$STATE/$id" --state "$STATE" \
        --layouts notebook/layouts.toml --words notebook/commentary-words.txt \
        --scan-config body-lab/adapter/scan_sources.toml --app body-lab/notebook \
        --stop-list .kiro/blind-scan/stop-list.txt --port "$PORT" \
        > "$WATCH_LOG" 2>&1 < /dev/null &
    watch=$!
    echo "$watch" > "$WATCH_PID"
    ready=0
    waited=0
    while [ "$ready" -eq 0 ]; do
        kill -0 "$watch" 2>/dev/null || die "the live notes stopped at once; see $WATCH_LOG"
        if curl -fsS "http://127.0.0.1:$PORT/version" >/dev/null 2>&1; then
            ready=1
        else
            [ "$waited" -ge 30 ] && die "the live notes did not answer on port $PORT; see $WATCH_LOG"
            sleep 1
            waited=$((waited + 1))
        fi
    done

    cat <<EOF
try-lab: session $id is open. Live notes: http://127.0.0.1:$PORT/

Next, in Kiro IDE:
  1. Open the folder $ROOT/$LAB as the only folder of the workspace.
  2. Check that the "bench" MCP server shows Connected.
  3. Choose the agent Dr. Kiro, then send: Begin the session.

When Dr. Kiro says the session has ended, or to stop early, run: sh scripts/try-lab.sh stop
EOF
}

stop() {
    if [ ! -e "$CURRENT" ]; then
        echo "try-lab: no trial session is recorded as open"
        exit 0
    fi
    id=$(cat "$CURRENT")
    config="$TRY/$id.toml"
    sealed="$SESSIONS/$APP/$id"

    if [ -e "$WATCH_PID" ]; then
        watch=$(cat "$WATCH_PID")
        if kill -0 "$watch" 2>/dev/null; then
            end_processes "$watch"
        fi
        rm -f "$WATCH_PID"
    fi

    if [ -f "$sealed/log.jsonl" ]; then
        echo "try-lab: session $id was already sealed by Dr. Kiro at $sealed"
    else
        # bench-stop needs the session's lock, which the bench-mcp server holds while it runs in the lab.
        mcp=$(lab_mcp_pids)
        if [ -n "$mcp" ]; then
            echo "try-lab: stopping the bench MCP server of the lab, so that the session can be sealed"
            # shellcheck disable=SC2086
            end_processes $mcp
        fi
        bench-stop "$config" --reason "stopped with scripts/try-lab.sh stop" ||
            die "bench-stop failed; the session stays recorded as open, and the lab's spec is not reset"
        [ -f "$sealed/log.jsonl" ] || die "no sealed record at $sealed after bench-stop"
        echo "try-lab: session $id sealed as stopped at $sealed"
    fi

    for name in $SPECS; do
        cp "$TEMPLATES/$name" "$SPEC_DIR/$name" || die "cannot reset $SPEC_DIR/$name"
    done
    clear_dr_kiro_files
    rm -f "$CURRENT"
    echo "try-lab: the lab's spec is back at the template. Start again with: sh scripts/try-lab.sh start"
}

case "${1:-}" in
    start) start ;;
    stop) stop ;;
    *)
        echo "usage: sh scripts/try-lab.sh start|stop" >&2
        exit 2
        ;;
esac
