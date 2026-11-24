#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/st-selection-test.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

set --
if [ -n "${ST_TEST_SANITIZERS:-}" ]; then
	set -- "-fsanitize=$ST_TEST_SANITIZERS" -fno-omit-frame-pointer
fi

"${CC:-cc}" -std=c99 -D_XOPEN_SOURCE=600 -O1 -g \
	-ffunction-sections -fdata-sections "$@" \
	"$repo_root/scripts/test-st-selection.c" -Wl,--gc-sections \
	-o "$work_dir/test-st-selection"
"$work_dir/test-st-selection"
