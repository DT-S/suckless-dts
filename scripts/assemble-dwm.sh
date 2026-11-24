#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
source_dir="$repo_root/New Versions of DWM/dwm-6.8"
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/suckless-dwm-6.8.XXXXXX")

cleanup() {
	rm -rf "$work_dir"
}
trap cleanup EXIT HUP INT TERM

cp -a "$source_dir/." "$work_dir/"

printf '\n==> Porting alpha support to DWM 6.8\n'
python3 "$repo_root/scripts/port-dwm-6.8.py" "$work_dir"

printf '\n==> Porting active DWM behaviour to 6.8\n'
python3 "$repo_root/scripts/port-dwm-6.8-features.py" "$work_dir"

cd "$work_dir"

# The live configuration is the behavioural and visual baseline for the port.
# borderpx intentionally remains 5.
cp "$repo_root/dwm/config.h" config.h

# Reserve Alt for applications and use the Super/Windows key for DWM.
python3 - <<'PY'
from pathlib import Path

path = Path("config.h")
text = path.read_text(encoding="utf-8")
old = "#define MODKEY Mod1Mask"
new = "#define MODKEY Mod4Mask"
if text.count(old) != 1:
    raise SystemExit(f"expected exactly one {old!r} in config.h")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
PY

make clean
make

out_dir="$repo_root/build/dwm"
mkdir -p "$out_dir"
cp -f dwm "$out_dir/dwm"

printf '\nDWM 6.8 candidate built successfully: %s\n' "$out_dir/dwm"
