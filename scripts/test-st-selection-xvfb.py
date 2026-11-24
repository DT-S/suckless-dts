#!/usr/bin/env python3
"""Exercise real ST mouse selections and PRIMARY/CLIPBOARD under an isolated Xvfb.

Requires a built ST, Python 3, Xvfb, xdotool, xclip and an installed monospace font.
Use --tcp only on hosts which cannot create Unix-domain X sockets. No running
desktop, user X server or installed terminal is modified.
"""

import argparse
import ctypes
import os
from pathlib import Path
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time


COLS, ROWS, BORDER = 80, 12, 2


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def numbered(count, prefix="row"):
    return "\r\n".join(f"{prefix}-{i:04d}: sample output" for i in range(1, count + 1))


def check_rows(text, minimum=1, first=None, last=None):
    lines = text.rstrip("\n").split("\n")
    numbers = []
    for line in lines:
        match = re.fullmatch(r"row-(\d{4}): sample output", line)
        assert match, f"Partial, duplicate or corrupt copied line: {line!r}"
        numbers.append(int(match.group(1)))
    assert len(numbers) >= minimum, f"Only {len(numbers)} rows copied: {numbers}"
    assert numbers == list(range(numbers[0], numbers[-1] + 1)), numbers
    if first is not None:
        assert numbers[0] == first, (numbers, first)
    if last is not None:
        assert numbers[-1] == last, (numbers, last)
    return numbers


class XImage(ctypes.Structure):
    # Only the public prefix through bits_per_pixel is needed to read pixels.
    _fields_ = [
        ("width", ctypes.c_int), ("height", ctypes.c_int),
        ("xoffset", ctypes.c_int), ("format", ctypes.c_int),
        ("data", ctypes.c_void_p), ("byte_order", ctypes.c_int),
        ("bitmap_unit", ctypes.c_int), ("bitmap_bit_order", ctypes.c_int),
        ("bitmap_pad", ctypes.c_int), ("depth", ctypes.c_int),
        ("bytes_per_line", ctypes.c_int), ("bits_per_pixel", ctypes.c_int),
    ]


class Server:
    def __init__(self, directory, tcp):
        self.directory = directory
        self.log = open(directory / "xvfb.log", "wb")
        self.process = None
        self.display = None
        readfd, writefd = os.pipe()
        transport = ["-nolisten", "unix", "-nolisten", "local", "-listen", "tcp"] if tcp else ["-nolisten", "tcp"]
        try:
            self.process = subprocess.Popen(
                ["Xvfb", "-displayfd", str(writefd), "-ac", *transport,
                 "-screen", "0", "1280x720x24"],
                pass_fds=(writefd,), stdout=self.log, stderr=self.log,
            )
            os.close(writefd)
            writefd = -1
            if not select.select([readfd], [], [], 8)[0]:
                raise RuntimeError("Xvfb did not report an available display")
            number = os.read(readfd, 64).decode().strip()
            if not number.isdigit():
                raise RuntimeError("Xvfb failed to start: " + (directory / "xvfb.log").read_text())
            self.env = dict(os.environ, DISPLAY=("127.0.0.1:" if tcp else ":") + number)
            self.x11 = ctypes.CDLL("libX11.so.6")
            self.x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
            self.x11.XOpenDisplay.restype = ctypes.c_void_p
            self.x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
            self.x11.XGetImage.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
                ctypes.c_ulong, ctypes.c_int]
            self.x11.XGetImage.restype = ctypes.POINTER(XImage)
            self.x11.XDestroyImage.argtypes = [ctypes.POINTER(XImage)]
            self.display = self.x11.XOpenDisplay(self.env["DISPLAY"].encode())
            if not self.display:
                raise RuntimeError("Cannot open isolated X display " + self.env["DISPLAY"])
        except BaseException:
            self.close()
            raise
        finally:
            os.close(readfd)
            if writefd >= 0:
                os.close(writefd)

    def close(self):
        if self.display:
            self.x11.XCloseDisplay(self.display)
            self.display = None
        stop(self.process)
        self.log.close()

    def command(self, *args, check=True):
        return subprocess.run(args, env=self.env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=5, check=check)

    def pixels(self, window, x, y, width, height):
        image = self.x11.XGetImage(self.display, window, x, y, width, height,
                                  ctypes.c_ulong(-1).value, 2)
        if not image:
            raise RuntimeError("Cannot inspect isolated terminal pixels")
        try:
            return ctypes.string_at(image.contents.data,
                                    image.contents.bytes_per_line * image.contents.height)
        finally:
            self.x11.XDestroyImage(image)


