# suckless-dts

Personal Arch Linux suckless desktop stack.

## Current refreshed stack

- DWM 6.8
- ST 0.9.3 with alpha transparency and scrollback
- dmenu 5.4 with alpha, centered layout and border support
- slstatus 1.1
- DWM modifier: Super / Windows key (`Mod4Mask`)

The known-working pre-refresh state is tagged as `legacy-live-2026-11-24`.

## ST: select and copy long output

- Drag with the left mouse button to select text. Hold the pointer in the first
  or last text row to scroll automatically after a short delay. Moving farther
  outside the window scrolls faster; moving back into the centre or releasing
  the button stops it.
- Use the mouse wheel to move through normal terminal history, including while
  holding a selection. The selection stays attached to its text across screens.
- Release the mouse button, then use `Ctrl+Shift+C` to copy to the clipboard.
  Middle-click continues to paste the primary selection.
- `Shift+PageUp` and `Shift+PageDown` still work. Applications that handle mouse
  events keep their own controls; hold `Shift` to select terminal text instead.
  Alternate-screen applications keep their own screen and wheel behavior.

The history retains up to 2,000 physical terminal rows. New output preserves a
scrolled-back view and its selection until the selected rows leave that buffer.
Resizing the terminal or switching screens cancels the current selection; the
terminal does not reflow old lines when its width changes.

Mouse speed and delay are configurable in `st/config.h`: `mousescrolllines`,
`selscrolldelay`, `selscrollinterval`, and `selscrollmax`. Set the interval to
zero to disable automatic edge scrolling, then rebuild.

Automated selection tests:

```sh
./scripts/test-st-selection.sh
make -C st
python3 scripts/test-st-selection-xvfb.py --st ./st/st
```

The X11 test starts its own Xvfb display and checks the actual copied text. It
needs Python 3, Xvfb, xdotool and xclip. ST assembly uses the checked-in patches
and verifies that its generated implementation matches the normal source tree.

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
