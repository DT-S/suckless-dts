#!/usr/bin/env python3
"""Port the active local DWM behaviour onto the pristine DWM 6.8 source.

The transformations are deliberately strict. If an expected upstream fragment
does not occur exactly once, the script stops instead of producing a partially
ported window manager.
"""

from __future__ import annotations

import sys
from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one match in {path}, found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def port_alwayscenter(dwm_c: Path) -> None:
    replace_once(
        dwm_c,
        "\tupdatewindowtype(c);\n"
        "\tupdatesizehints(c);\n"
        "\tupdatewmhints(c);\n"
        "\tXSelectInput(dpy, w, EnterWindowMask|FocusChangeMask|PropertyChangeMask|StructureNotifyMask);\n",
        "\tupdatewindowtype(c);\n"
        "\tupdatesizehints(c);\n"
        "\tupdatewmhints(c);\n"
        "\tc->x = c->mon->mx + (c->mon->mw - WIDTH(c)) / 2;\n"
        "\tc->y = c->mon->my + (c->mon->mh - HEIGHT(c)) / 2;\n"
        "\tXSelectInput(dpy, w, EnterWindowMask|FocusChangeMask|PropertyChangeMask|StructureNotifyMask);\n",
        "alwayscenter: center managed clients",
    )


def port_attachbelow(dwm_c: Path) -> None:
    replace_once(
        dwm_c,
        "static void attach(Client *c);\n"
        "static void attachstack(Client *c);\n",
        "static void attach(Client *c);\n"
        "static void attachbelowclient(Client *c);\n"
        "static void attachstack(Client *c);\n",
        "attachbelow: declaration",
    )
    replace_once(
        dwm_c,
        "void\n"
        "attach(Client *c)\n"
        "{\n"
        "\tc->next = c->mon->clients;\n"
        "\tc->mon->clients = c;\n"
        "}\n\n"
        "void\n"
        "attachstack(Client *c)\n",
        "void\n"
        "attach(Client *c)\n"
        "{\n"
        "\tc->next = c->mon->clients;\n"
        "\tc->mon->clients = c;\n"
        "}\n\n"
        "void\n"
        "attachbelowclient(Client *c)\n"
        "{\n"
        "\tClient *selected = c->mon->sel;\n\n"
        "\tif (!selected || selected == c || selected->isfloating) {\n"
        "\t\tattach(c);\n"
        "\t\treturn;\n"
        "\t}\n\n"
        "\tc->next = selected->next;\n"
        "\tselected->next = c;\n"
        "}\n\n"
        "void\n"
        "attachstack(Client *c)\n",
        "attachbelow: implementation",
    )
    replace_once(
        dwm_c,
        "\tif (c->isfloating)\n"
        "\t\tXRaiseWindow(dpy, c->win);\n"
        "\tattach(c);\n"
        "\tattachstack(c);\n",
        "\tif (c->isfloating)\n"
        "\t\tXRaiseWindow(dpy, c->win);\n"
        "\tif (attachbelow)\n"
        "\t\tattachbelowclient(c);\n"
        "\telse\n"
        "\t\tattach(c);\n"
        "\tattachstack(c);\n",
        "attachbelow: manage clients",
    )
    replace_once(
        dwm_c,
        "\tc->mon = m;\n"
        "\tc->tags = m->tagset[m->seltags]; /* assign tags of target monitor */\n"
        "\tattach(c);\n"
        "\tattachstack(c);\n",
        "\tc->mon = m;\n"
        "\tc->tags = m->tagset[m->seltags]; /* assign tags of target monitor */\n"
        "\tif (attachbelow)\n"
        "\t\tattachbelowclient(c);\n"
        "\telse\n"
        "\t\tattach(c);\n"
        "\tattachstack(c);\n",
        "attachbelow: move clients between monitors",
    )
    replace_once(
        dwm_c,
        "\t\t\t\t\tdetachstack(c);\n"
        "\t\t\t\t\tc->mon = mons;\n"
        "\t\t\t\t\tattach(c);\n"
        "\t\t\t\t\tattachstack(c);\n",
        "\t\t\t\t\tdetachstack(c);\n"
        "\t\t\t\t\tc->mon = mons;\n"
        "\t\t\t\t\tif (attachbelow)\n"
        "\t\t\t\t\t\tattachbelowclient(c);\n"
        "\t\t\t\t\telse\n"
        "\t\t\t\t\t\tattach(c);\n"
        "\t\t\t\t\tattachstack(c);\n",
        "attachbelow: migrate clients from removed monitors",
    )


