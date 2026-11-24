#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
geometry=${ST_TEST_GEOMETRY:-1920x1080}

if ! command -v Xephyr >/dev/null 2>&1; then
	printf '%s\n' "Xephyr is missing. Install it with: sudo pacman -S xorg-server-xephyr" >&2
	exit 1
fi

"$repo_root/scripts/assemble-dwm.sh"
"$repo_root/scripts/assemble-st.sh"

if [ -n "${ST_TEST_DISPLAY:-}" ]; then
	display=$ST_TEST_DISPLAY
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

log_file=${TMPDIR:-/tmp}/st-xephyr-${display#:}.log
Xephyr "$display" -ac -br -noreset -resizeable -screen "$geometry" \
	> "$log_file" 2>&1 &
xephyr_pid=$!
dwm_pid=
st_pid=

cleanup() {
	if [ -n "${st_pid:-}" ]; then
		kill "$st_pid" 2>/dev/null || true
	fi
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

DISPLAY="$display" "$repo_root/build/dwm/dwm" &
dwm_pid=$!

wm_ready=0
for _ in $(seq 1 50); do
	if ! kill -0 "$dwm_pid" 2>/dev/null; then
		printf '%s\n' "Nested DWM exited before ST could be tested." >&2
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

DISPLAY="$display" "$repo_root/build/st/st" -e /bin/sh -lc '
	i=1
	while [ "$i" -le 400 ]; do
		printf "ST 0.9.3 scrollback test line %03d\n" "$i"
		i=$((i + 1))
	done
	printf "\nUse Shift+PageUp/PageDown to inspect the history.\n"
	exec "${SHELL:-/bin/sh}"
' &
st_pid=$!

cat <<EOF
ST 0.9.3 test session running on $display at $geometry.

Check the automatically opened terminal for:
  - the existing font and colour palette
  - 80 percent background opacity
  - Shift+PageUp / Shift+PageDown scrollback
  - Ctrl+Shift+C / Ctrl+Shift+V
  - normal application Alt shortcuts

Super+Shift+q closes the nested DWM test.
Your real desktop is untouched.
EOF

wait "$dwm_pid"
dwm_pid=
