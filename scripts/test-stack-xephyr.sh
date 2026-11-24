#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
geometry=${STACK_TEST_GEOMETRY:-1920x1080}

require_command() {
	command_name=$1
	package_name=$2

	if ! command -v "$command_name" >/dev/null 2>&1; then
		printf 'Missing %s. Install it with: sudo pacman -S --needed %s\n' \
			"$command_name" "$package_name" >&2
		exit 1
	fi
}

require_command Xephyr xorg-server-xephyr
require_command xdpyinfo xorg-xdpyinfo
require_command xprop xorg-xprop
require_command xdotool xdotool

"$repo_root/scripts/build-stack.sh"
bin_dir="$repo_root/build/stack/root/usr/local/bin"
helper_dir=$(mktemp -d "${TMPDIR:-/tmp}/suckless-stack-helpers.XXXXXX")

cleanup() {
	if [ -n "${dwm_pid:-}" ]; then
		kill "$dwm_pid" 2>/dev/null || true
	fi
	if [ -n "${xephyr_pid:-}" ]; then
		kill "$xephyr_pid" 2>/dev/null || true
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

if [ -n "${STACK_TEST_DISPLAY:-}" ]; then
	display=$STACK_TEST_DISPLAY
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

log_file=${TMPDIR:-/tmp}/suckless-stack-xephyr-${display#:}.log
Xephyr "$display" -ac -br -noreset -resizeable -screen "$geometry" \
	> "$log_file" 2>&1 &
xephyr_pid=$!
dwm_pid=

ready=0
for _ in $(seq 1 50); do
	if DISPLAY="$display" xdpyinfo >/dev/null 2>&1; then
		ready=1
		break
	fi
	sleep 0.1
done
if [ "$ready" -ne 1 ]; then
	cat "$log_file" >&2
	exit 1
fi

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
if [ "$wm_ready" -ne 1 ]; then
	printf '%s\n' "Nested DWM did not become ready." >&2
	exit 1
fi

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
if [ "$status_ready" -ne 1 ]; then
	printf '%s\n' "slstatus did not publish the expected status." >&2
	exit 1
fi

DISPLAY="$display" xdotool key --clearmodifiers super+shift+Return
st_ready=0
for _ in $(seq 1 50); do
	if DISPLAY="$display" xdotool search --class St >/dev/null 2>&1; then
		st_ready=1
		break
	fi
	sleep 0.1
done
if [ "$st_ready" -ne 1 ]; then
	printf '%s\n' "Super+Shift+Return did not open the staged ST." >&2
	exit 1
fi

DISPLAY="$display" xdotool key --clearmodifiers super+p
dmenu_ready=0
for _ in $(seq 1 50); do
	if DISPLAY="$display" xdotool search --class dmenu >/dev/null 2>&1; then
		dmenu_ready=1
		break
	fi
	sleep 0.1
done
if [ "$dmenu_ready" -ne 1 ]; then
	printf '%s\n' "Super+p did not open the staged dmenu." >&2
	exit 1
fi
DISPLAY="$display" xdotool key --clearmodifiers Escape

cat <<EOF_INFO
Full stack test passed on $display at $geometry.

Running together now:
  DWM 6.8
  ST 0.9.3
  dmenu 5.4
  slstatus 1.1

Automatic checks passed for the Super key, ST launch, dmenu launch and status bar.
Inspect the session normally, then press Super+Shift+q to close it.
Your real desktop is untouched.
EOF_INFO

wait "$dwm_pid"
dwm_pid=