def port_autostart(dwm_c: Path) -> None:
    replace_once(
        dwm_c,
        "/* function declarations */\n"
        "static void applyrules(Client *c);\n",
        "/* function declarations */\n"
        "static void applyrules(Client *c);\n"
        "static void autostart_exec(void);\n",
        "autostart: declaration",
    )
    replace_once(
        dwm_c,
        "static void seturgent(Client *c, int urg);\n"
        "static void showhide(Client *c);\n",
        "static void seturgent(Client *c, int urg);\n"
        "static void sigchld(int unused);\n"
        "static void showhide(Client *c);\n",
        "autostart: SIGCHLD declaration",
    )
    replace_once(
        dwm_c,
        "/* compile-time check if all tags fit into an unsigned int bit array. */\n"
        "struct NumTags { char limitexceeded[LENGTH(tags) > 31 ? -1 : 1]; };\n\n"
        "/* function implementations */\n",
        "/* compile-time check if all tags fit into an unsigned int bit array. */\n"
        "struct NumTags { char limitexceeded[LENGTH(tags) > 31 ? -1 : 1]; };\n\n"
        "/* Track long-running commands started from the config.h autostart array. */\n"
        "static pid_t *autostart_pids;\n"
        "static size_t autostart_len;\n\n"
        "void\n"
        "autostart_exec(void)\n"
        "{\n"
        "\tconst char *const *p;\n"
        "\tpid_t pid;\n"
        "\tsigset_t block, previous;\n"
        "\tstruct sigaction sa;\n"
        "\tsize_t i = 0;\n\n"
        "\tfor (p = autostart; *p; autostart_len++, p++)\n"
        "\t\twhile (*++p);\n"
        "\tif (autostart_len == 0)\n"
        "\t\treturn;\n\n"
        "\tautostart_pids = ecalloc(autostart_len, sizeof(*autostart_pids));\n"
        "\tsigemptyset(&block);\n"
        "\tsigaddset(&block, SIGCHLD);\n"
        "\tif (sigprocmask(SIG_BLOCK, &block, &previous) == -1)\n"
        "\t\tdie(\"dwm: cannot block SIGCHLD:\");\n\n"
        "\tfor (p = autostart; *p; i++, p++) {\n"
        "\t\tpid = fork();\n"
        "\t\tif (pid == 0) {\n"
        "\t\t\tsigprocmask(SIG_SETMASK, &previous, NULL);\n"
        "\t\t\tif (dpy)\n"
        "\t\t\t\tclose(ConnectionNumber(dpy));\n"
        "\t\t\tsetsid();\n"
        "\t\t\tsigemptyset(&sa.sa_mask);\n"
        "\t\t\tsa.sa_flags = 0;\n"
        "\t\t\tsa.sa_handler = SIG_DFL;\n"
        "\t\t\tsigaction(SIGCHLD, &sa, NULL);\n"
        "\t\t\texecvp(*p, (char *const *)p);\n"
        "\t\t\tfprintf(stderr, \"dwm: execvp '%s' failed: %s\\n\", *p, strerror(errno));\n"
        "\t\t\t_exit(EXIT_FAILURE);\n"
        "\t\t}\n"
        "\t\tif (pid < 0) {\n"
        "\t\t\tperror(\"dwm: fork\");\n"
        "\t\t\tautostart_pids[i] = -1;\n"
        "\t\t} else {\n"
        "\t\t\tautostart_pids[i] = pid;\n"
        "\t\t}\n"
        "\t\twhile (*++p);\n"
        "\t}\n\n"
        "\tif (sigprocmask(SIG_SETMASK, &previous, NULL) == -1)\n"
        "\t\tdie(\"dwm: cannot restore signal mask:\");\n"
        "}\n\n"
        "/* function implementations */\n",
        "autostart: process tracking",
    )
    replace_once(
        dwm_c,
        "\t/* do not transform children into zombies when they terminate */\n"
        "\tsigemptyset(&sa.sa_mask);\n"
        "\tsa.sa_flags = SA_NOCLDSTOP | SA_NOCLDWAIT | SA_RESTART;\n"
        "\tsa.sa_handler = SIG_IGN;\n"
        "\tsigaction(SIGCHLD, &sa, NULL);\n",
        "\t/* Reap children while retaining PIDs for managed autostart commands. */\n"
        "\tsigemptyset(&sa.sa_mask);\n"
        "\tsa.sa_flags = SA_NOCLDSTOP | SA_RESTART;\n"
        "\tsa.sa_handler = sigchld;\n"
        "\tif (sigaction(SIGCHLD, &sa, NULL) == -1)\n"
        "\t\tdie(\"dwm: cannot install SIGCHLD handler:\");\n",
        "autostart: install SIGCHLD handler",
    )
    replace_once(
        dwm_c,
        "void\n"
        "quit(const Arg *arg)\n"
        "{\n"
        "\trunning = 0;\n"
        "}\n",
        "void\n"
        "quit(const Arg *arg)\n"
        "{\n"
        "\tsize_t i;\n\n"
        "\tfor (i = 0; i < autostart_len; i++)\n"
        "\t\tif (autostart_pids && autostart_pids[i] > 0)\n"
        "\t\t\tkill(autostart_pids[i], SIGTERM);\n"
        "\trunning = 0;\n"
        "}\n",
        "autostart: terminate managed commands on quit",
    )
    replace_once(
        dwm_c,
        "void\n"
        "showhide(Client *c)\n",
        "void\n"
        "sigchld(int unused)\n"
        "{\n"
        "\tpid_t pid;\n"
        "\tsize_t i;\n\n"
        "\t(void)unused;\n"
        "\twhile ((pid = waitpid(-1, NULL, WNOHANG)) > 0)\n"
        "\t\tfor (i = 0; i < autostart_len; i++)\n"
        "\t\t\tif (autostart_pids && autostart_pids[i] == pid) {\n"
        "\t\t\t\tautostart_pids[i] = -1;\n"
        "\t\t\t\tbreak;\n"
        "\t\t\t}\n"
        "}\n\n"
        "void\n"
        "showhide(Client *c)\n",
        "autostart: reap child processes",
    )
    replace_once(
        dwm_c,
        "\tcheckotherwm();\n"
        "\tsetup();\n"
        "#ifdef __OpenBSD__\n",
        "\tcheckotherwm();\n"
        "\tsetup();\n"
        "\tautostart_exec();\n"
        "#ifdef __OpenBSD__\n",
        "autostart: launch configured commands",
    )


