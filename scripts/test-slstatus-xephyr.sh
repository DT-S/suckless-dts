#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
geometry=${SLSTATUS_TEST_GEOMETRY:-1920x1080}

if ! command -v Xephyr >/dev/null 2>&1; then
	printf '%s\n' "Xephyr is missing. Install it with: sudo pacman -S xorg-server-xephyr" >&2
	exit 1
fi

"$repo_root/scripts/assemble-dwm.sh"
"$repo_root/scripts/assemble-slstatus.sh"

if [ -n "${SLSTATUS_TEST_DISPLAY:-}" ]; then
	display=$SLSTATUS_TEST_DISPLAY
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

log_file=${TMPDIR:-/tmp}/slstatus-xephyr-${display#:}.log
shim_dir=$(mktemp -d "${TMPDIR:-/tmp}/slstatus-test-bin.XXXXXX")

# The nested DWM inherits the real desktop's D-Bus session and HOME. Starting
# another dunst, picom and feh there only creates duplicate-service warnings,
# compositor noise and wallpaper-path errors. Replace those unrelated helpers
# with harmless stubs while keeping the real slstatus 1.1 candidate in PATH.
for helper in feh picom dunst; do
	cat > "$shim_dir/$helper" <<'EOF'
#!/bin/sh
exit 0
EOF
	chmod 755 "$shim_dir/$helper"
done
ln -s "$repo_root/build/slstatus/slstatus" "$shim_dir/slstatus"

Xephyr "$display" -ac -br -noreset -resizeable -screen "$geometry" \
	> "$log_file" 2>&1 &
xephyr_pid=$!
dwm_pid=

cleanup() {
	if [ -n "${dwm_pid:-}" ]; then
		kill "$dwm_pid" 2>/dev/null || true
	fi
	kill "$xephyr_pid" 2>/dev/null || true
	rm -rf "$shim_dir"
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

# DWM's existing autostart launches `slstatus`. The shim directory makes that
# exact autostart exercise slstatus 1.1, not the installed legacy binary.
PATH="$shim_dir:$PATH" DISPLAY="$display" \
	"$repo_root/build/dwm/dwm" &
dwm_pid=$!

status_ready=0
status_text=
for _ in $(seq 1 60); do
	if ! kill -0 "$dwm_pid" 2>/dev/null; then
		printf '%s\n' "Nested DWM exited before slstatus could be inspected." >&2
		exit 1
	fi
	if command -v xprop >/dev/null 2>&1; then
		status_text=$(DISPLAY="$display" xprop -root WM_NAME 2>/dev/null || true)
		has_percent=0
		has_speed=0
		case "$status_text" in
			*%*) has_percent=1 ;;
		esac
		case "$status_text" in
			*kb/s*) has_speed=1 ;;
		esac
		if [ "$has_percent" -eq 1 ] && [ "$has_speed" -eq 1 ]; then
			status_ready=1
			break
		fi
	fi
	sleep 0.1
done

if [ "$status_ready" -ne 1 ]; then
	printf '%s\n' "slstatus did not publish the expected status text." >&2
	printf '%s\n' "$status_text" >&2
	exit 1
fi

cat <<EOF
slstatus 1.1 test session running on $display at $geometry.

Check the DWM bar for:
  - RAM percentage
  - CPU percentage
  - download and upload speed for enp8s0
  - date and time
  - the existing Nerd Font icons and spacing
  - updates roughly twice per second

Published root status:
$status_text

Super+Shift+q closes the nested DWM test.
Your real desktop is untouched.
EOF

wait "$dwm_pid"
dwm_pid=
