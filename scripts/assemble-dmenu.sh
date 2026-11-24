#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
source_dir="$repo_root/New Versions of DWM/dmenu-5.4"
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/suckless-dmenu-5.4.XXXXXX")

cleanup() {
	rm -rf "$work_dir"
}
trap cleanup EXIT HUP INT TERM

cp -a "$source_dir/." "$work_dir/"

printf '\n==> Porting alpha, center and border support to dmenu 5.4\n'
python3 "$repo_root/scripts/port-dmenu-5.4.py" "$work_dir"

cd "$work_dir"

# Preserve the live menu's appearance and geometry defaults.
cp "$repo_root/dmenu/config.h" config.h

python3 - <<'PY'
from pathlib import Path

text = Path("config.h").read_text(encoding="utf-8")
required = (
    "static const unsigned int alpha = 0x55;",
    "static int centered = 1;",
    "static int min_width = 500;",
    "static unsigned int lines      = 10;",
    "static unsigned int border_width = 4;",
)
for declaration in required:
    if text.count(declaration) != 1:
        raise SystemExit(f"missing or duplicate dmenu setting: {declaration!r}")
PY

# Keep default and active configuration identical.
cp config.h config.def.h

make clean
make

out_dir="$repo_root/build/dmenu"
rm -rf "$out_dir"
mkdir -p "$out_dir/source"
cp -f dmenu stest dmenu_path dmenu_run "$out_dir/"

make clean
cp -a . "$out_dir/source/"

printf '\ndmenu 5.4 candidate built successfully: %s\n' "$out_dir/dmenu"
