# suckless-dts

Personal Arch Linux suckless desktop stack.

## Current refreshed stack

- DWM 6.8
- ST 0.9.3 with alpha transparency and scrollback
- dmenu 5.4 with alpha, centered layout and border support
- slstatus 1.1
- DWM modifier: Super / Windows key (`Mod4Mask`)

The known-working pre-refresh state is tagged as `legacy-live-2026-11-24`.

## Test without touching the running desktop

Individual component tests:

```sh
./scripts/test-dwm-xephyr.sh
./scripts/test-st-xephyr.sh
./scripts/test-dmenu-xephyr.sh
./scripts/test-slstatus-xephyr.sh
```

Full integrated test:

```sh
./scripts/test-stack-xephyr.sh
```

The full test builds all four checked-in source trees, starts them inside Xephyr, verifies the status bar, opens ST through `Super+Shift+Return`, and opens dmenu through `Super+p`.

## Install safely

```sh
./scripts/install-stack.sh
```

The installer builds into a staging directory first, backs up every replaced file under:

```text
~/.local/state/suckless-dts/backups/
```

It does not replace the currently running DWM process. Restart the session after installation.

## Roll back

Restore the newest backup:

```sh
./scripts/rollback-stack.sh
```

Restore a specific backup:

```sh
./scripts/rollback-stack.sh ~/.local/state/suckless-dts/backups/YYYYMMDD-HHMMSS
```
