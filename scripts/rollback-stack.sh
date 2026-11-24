#!/bin/sh
set -eu

state_home=${XDG_STATE_HOME:-"$HOME/.local/state"}
backup_base="$state_home/suckless-dts/backups"
backup_dir=${1:-"$backup_base/latest"}

if [ "$(id -u)" -eq 0 ]; then
	printf '%s\n' "Run this script as your normal user, not as root." >&2
	exit 1
fi

for command in sudo readlink find cp mkdir dirname rm; do
	if ! command -v "$command" >/dev/null 2>&1; then
		printf 'Missing required command: %s\n' "$command" >&2
		exit 1
	fi
done

if [ -L "$backup_dir" ]; then
	backup_dir=$(readlink -f "$backup_dir")
fi
manifest="$backup_dir/manifest.tsv"
if [ ! -f "$manifest" ]; then
	printf 'Backup manifest not found: %s\n' "$manifest" >&2
	exit 1
fi

sudo -v
while IFS="	" read -r action target; do
	case "$action" in
		restore)
			source_file="$backup_dir/root$target"
			if [ ! -e "$source_file" ] && [ ! -L "$source_file" ]; then
				printf 'Missing backup file: %s\n' "$source_file" >&2
				exit 1
			fi
			sudo rm -f -- "$target"
			sudo mkdir -p "$(dirname "$target")"
			sudo cp -a -- "$source_file" "$target"
			;;
		remove)
			sudo rm -f -- "$target"
			;;
		*)
			printf 'Unknown manifest action: %s\n' "$action" >&2
			exit 1
			;;
	esac
done < "$manifest"

if [ -f "$backup_dir/terminfo-created" ]; then
	find "$HOME/.terminfo" -type f -name 'st-256color' -delete 2>/dev/null || true
fi

printf 'Restored suckless binaries from: %s\n' "$backup_dir"
printf '%s\n' "Restart the DWM session to load the restored window manager binary."
