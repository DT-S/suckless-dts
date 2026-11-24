#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
geometry=${DMENU_TEST_GEOMETRY:-1920x1080}

if ! command -v Xephyr >/dev/null 2>&1; then
	printf '%s\n' "Xephyr is missing. Install it with: sudo pacman -S xorg-server-xephyr" >&2
	exit 1
fi

"$repo_root/scripts/assemble-dwm.sh"
"$repo_root/scripts/assemble-dmenu.sh"

if [ -n "${DMENU_TEST_DISPLAY:-}" ]; then
	display=$DMENU_TEST_DISPLAY
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

log_file=${TMPDIR:-/tmp}/dmenu-xephyr-${display#:}.log
selection_file=$(mktemp "${TMPDIR:-/tmp}/dmenu-selection.XXXXXX")
Xephyr "$display" -ac -br -noreset -resizeable -screen "$geometry" \
	> "$log_file" 2>&1 &
xephyr_pid=$!
dwm_pid=
dmenu_pid=

cleanup() {
	if [ -n "${dmenu_pid:-}" ]; then
		kill "$dmenu_pid" 2>/dev/null || true
	fi
	if [ -n "${dwm_pid:-}" ]; then
		kill "$dwm_pid" 2>/dev/null || true
	fi
	kill "$xephyr_pid" 2>/dev/null || true
	rm -f "$selection_file"
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

PATH="$repo_root/build/dmenu:$PATH" DISPLAY="$display" "$repo_root/build/dwm/dwm" &
dwm_pid=$!

wm_ready=0
for _ in $(seq 1 50); do
	if ! kill -0 "$dwm_pid" 2>/dev/null; then
		printf '%s\n' "Nested DWM exited before dmenu could be tested." >&2
		exit 1
	fi
	if command -v xprop >/dev/null 2>&1 \
		&& DISPLAY="$display" xprop -root _NET_SUPPORTING_WM_CHECK 2>/dev/null \
		| grep -q 'WINDOW'; then
		wm_ready=1
		break
	fi
	sleep 0.1
done

if [ "$wm_ready" -ne 1 ]; then
	printf '%s\n' "Nested DWM did not become ready." >&2
	exit 1
fi

{
	printf '%s\n' \
		"dmenu 5.4 candidate" \
		"centered layout" \
		"ten visible rows" \
		"four pixel border" \
		"transparent background" \
		"keyboard navigation" \
		"type to filter" \
		"Return selects" \
		"Escape cancels" \
		"Super plus p tests dmenu_run" \
		"one" "two" "three" "four" "five" "six" "seven" "eight" "nine" "ten" "eleven"
} | DISPLAY="$display" "$repo_root/build/dmenu/dmenu" -p "dmenu 5.4 test" \
	> "$selection_file" &
dmenu_pid=$!

cat <<EOF
dmenu 5.4 test session running on $display at $geometry.

Check the opened menu for:
  - centered placement
  - 10 visible rows
  - 4 pixel border
  - transparent background with opaque text
  - filtering, arrows, Return and Escape

After selecting or cancelling, Super+p opens dmenu_run with the candidate.
Super+Shift+q closes the nested DWM test.
Your real desktop is untouched.
EOF

wait "$dmenu_pid" || true
dmenu_pid=
if [ -s "$selection_file" ]; then
	printf 'Selected: %s\n' "$(cat "$selection_file")"
else
	printf '%s\n' "No item selected. The nested session remains available for Super+p."
fi

wait "$dwm_pid"
dwm_pid=