class Terminal:
    def __init__(self, server, binary, payload):
        self.server = server
        self.directory = Path(tempfile.mkdtemp(prefix="terminal-", dir=server.directory))
        fixture = self.directory / "output.txt"
        fixture.write_text(payload, encoding="utf-8")
        producer = self.directory / "producer.py"
        producer.write_text(
            "import os, pathlib, signal, tty\n"
            "tty.setraw(0)\n"
            "root = pathlib.Path(__file__).parent\n"
            "data = (root / 'output.txt').read_bytes()\n"
            "while data:\n"
            "    data = data[os.write(1, data):]\n"
            "(root / 'ready').touch()\n"
            "signal.pause()\n"
        )
        self.log = open(self.directory / "st.log", "wb")
        self.process = subprocess.Popen(
            [str(binary), "-f", "monospace:pixelsize=16", "-g", "80x12+100+100",
             "-T", "st-selection-test", "-e", sys.executable, str(producer)],
            env=server.env, stdout=self.log, stderr=self.log,
        )
        self.last_press = 0.0
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                result = self.xdo("search", "--pid", str(self.process.pid), check=False)
                if result.returncode == 0 and (self.directory / "ready").exists():
                    self.window = int(result.stdout.splitlines()[0])
                    break
                if self.process.poll() is not None:
                    raise RuntimeError((self.directory / "st.log").read_text())
                time.sleep(0.03)
            else:
                raise RuntimeError("ST did not create its test window")
            self.xdo("windowfocus", "--sync", str(self.window))
            geometry = self.xdo("getwindowgeometry", "--shell", str(self.window)).stdout.decode()
            values = dict(re.findall(r"^(\w+)=(\d+)$", geometry, re.MULTILINE))
            self.cw = (int(values["WIDTH"]) - 2 * BORDER) // COLS
            self.ch = (int(values["HEIGHT"]) - 2 * BORDER) // ROWS
            assert self.cw > 0 and self.ch > 0
            time.sleep(0.12)
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        # A failed assertion must not leave a grabbed button/modifier behind.
        self.xdo("mouseup", "1", "keyup", "Shift_L", "Control_L", check=False)
        stop(self.process)
        self.log.close()

    def xdo(self, *args, check=True):
        return self.server.command("xdotool", *args, check=check)

    def move(self, col, row):
        self.xdo("mousemove", "--sync", "--window", str(self.window),
                 str(BORDER + col * self.cw + self.cw // 2),
                 str(BORDER + row * self.ch + self.ch // 2))

    def press(self, col, row, shift=False):
        # Avoid testing accidental double/triple-click snapping.
        time.sleep(max(0, 0.65 - (time.monotonic() - self.last_press)))
        self.move(col, row)
        if shift:
            self.xdo("keydown", "Shift_L")
        self.xdo("mousedown", "1")
        self.last_press = time.monotonic()

    def release(self):
        self.xdo("mouseup", "1", "keyup", "Shift_L")
        time.sleep(0.06)

    def primary(self):
        return self.server.command("xclip", "-selection", "primary", "-out").stdout.decode("utf-8")

    def copy_row(self, row, shift=False):
        self.press(0, row, shift)
        self.move(COLS - 1, row)
        self.release()
        return self.primary()

    def wheel(self, direction, count):
        self.xdo("click", "--repeat", str(count), "--delay", "10", str(direction))
        time.sleep(0.06)

    def middle_pixels(self):
        # This row has no blinking cursor; compare pixels without saving images.
        return self.server.pixels(self.window, BORDER, BORDER + 5 * self.ch,
                                  32 * self.cw, self.ch)


def test_normal_copy(server, binary):
    heading = "Hello café – Grüße"
    wrapped = "wrapped:" + "0123456789" * 16
    with Terminal(server, binary, heading + "\r\n" + wrapped) as term:
        term.press(0, 0)
        term.move(COLS - 1, 3)
        term.release()
        expected = heading + "\n" + wrapped + "\n"
        assert term.primary() == expected, repr(term.primary())
        term.xdo("key", "--clearmodifiers", "ctrl+shift+c")
        clipboard = server.command("xclip", "-selection", "clipboard", "-out").stdout.decode("utf-8")
        assert clipboard == expected, repr(clipboard)


def test_wheel_drag(server, binary):
    with Terminal(server, binary, numbered(160)) as term:
        term.press(COLS - 1, 9)
        term.move(0, 2)
        term.wheel(4, 10)
        term.release()
        check_rows(term.primary(), minimum=ROWS + 1, last=158)


def test_edge_up_and_release(server, binary):
    with Terminal(server, binary, numbered(160)) as term:
        term.press(COLS - 1, 10)
        term.move(0, 0)
        # No further pointer motion: the timer must continue scrolling by itself.
        time.sleep(1.3)
        term.release()
        numbers = check_rows(term.primary(), minimum=ROWS + 1, last=159)
        time.sleep(0.4)
        # A release at the edge must stop the timer, even without pointer motion.
        check_rows(term.copy_row(5), first=numbers[0] + 5, last=numbers[0] + 5)


def test_edge_down(server, binary):
    with Terminal(server, binary, numbered(160)) as term:
        term.move(30, 5)
        term.wheel(4, 25)
        start = check_rows(term.copy_row(1))[0]
        term.press(0, 1)
        term.move(COLS - 1, ROWS - 1)
        time.sleep(1.3)
        term.release()
        check_rows(term.primary(), minimum=ROWS + 1, first=start)


def test_return_to_center(server, binary):
    with Terminal(server, binary, numbered(160)) as term:
        term.press(COLS - 1, 10)
        term.move(0, 0)
        time.sleep(0.8)
        term.move(0, 3)
        time.sleep(0.15)
        before = term.middle_pixels()
        time.sleep(0.45)
        assert term.middle_pixels() == before, "Scrolling continued after returning to the center"
        term.release()
        check_rows(term.primary(), minimum=ROWS + 1, last=159)


def test_history_boundary(server, binary):
    with Terminal(server, binary, numbered(3)) as term:
        term.move(30, 5)
        term.wheel(4, 30)
        check_rows(term.copy_row(0), first=1, last=1)
        check_rows(term.copy_row(2), first=3, last=3)


def test_alternate_screen(server, binary):
    payload = numbered(160) + "\033[?1049h" + numbered(20, "alt")
    with Terminal(server, binary, payload) as term:
        term.move(30, 5)
        term.wheel(4, 20)
        assert term.copy_row(1) == "alt-0010: sample output\n", repr(term.primary())
        term.press(COLS - 1, 10)
        term.move(0, 0)
        time.sleep(0.8)
        term.release()
        expected = "".join(f"alt-{i:04d}: sample output\n" for i in range(9, 20))
        assert term.primary() == expected, repr(term.primary())


def test_mouse_reporting_override(server, binary):
    with Terminal(server, binary, "\033[?1000h\033[?1006h" + numbered(160)) as term:
        term.move(30, 5)
        term.wheel(4, 10)
        # Unmodified events belong to the application and must not scroll ST.
        check_rows(term.copy_row(1, shift=True), first=150, last=150)
        term.press(COLS - 1, 10, shift=True)
        term.move(0, 0)
        time.sleep(1.3)
        term.release()
        check_rows(term.primary(), minimum=ROWS + 1, last=159)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", "--st", type=Path, default=Path(__file__).resolve().parents[1] / "st" / "st")
    parser.add_argument("--tcp", action="store_true", help="use TCP loopback when Unix X sockets are unavailable")
    args = parser.parse_args()
    for tool in ("Xvfb", "xdotool", "xclip"):
        if shutil.which(tool) is None:
            parser.error(f"missing required program: {tool}")
    binary = args.binary.resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        parser.error(f"build ST first or provide --binary: {binary}")
    tests = [test_normal_copy, test_wheel_drag, test_edge_up_and_release,
             test_edge_down, test_return_to_center, test_history_boundary,
             test_alternate_screen, test_mouse_reporting_override]
    with tempfile.TemporaryDirectory(prefix="st-selection-xvfb-") as temporary:
        server = Server(Path(temporary), args.tcp)
        try:
            for test in tests:
                test(server, binary)
                print("PASS", test.__name__.removeprefix("test_"), flush=True)
        finally:
            server.close()
    print(f"All {len(tests)} ST selection integration tests passed.")


if __name__ == "__main__":
    main()
