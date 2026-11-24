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

# The canonical configuration in dwm/config.h is the behavioural and visual
# baseline for the reproducible port. borderpx intentionally remains 5.
cp "$repo_root/dwm/config.h" config.h

# Reserve Alt for applications and use the Super/Windows key for DWM. The
# normalization is intentionally idempotent so the same script works before
# and after the tested 6.8 source is materialized into dwm/.
python3 - <<'PY'
from pathlib import Path

path = Path("config.h")
text = path.read_text(encoding="utf-8")
old = "#define MODKEY Mod1Mask"
new = "#define MODKEY Mod4Mask"
old_count = text.count(old)
new_count = text.count(new)
if old_count == 1 and new_count == 0:
    text = text.replace(old, new, 1)
elif old_count == 0 and new_count == 1:
    pass
else:
    raise SystemExit(
        f"expected exactly one Mod1 or Mod4 MODKEY declaration, "
        f"found Mod1={old_count}, Mod4={new_count}"
    )

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