def port_uselessgaps(dwm_c: Path) -> None:
    replace_once(
        dwm_c,
        "#define WIDTH(X)                ((X)->w + 2 * (X)->bw)\n"
        "#define HEIGHT(X)               ((X)->h + 2 * (X)->bw)\n",
        "#define WIDTH(X)                ((X)->w + 2 * (X)->bw + gappx)\n"
        "#define HEIGHT(X)               ((X)->h + 2 * (X)->bw + gappx)\n",
        "uselessgaps: client dimensions",
    )
    replace_once(
        dwm_c,
        "void\n"
        "resizeclient(Client *c, int x, int y, int w, int h)\n"
        "{\n"
        "\tXWindowChanges wc;\n\n"
        "\tc->oldx = c->x; c->x = wc.x = x;\n"
        "\tc->oldy = c->y; c->y = wc.y = y;\n"
        "\tc->oldw = c->w; c->w = wc.width = w;\n"
        "\tc->oldh = c->h; c->h = wc.height = h;\n"
        "\twc.border_width = c->bw;\n"
        "\tXConfigureWindow(dpy, c->win, CWX|CWY|CWWidth|CWHeight|CWBorderWidth, &wc);\n"
        "\tconfigure(c);\n"
        "\tXSync(dpy, False);\n"
        "}\n",
        "void\n"
        "resizeclient(Client *c, int x, int y, int w, int h)\n"
        "{\n"
        "\tClient *nbc;\n"
        "\tXWindowChanges wc;\n"
        "\tint gapincr, gapoffset;\n"
        "\tunsigned int n;\n\n"
        "\tfor (n = 0, nbc = nexttiled(c->mon->clients); nbc;\n"
        "\t     nbc = nexttiled(nbc->next), n++);\n\n"
        "\tif (c->isfloating || !c->mon->lt[c->mon->sellt]->arrange) {\n"
        "\t\tgapincr = gapoffset = 0;\n"
        "\t} else if (c->mon->lt[c->mon->sellt]->arrange == monocle || n == 1) {\n"
        "\t\tgapoffset = 0;\n"
        "\t\tgapincr = -2 * (int)borderpx;\n"
        "\t\twc.border_width = 0;\n"
        "\t} else {\n"
        "\t\tgapoffset = gappx;\n"
        "\t\tgapincr = 2 * (int)gappx;\n"
        "\t}\n\n"
        "\tif (c->isfloating || !c->mon->lt[c->mon->sellt]->arrange\n"
        "\t|| (c->mon->lt[c->mon->sellt]->arrange != monocle && n != 1))\n"
        "\t\twc.border_width = c->bw;\n\n"
        "\tc->oldx = c->x; c->x = wc.x = x + gapoffset;\n"
        "\tc->oldy = c->y; c->y = wc.y = y + gapoffset;\n"
        "\tc->oldw = c->w; c->w = wc.width = w - gapincr;\n"
        "\tc->oldh = c->h; c->h = wc.height = h - gapincr;\n"
        "\tXConfigureWindow(dpy, c->win, CWX|CWY|CWWidth|CWHeight|CWBorderWidth, &wc);\n"
        "\tconfigure(c);\n"
        "\tXSync(dpy, False);\n"
        "}\n",
        "uselessgaps: resize clients",
    )
    replace_once(
        dwm_c,
        "\t\t\tresize(c, m->wx, m->wy + my, mw - (2*c->bw), h - (2*c->bw), 0);\n",
        "\t\t\tresize(c, m->wx, m->wy + my,\n"
        "\t\t\t       mw - (2*c->bw) + (n > 1 ? gappx : 0),\n"
        "\t\t\t       h - (2*c->bw), 0);\n",
        "uselessgaps: avoid doubled master-stack gap",
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} DWM_SOURCE_DIR", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    dwm_c = root / "dwm.c"
    if not dwm_c.is_file():
        raise FileNotFoundError(f"not a DWM source directory: {root}")

    port_alwayscenter(dwm_c)
    port_attachbelow(dwm_c)
    port_autostart(dwm_c)
    port_uselessgaps(dwm_c)
    print("Applied active DWM behaviour ports for 6.8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
