#!/bin/sh
# List Japanese spec translations that are missing or out of date (.kiro/steering/japanese-translations.md).
# A translation is up to date when its header line "原文 SHA-256" equals the hash of the English file.
#   sh scripts/ja-check.sh
# POSIX sh; runs the same on macOS and Linux. Exits 1 if any translation is missing or stale.

cd "$(dirname "$0")/.." || exit 2

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum | cut -d ' ' -f 1
    else
        shasum -a 256 | cut -d ' ' -f 1
    fi
}

# For tasks.md, ticking a task does not make the translation stale: "- [x]" is hashed as "- [ ]".
hash_of() {
    case "$1" in
        */tasks.md) sed 's/^\([[:space:]]*- \)\[[xX]\]/\1[ ]/' "$1" | sha256 ;;
        *) sha256 < "$1" ;;
    esac
}

checked=0
problems=0
for source in .kiro/specs/*/requirements.md .kiro/specs/*/design.md .kiro/specs/*/tasks.md; do
    [ -f "$source" ] || continue
    checked=$((checked + 1))
    spec=$(basename "$(dirname "$source")")
    target="docs/ja/$spec/$(basename "$source")"
    if [ ! -f "$target" ]; then
        echo "missing: $target (translation of $source)"
        problems=$((problems + 1))
        continue
    fi
    recorded=$(sed -n 's/^> 原文 SHA-256: `\([0-9a-f]*\)`.*/\1/p' "$target" | head -n 1)
    if [ "$recorded" != "$(hash_of "$source")" ]; then
        echo "stale: $target (English $source changed since it was translated)"
        problems=$((problems + 1))
    fi
done

echo "ja-check: $checked spec file(s), $problems missing or stale"
[ "$problems" -eq 0 ]
