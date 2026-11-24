#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
source_dir="$repo_root/New Versions of DWM/st-0.9.3"
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/suckless-st-0.9.3.XXXXXX")
patch_dir="$repo_root/st/patches"

cleanup() {
	rm -rf "$work_dir"
}
trap cleanup EXIT HUP INT TERM

cp -a "$source_dir/." "$work_dir/"

alpha_patch="$patch_dir/st-alpha-20240814-a0274bc.diff"
scrollback_patch="$patch_dir/st-scrollback-0.9.2.diff"
selection_patch="$patch_dir/st-scrollback-selection-0.9.3.diff"

printf '\n==> Verifying pinned ST patches\n'
(
	cd "$patch_dir"
	sha256sum -c SHA256SUMS
)

cd "$work_dir"

printf '\n==> Applying ST alpha support\n'
patch --batch --forward --no-backup-if-mismatch -p1 < "$alpha_patch"

printf '\n==> Applying ST scrollback support\n'
patch --batch --forward --no-backup-if-mismatch -p1 < "$scrollback_patch"

printf '\n==> Applying persistent selection and mouse edge scrolling\n'
patch --batch --forward --no-backup-if-mismatch -p1 < "$selection_patch"

if find . -type f \( -name '*.rej' -o -name '*.orig' \) | grep -q .; then
	printf '%s\n' "Patch residue found after applying ST patches:" >&2
	find . -type f \( -name '*.rej' -o -name '*.orig' \) -print >&2
	exit 1
fi

# Preserve the live terminal's fonts, palette, opacity and shortcuts while
# moving the implementation to ST 0.9.3.
cp "$repo_root/st/config.h" config.h

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

required = (
    "float alpha = 0.8;",
    "{ ShiftMask,            XK_Page_Up,     kscrollup,      {.i = -1} },",
    "{ ShiftMask,            XK_Page_Down,   kscrolldown,    {.i = -1} },",
)
for declaration in required:
    if text.count(declaration) != 1:
        raise SystemExit(f"missing or duplicate ST setting: {declaration!r}")

path.write_text(text, encoding="utf-8")
PY

# Keep default and active configuration in sync.
cp config.h config.def.h

# Both the regular build and the assembled candidate must use the same code.
for file in st.c st.h x.c st.1; do
	if ! cmp -s "$file" "$repo_root/st/$file"; then
		printf 'Assembled ST source differs from st/%s\n' "$file" >&2
		exit 1
	fi
done

make clean
make

out_dir="$repo_root/build/st"
rm -rf "$out_dir"
mkdir -p "$out_dir/source" "$out_dir/patches"
cp -f st "$out_dir/st"
cp -f "$alpha_patch" "$scrollback_patch" "$selection_patch" "$out_dir/patches/"
(
	cd "$out_dir/patches"
	sha256sum ./*.diff > SHA256SUMS
)

make clean
cp -a . "$out_dir/source/"

printf '\nST 0.9.3 candidate built successfully: %s\n' "$out_dir/st"
