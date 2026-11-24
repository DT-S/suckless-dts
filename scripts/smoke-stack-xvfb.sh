#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
display=${STACK_SMOKE_DISPLAY:-:103}

for command in Xvfb xdpyinfo xprop xdotool; do
	if ! command -v "$command" >/dev/null 2>&1; then
		printf 'Missing required command: %s\n' "$command" >&2
		exit 1
	fi
done

"$repo_root/scripts/build-stack.sh"
bin_dir="$repo_root/build/stack/root/usr/local/bin"
helper_dir=$(mktemp -d "${TMPDIR:-/tmp}/suckless-stack-ci.XXXXXX")

cleanup() {
	if [ -n "${dwm_pid:-}" ]; then
		kill "$dwm_pid" 2>/dev/null || true
	fi
	if [ -n "${xvfb_pid:-}" ]; then
		kill "$xvfb_pid" 2>/dev/null || true
	fi
	rm -rf "$helper_dir"
}
trap cleanup EXIT HUP INT TERM

for helper in feh picom dunst; do
	cat > "$helper_dir/$helper" <<'EOF_HELPER'
#!/bin/sh
exit 0
EOF_HELPER
	chmod 755 "$helper_dir/$helper"
done

Xvfb "$display" -ac -nolisten tcp -screen 0 1280x720x24 \
	> "${TMPDIR:-/tmp}/suckless-stack-xvfb.log" 2>&1 &
xvfb_pid=$!
dwm_pid=

for _ in $(seq 1 50); do
	if DISPLAY="$display" xdpyinfo >/dev/null 2>&1; then
		break
	fi
	sleep 0.1
done
DISPLAY="$display" xdpyinfo >/dev/null 2>&1

PATH="$helper_dir:$bin_dir:$PATH" DISPLAY="$display" \
	"$bin_dir/dwm" > "${TMPDIR:-/tmp}/suckless-stack-dwm.log" 2>&1 &
dwm_pid=$!

wm_ready=0
for _ in $(seq 1 60); do
	if ! kill -0 "$dwm_pid" 2>/dev/null; then
		cat "${TMPDIR:-/tmp}/suckless-stack-dwm.log" >&2
		exit 1
	fi
	if DISPLAY="$display" xprop -root _NET_SUPPORTING_WM_CHECK 2>/dev/null \
		| grep -q 'WINDOW'; then
		wm_ready=1
		break
	fi
	sleep 0.1
done
[ "$wm_ready" -eq 1 ]

status_ready=0
for _ in $(seq 1 60); do
	root_status=$(DISPLAY="$display" xprop -root WM_NAME 2>/dev/null || true)
	if printf '%s\n' "$root_status" | grep -Fq '%' \
		&& printf '%s\n' "$root_status" | grep -Fq 'kb/s'; then
		status_ready=1
		break
	fi
	sleep 0.1
done
[ "$status_ready" -eq 1 ]

DISPLAY="$display" xdotool key --clearmodifiers super+shift+Return
st_ready=0
for _ in $(seq 1 50); do
	if DISPLAY="$display" xdotool search --class St >/dev/null 2>&1; then
		st_ready=1
		break
	fi
	sleep 0.1
done
[ "$st_ready" -eq 1 ]

DISPLAY="$display" xdotool key --clearmodifiers super+p
dmenu_ready=0
for _ in $(seq 1 50); do
	if DISPLAY="$display" xdotool search --class dmenu >/dev/null 2>&1; then
		dmenu_ready=1
		break
	fi
	sleep 0.1
done
[ "$dmenu_ready" -eq 1 ]
DISPLAY="$display" xdotool key --clearmodifiers Escape

DISPLAY="$display" xdotool key --clearmodifiers super+shift+q
for _ in $(seq 1 30); do
	if ! kill -0 "$dwm_pid" 2>/dev/null; then
		dwm_pid=
		break
	fi
	sleep 0.1
done
if [ -n "$dwm_pid" ]; then
	printf '%s\n' "DWM did not exit through Super+Shift+q." >&2
	exit 1
fi

printf '%s\n' "Full suckless stack smoke test passed."
