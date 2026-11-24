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

# Reserve Alt for applications and use the Super/Windows key for DWM. Add the
# one configuration value introduced by DWM 6.8 that is absent from the 6.4
# live configuration.
python3 - <<'PY'
from pathlib import Path

path = Path("config.h")
text = path.read_text(encoding="utf-8")
old = "#define MODKEY Mod1Mask"
new = "#define MODKEY Mod4Mask"
if text.count(old) != 1:
    raise SystemExit(f"expected exactly one {old!r} in config.h")
text = text.replace(old, new, 1)

refresh_decl = "static const int refreshrate = 120;"
if refresh_decl not in text:
    anchor = (
        "static const int lockfullscreen = 1; "
        "/* 1 will force focus on the fullscreen window */"
    )
    if text.count(anchor) != 1:
        raise SystemExit(f"expected exactly one {anchor!r} in config.h")
    text = text.replace(
        anchor,
        anchor
        + "\n"
        + refresh_decl
        + "  /* refresh rate (per second) for client move/resize */",
        1,
    )

path.write_text(text, encoding="utf-8")
PY

# Keep the generated candidate's default and active configuration identical.
cp config.h config.def.h

make clean
make

out_dir="$repo_root/build/dwm"
rm -rf "$out_dir"
mkdir -p "$out_dir/source"
cp -f dwm "$out_dir/dwm"

# Preserve reviewable, clean generated source alongside the test binary.
make clean
cp -a . "$out_dir/source/"

printf '\nDWM 6.8 candidate built successfully: %s\n' "$out_dir/dwm"
