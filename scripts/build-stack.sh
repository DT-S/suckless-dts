#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
out_dir="$repo_root/build/stack"
stage_dir="$out_dir/root"
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/suckless-stack.XXXXXX")

cleanup() {
	rm -rf "$work_dir"
}
trap cleanup EXIT HUP INT TERM

for command in make cc awk sed install cp mktemp; do
	if ! command -v "$command" >/dev/null 2>&1; then
		printf 'Missing required command: %s\n' "$command" >&2
		exit 1
	fi
done

for project in dwm st dmenu slstatus; do
	if ! grep -Eq '^PREFIX[[:space:]]*=[[:space:]]*/usr/local[[:space:]]*$' \
		"$repo_root/$project/config.mk"; then
		printf '%s\n' "$project/config.mk must use PREFIX = /usr/local for the staged installer." >&2
		exit 1
	fi
	cp -a "$repo_root/$project" "$work_dir/$project"
	(
		cd "$work_dir/$project"
		make clean
		make
	)
done

rm -rf "$out_dir"
mkdir -p "$stage_dir/usr/local/bin" "$stage_dir/usr/local/share/man/man1"

version_of() {
	awk '$1 == "VERSION" && $2 == "=" { print $3; exit }' "$1/config.mk"
}

dwm_version=$(version_of "$work_dir/dwm")
st_version=$(version_of "$work_dir/st")
dmenu_version=$(version_of "$work_dir/dmenu")
slstatus_version=$(version_of "$work_dir/slstatus")

install -m 755 "$work_dir/dwm/dwm" "$stage_dir/usr/local/bin/dwm"
install -m 755 "$work_dir/st/st" "$stage_dir/usr/local/bin/st"
install -m 755 "$work_dir/dmenu/dmenu" "$stage_dir/usr/local/bin/dmenu"
install -m 755 "$work_dir/dmenu/dmenu_path" "$stage_dir/usr/local/bin/dmenu_path"
install -m 755 "$work_dir/dmenu/dmenu_run" "$stage_dir/usr/local/bin/dmenu_run"
install -m 755 "$work_dir/dmenu/stest" "$stage_dir/usr/local/bin/stest"
install -m 755 "$work_dir/slstatus/slstatus" "$stage_dir/usr/local/bin/slstatus"

sed "s/VERSION/$dwm_version/g" "$work_dir/dwm/dwm.1" \
	> "$stage_dir/usr/local/share/man/man1/dwm.1"
sed "s/VERSION/$st_version/g" "$work_dir/st/st.1" \
	> "$stage_dir/usr/local/share/man/man1/st.1"
sed "s/VERSION/$dmenu_version/g" "$work_dir/dmenu/dmenu.1" \
	> "$stage_dir/usr/local/share/man/man1/dmenu.1"
sed "s/VERSION/$dmenu_version/g" "$work_dir/dmenu/stest.1" \
	> "$stage_dir/usr/local/share/man/man1/stest.1"
sed "s/VERSION/$slstatus_version/g" "$work_dir/slstatus/slstatus.1" \
	> "$stage_dir/usr/local/share/man/man1/slstatus.1"
chmod 644 "$stage_dir/usr/local/share/man/man1/"*.1

cp "$work_dir/st/st.info" "$out_dir/st.info"

commit=unknown
if command -v git >/dev/null 2>&1 \
	&& git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	commit=$(git -C "$repo_root" rev-parse HEAD)
fi

cat > "$out_dir/BUILD_INFO" <<EOF_INFO
commit=$commit
dwm=$dwm_version
st=$st_version
dmenu=$dmenu_version
slstatus=$slstatus_version
EOF_INFO

printf '\nStack built successfully:\n'
printf '  DWM       %s\n' "$dwm_version"
printf '  ST        %s\n' "$st_version"
printf '  dmenu     %s\n' "$dmenu_version"
printf '  slstatus  %s\n' "$slstatus_version"
printf '\nStaged installation: %s\n' "$stage_dir"
