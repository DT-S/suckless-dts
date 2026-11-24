#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
source_dir="$repo_root/New Versions of DWM/slstatus-1.1"
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/suckless-slstatus-1.1.XXXXXX")

cleanup() {
	rm -rf "$work_dir"
}
trap cleanup EXIT HUP INT TERM

cp -a "$source_dir/." "$work_dir/"
cd "$work_dir"

# Preserve the live status layout, update interval, icons and network device
# while moving the implementation to slstatus 1.1.
cp "$repo_root/slstatus/config.h" config.h
cp config.h config.def.h

grep -Fq 'const unsigned int interval = 500;' config.h
grep -Fq 'netspeed_rx' config.h
grep -Fq 'netspeed_tx' config.h
grep -Fq '"enp8s0"' config.h
grep -Fq 'datetime' config.h

make clean
make

out_dir="$repo_root/build/slstatus"
rm -rf "$out_dir"
mkdir -p "$out_dir/source"
cp -f slstatus "$out_dir/slstatus"

# Preserve a clean, reviewable source tree beside the candidate binary.
make clean
cp -a . "$out_dir/source/"

printf '\nslstatus 1.1 candidate built successfully: %s\n' "$out_dir/slstatus"
