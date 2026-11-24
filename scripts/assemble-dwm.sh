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
cd "$work_dir"

apply_patch() {
	patch_file=$1
	printf '\n==> Applying %s\n' "$(basename "$patch_file")"
	patch --batch --forward -p1 < "$patch_file"
}

apply_patch "$repo_root/dwm/patches/dwm-alpha-20230401-348f655.diff"
apply_patch "$repo_root/dwm/patches/dwm-alwayscenter-20200625-f04cac6.diff"
apply_patch "$repo_root/dwm/patches/dwm-attachbelow-6.2.diff"
apply_patch "$repo_root/dwm/patches/dwm-cool-autostart-6.2.diff"
apply_patch "$repo_root/dwm/patches/dwm-uselessgap-20211119-58414bee958f2.diff"

# The live configuration is the behavioural baseline for the port.
# It intentionally keeps borderpx = 5 for now. MODKEY will be changed
# from Mod1Mask to Mod4Mask only after the 6.8 port builds cleanly.
cp "$repo_root/dwm/config.h" config.h

make clean
make

out_dir="$repo_root/build/dwm"
mkdir -p "$out_dir"
cp -f dwm "$out_dir/dwm"

printf '\nDWM 6.8 candidate built successfully: %s\n' "$out_dir/dwm"
