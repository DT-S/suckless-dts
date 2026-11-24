#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
state_home=${XDG_STATE_HOME:-"$HOME/.local/state"}
backup_base="$state_home/suckless-dts/backups"

if [ "$(id -u)" -eq 0 ]; then
	printf '%s\n' "Run this script as your normal user, not as root." >&2
	exit 1
fi

for command in sudo install stat date find sort cp mkdir dirname mv ln; do
	if ! command -v "$command" >/dev/null 2>&1; then
		printf 'Missing required command: %s\n' "$command" >&2
		exit 1
	fi
done

"$repo_root/scripts/build-stack.sh"
stage_dir="$repo_root/build/stack/root"

if [ ! -d "$stage_dir/usr/local/bin" ]; then
	printf '%s\n' "Staged installation is missing." >&2
	exit 1
fi

timestamp=$(date '+%Y%m%d-%H%M%S')
backup_dir="$backup_base/$timestamp"
manifest="$backup_dir/manifest.tsv"
mkdir -p "$backup_dir/root"

commit=unknown
if command -v git >/dev/null 2>&1 \
	&& git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	commit=$(git -C "$repo_root" rev-parse HEAD)
fi
printf 'commit=%s\ninstalled_at=%s\n' "$commit" "$timestamp" > "$backup_dir/metadata"

find "$stage_dir" -type f -print | sort | while IFS= read -r staged; do
	target=${staged#"$stage_dir"}
	if [ -e "$target" ] || [ -L "$target" ]; then
		backup_target="$backup_dir/root$target"
		mkdir -p "$(dirname "$backup_target")"
		cp -a -- "$target" "$backup_target"
		printf 'restore\t%s\n' "$target"
	else
		printf 'remove\t%s\n' "$target"
	fi
done > "$manifest"

sudo -v
rollback_needed=1
rollback_on_failure() {
	status=$?
	trap - EXIT HUP INT TERM
	if [ "$rollback_needed" -eq 1 ]; then
		printf '\nInstallation failed. Restoring the previous binaries...\n' >&2
		"$repo_root/scripts/rollback-stack.sh" "$backup_dir" || true
	fi
	exit "$status"
}
trap rollback_on_failure EXIT
trap 'exit 130' HUP INT TERM

while IFS="	" read -r action target; do
	staged="$stage_dir$target"
	mode=$(stat -c '%a' "$staged")
	tmp_target="${target}.suckless-dts-new.$$"
	sudo install -D -m "$mode" "$staged" "$tmp_target"
	sudo mv -f -- "$tmp_target" "$target"
done < "$manifest"

if command -v infocmp >/dev/null 2>&1 \
	&& ! infocmp -x st-256color >/dev/null 2>&1; then
	if ! command -v tic >/dev/null 2>&1; then
		printf '%s\n' "ST terminfo is missing and tic is unavailable." >&2
		exit 1
	fi
	tic -sx "$repo_root/build/stack/st.info"
	: > "$backup_dir/terminfo-created"
fi

ln -sfn "$timestamp" "$backup_base/latest"
rollback_needed=0
trap - EXIT HUP INT TERM

printf '\nInstalled the refreshed suckless stack.\n'
printf 'Backup: %s\n' "$backup_dir"
printf '\nThe current DWM process is still the old binary. Log out and back in,\n'
printf 'or quit it with its current binding (legacy setup: Alt+Shift+q).\n'
printf 'After the next login, DWM uses Super as its modifier.\n'
printf '\nRollback command:\n  %s/scripts/rollback-stack.sh %s\n' "$repo_root" "$backup_dir"
