#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
geometry=${DWM_TEST_GEOMETRY:-1920x1080}

if ! command -v Xephyr >/dev/null 2>&1; then
	printf '%s\n' "Xephyr is missing. Install it with: sudo pacman -S xorg-server-xephyr" >&2
	exit 1
fi

"$repo_root/scripts/assemble-dwm.sh"

if [ -n "${DWM_TEST_DISPLAY:-}" ]; then
	display=$DWM_TEST_DISPLAY
else
	display=
	for number in $(seq 2 20); do
		if [ ! -e "/tmp/.X11-unix/X$number" ]; then
			display=:$number
			break
		fi
	done
	if [ -z "$display" ]; then
		printf '%s\n' "No free nested X display found between :2 and :20." >&2
		exit 1
	fi
fi

log_file=${TMPDIR:-/tmp}/dwm-xephyr-${display#:}.log
Xephyr "$display" -ac -br -noreset -resizeable -screen "$geometry" \
	> "$log_file" 2>&1 &
xephyr_pid=$!
dwm_pid=

cleanup() {
	if [ -n "${dwm_pid:-}" ]; then
		kill "$dwm_pid" 2>/dev/null || true
	fi
	kill "$xephyr_pid" 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM

ready=0
for _ in $(seq 1 50); do
	if command -v xdpyinfo >/dev/null 2>&1; then
		if DISPLAY="$display" xdpyinfo >/dev/null 2>&1; then
			ready=1
			break
		fi
	elif [ -S "/tmp/.X11-unix/X${display#:}" ]; then
		ready=1
		break
	fi
	sleep 0.1
done

if [ "$ready" -ne 1 ]; then
	cat "$log_file" >&2
	exit 1
fi

cat <<EOF
DWM 6.8 test session running on $display at $geometry.

  Super+Shift+Return  open st
  Super+p              open dmenu
  Super+Shift+q        quit the nested DWM test

Your real desktop is untouched.
EOF

DISPLAY="$display" "$repo_root/build/dwm/dwm" &
dwm_pid=$!
wait "$dwm_pid"
dwm_pid=
