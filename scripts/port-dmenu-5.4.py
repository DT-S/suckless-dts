#!/usr/bin/env python3
"""Port the live dmenu features to a clean dmenu 5.4 source tree."""

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


def port_config_mk(path: Path) -> None:
    replace_once(
        path,
        "LIBS = -L$(X11LIB) -lX11 $(XINERAMALIBS) $(FREETYPELIBS)",
        "LIBS = -L$(X11LIB) -lX11 $(XINERAMALIBS) $(FREETYPELIBS) -lXrender",
        "alpha: link Xrender",
    )


def port_drw_h(path: Path) -> None:
    replace_once(
        path,
        "\tWindow root;\n\tDrawable drawable;",
        "\tWindow root;\n\tVisual *visual;\n\tunsigned int depth;\n\tColormap cmap;\n\tDrawable drawable;",
        "alpha: drawing context visual fields",
    )
    replace_once(
        path,
        "Drw *drw_create(Display *dpy, int screen, Window win, unsigned int w, unsigned int h);",
        "Drw *drw_create(Display *dpy, int screen, Window win, unsigned int w, unsigned int h, Visual *visual, unsigned int depth, Colormap cmap);",
        "alpha: drw_create declaration",
    )
    replace_once(
        path,
        "void drw_clr_create(Drw *drw, Clr *dest, const char *clrname);\n"
        "Clr *drw_scm_create(Drw *drw, const char *clrnames[], size_t clrcount);",
        "void drw_clr_create(Drw *drw, Clr *dest, const char *clrname, unsigned int alpha);\n"
        "Clr *drw_scm_create(Drw *drw, const char *clrnames[], size_t clrcount, const unsigned int alphas[]);",
        "alpha: color API declarations",
    )


def port_drw_c(path: Path) -> None:
    replace_once(
        path,
        "drw_create(Display *dpy, int screen, Window root, unsigned int w, unsigned int h)",
        "drw_create(Display *dpy, int screen, Window root, unsigned int w, unsigned int h, Visual *visual, unsigned int depth, Colormap cmap)",
        "alpha: drw_create definition",
    )
    replace_once(
        path,
        "\tdrw->h = h;\n"
        "\tdrw->drawable = XCreatePixmap(dpy, root, w, h, DefaultDepth(dpy, screen));\n"
        "\tdrw->gc = XCreateGC(dpy, root, 0, NULL);",
        "\tdrw->h = h;\n"
        "\tdrw->visual = visual;\n"
        "\tdrw->depth = depth;\n"
        "\tdrw->cmap = cmap;\n"
        "\tdrw->drawable = XCreatePixmap(dpy, root, w, h, depth);\n"
        "\tdrw->gc = XCreateGC(dpy, drw->drawable, 0, NULL);",
        "alpha: initialize drawing context",
    )
    replace_once(
        path,
        "\tdrw->drawable = XCreatePixmap(drw->dpy, drw->root, w, h, DefaultDepth(drw->dpy, drw->screen));",
        "\tdrw->drawable = XCreatePixmap(drw->dpy, drw->root, w, h, drw->depth);",
        "alpha: resize pixmap depth",
    )
    replace_once(
        path,
        "drw_clr_create(Drw *drw, Clr *dest, const char *clrname)\n"
        "{\n"
        "\tif (!drw || !dest || !clrname)\n"
        "\t\treturn;\n\n"
        "\tif (!XftColorAllocName(drw->dpy, DefaultVisual(drw->dpy, drw->screen),\n"
        "\t                       DefaultColormap(drw->dpy, drw->screen),\n"
        "\t                       clrname, dest))\n"
        "\t\tdie(\"error, cannot allocate color '%s'\", clrname);\n"
        "}",
        "drw_clr_create(Drw *drw, Clr *dest, const char *clrname, unsigned int alpha)\n"
        "{\n"
        "\tif (!drw || !dest || !clrname)\n"
        "\t\treturn;\n\n"
        "\tif (!XftColorAllocName(drw->dpy, drw->visual, drw->cmap,\n"
        "\t                       clrname, dest))\n"
        "\t\tdie(\"error, cannot allocate color '%s'\", clrname);\n\n"
        "\tdest->pixel = (dest->pixel & 0x00ffffffU) | (alpha << 24);\n"
        "}",
        "alpha: allocate colors for selected visual",
    )
    replace_once(
        path,
        "drw_scm_create(Drw *drw, const char *clrnames[], size_t clrcount)",
        "drw_scm_create(Drw *drw, const char *clrnames[], size_t clrcount, const unsigned int alphas[])",
        "alpha: scheme API definition",
    )
    replace_once(
        path,
        "\tfor (i = 0; i < clrcount; i++)\n"
        "\t\tdrw_clr_create(drw, &ret[i], clrnames[i]);",
        "\tfor (i = 0; i < clrcount; i++)\n"
        "\t\tdrw_clr_create(drw, &ret[i], clrnames[i], alphas[i]);",
        "alpha: create scheme with alpha values",
    )
    replace_once(
        path,
        "\t\td = XftDrawCreate(drw->dpy, drw->drawable,\n"
        "\t\t                  DefaultVisual(drw->dpy, drw->screen),\n"
        "\t\t                  DefaultColormap(drw->dpy, drw->screen));",
        "\t\td = XftDrawCreate(drw->dpy, drw->drawable, drw->visual, drw->cmap);",
        "alpha: draw text with selected visual",
    )


def port_dmenu_c(path: Path) -> None:
    replace_once(
        path,
        "#include <X11/Xatom.h>\n#include <X11/Xutil.h>",
        "#include <X11/Xatom.h>\n#include <X11/Xproto.h>\n#include <X11/Xutil.h>",
        "alpha: include Xproto",
    )
    replace_once(
        path,
        "#endif\n#include <X11/Xft/Xft.h>",
        "#endif\n#include <X11/extensions/Xrender.h>\n#include <X11/Xft/Xft.h>",
        "alpha: include Xrender",
    )
    replace_once(
        path,
        "#define TEXTW(X)              (drw_fontset_getwidth(drw, (X)) + lrpad)\n",
        "#define TEXTW(X)              (drw_fontset_getwidth(drw, (X)) + lrpad)\n"
        "#define OPAQUE                0xffu\n",
        "alpha: opaque constant",
    )
    replace_once(
        path,
        "struct item {\n\tchar *text;\n\tstruct item *left, *right;",
        "struct item {\n\tchar *text;\n\tunsigned int width;\n\tstruct item *left, *right;",
        "center: cache item width",
    )
    replace_once(
        path,
        "static Drw *drw;\nstatic Clr *scheme[SchemeLast];\n",
        "static Drw *drw;\nstatic Clr *scheme[SchemeLast];\n\n"
        "static Visual *visual;\n"
        "static int depth;\n"
        "static Colormap cmap;\n",
        "alpha: visual state",
    )
    replace_once(
        path,
        "static int (*fstrncmp)(const char *, const char *, size_t) = strncmp;\n"
        "static char *(*fstrstr)(const char *, const char *) = strstr;\n",
        "static int (*fstrncmp)(const char *, const char *, size_t) = strncmp;\n"
        "static char *(*fstrstr)(const char *, const char *) = strstr;\n"
        "static void xinitvisual(void);\n",
        "alpha: xinitvisual declaration",
    )
    replace_once(
        path,
        "\nstatic void\ncleanup(void)\n",
        "\nstatic int\nmax_textw(void)\n"
        "{\n"
        "\tunsigned int len = 0;\n\n"
        "\tfor (struct item *item = items; item && item->text; item++)\n"
        "\t\tlen = MAX(item->width, len);\n"
        "\treturn (int)len;\n"
        "}\n\n"
        "static void\ncleanup(void)\n",
        "center: maximum item width helper",
    )
    replace_once(
        path,
        "\t\tif (!(items[i].text = strdup(line)))\n"
        "\t\t\tdie(\"strdup:\");\n\n"
        "\t\titems[i].out = 0;",
        "\t\tif (!(items[i].text = strdup(line)))\n"
        "\t\t\tdie(\"strdup:\");\n"
        "\t\titems[i].width = TEXTW(line);\n\n"
        "\t\titems[i].out = 0;",
        "center: cache widths while reading input",
    )
    replace_once(
        path,
        "\tfor (j = 0; j < SchemeLast; j++)\n"
        "\t\tscheme[j] = drw_scm_create(drw, colors[j], 2);",
        "\tfor (j = 0; j < SchemeLast; j++)\n"
        "\t\tscheme[j] = drw_scm_create(drw, colors[j], 2, alphas[j]);",
        "alpha: initialize schemes",
    )
    replace_once(
        path,
        "\tmh = (lines + 1) * bh;\n#ifdef XINERAMA",
        "\tmh = (lines + 1) * bh;\n"
        "\tpromptw = (prompt && *prompt) ? TEXTW(prompt) - lrpad / 4 : 0;\n"
        "#ifdef XINERAMA",
        "center: compute prompt width before geometry",
    )
    replace_once(
        path,
        "\t\tx = info[i].x_org;\n"
        "\t\ty = info[i].y_org + (topbar ? 0 : info[i].height - mh);\n"
        "\t\tmw = info[i].width;",
        "\t\tif (centered) {\n"
        "\t\t\tmw = MIN(MAX(max_textw() + promptw, min_width), info[i].width);\n"
        "\t\t\tx = info[i].x_org + ((info[i].width - mw) / 2);\n"
        "\t\t\ty = info[i].y_org + ((info[i].height - mh) / 2);\n"
        "\t\t} else {\n"
        "\t\t\tx = info[i].x_org;\n"
        "\t\t\ty = info[i].y_org + (topbar ? 0 : info[i].height - mh);\n"
        "\t\t\tmw = info[i].width;\n"
        "\t\t}",
        "center: Xinerama geometry",
    )
    replace_once(
        path,
        "\t\tx = 0;\n"
        "\t\ty = topbar ? 0 : wa.height - mh;\n"
        "\t\tmw = wa.width;",
        "\t\tif (centered) {\n"
        "\t\t\tmw = MIN(MAX(max_textw() + promptw, min_width), wa.width);\n"
        "\t\t\tx = (wa.width - mw) / 2;\n"
        "\t\t\ty = (wa.height - mh) / 2;\n"
        "\t\t} else {\n"
        "\t\t\tx = 0;\n"
        "\t\t\ty = topbar ? 0 : wa.height - mh;\n"
        "\t\t\tmw = wa.width;\n"
        "\t\t}",
        "center: single-screen geometry",
    )
    replace_once(
        path,
        "\t/* create menu window */\n"
        "\tswa.override_redirect = True;\n"
        "\tswa.background_pixel = scheme[SchemeNorm][ColBg].pixel;\n"
        "\tswa.event_mask = ExposureMask | KeyPressMask | VisibilityChangeMask;\n"
        "\twin = XCreateWindow(dpy, root, x, y, mw, mh, 0,\n"
        "\t                    CopyFromParent, CopyFromParent, CopyFromParent,\n"
        "\t                    CWOverrideRedirect | CWBackPixel | CWEventMask, &swa);\n"
        "\tXSetClassHint(dpy, win, &ch);",
        "\t/* create menu window */\n"
        "\tswa.override_redirect = True;\n"
        "\tswa.background_pixel = 0;\n"
        "\tswa.border_pixel = 0;\n"
        "\tswa.colormap = cmap;\n"
        "\tswa.event_mask = ExposureMask | KeyPressMask | VisibilityChangeMask;\n"
        "\twin = XCreateWindow(dpy, root, x, y, mw, mh, border_width,\n"
        "\t                    depth, CopyFromParent, visual,\n"
        "\t                    CWOverrideRedirect | CWBackPixel | CWBorderPixel | CWColormap | CWEventMask, &swa);\n"
        "\tif (border_width)\n"
        "\t\tXSetWindowBorder(dpy, win, scheme[SchemeSel][ColBg].pixel);\n"
        "\tXSetClassHint(dpy, win, &ch);",
        "alpha/border: create menu window",
    )
    replace_once(
        path,
        "\tdie(\"usage: dmenu [-bfiv] [-l lines] [-p prompt] [-fn font] [-m monitor]\\n\"\n"
        "\t    \"             [-nb color] [-nf color] [-sb color] [-sf color] [-w windowid]\");",
        "\tdie(\"usage: dmenu [-bcfiv] [-l lines] [-p prompt] [-fn font] [-m monitor]\\n\"\n"
        "\t    \"             [-nb color] [-nf color] [-sb color] [-sf color] [-bw width] [-w windowid]\");",
        "center/border: usage string",
    )
    replace_once(
        path,
        "\t\t} else if (!strcmp(argv[i], \"-b\")) /* appears at the bottom of the screen */\n"
        "\t\t\ttopbar = 0;\n"
        "\t\telse if (!strcmp(argv[i], \"-f\"))   /* grabs keyboard before reading stdin */",
        "\t\t} else if (!strcmp(argv[i], \"-b\")) /* appears at the bottom of the screen */\n"
        "\t\t\ttopbar = 0;\n"
        "\t\telse if (!strcmp(argv[i], \"-c\"))   /* centers dmenu on screen */\n"
        "\t\t\tcentered = 1;\n"
        "\t\telse if (!strcmp(argv[i], \"-f\"))   /* grabs keyboard before reading stdin */",
        "center: command-line option",
    )
    replace_once(
        path,
        "\t\telse if (!strcmp(argv[i], \"-sf\"))  /* selected foreground color */\n"
        "\t\t\tcolors[SchemeSel][ColFg] = argv[++i];\n"
        "\t\telse if (!strcmp(argv[i], \"-w\"))   /* embedding window id */",
        "\t\telse if (!strcmp(argv[i], \"-sf\"))  /* selected foreground color */\n"
        "\t\t\tcolors[SchemeSel][ColFg] = argv[++i];\n"
        "\t\telse if (!strcmp(argv[i], \"-bw\"))  /* border width */\n"
        "\t\t\tborder_width = (unsigned int)atoi(argv[++i]);\n"
        "\t\telse if (!strcmp(argv[i], \"-w\"))   /* embedding window id */",
        "border: command-line option",
    )
    replace_once(
        path,
        "\tdrw = drw_create(dpy, screen, root, wa.width, wa.height);",
        "\txinitvisual();\n"
        "\tdrw = drw_create(dpy, screen, root, wa.width, wa.height, visual, depth, cmap);",
        "alpha: initialize drawing visual",
    )

    text = path.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        text += "\n"
    text += """

static void
xinitvisual(void)
{
	XVisualInfo *infos;
	XRenderPictFormat *fmt;
	XVisualInfo tpl = {
		.screen = screen,
		.depth = 32,
		.class = TrueColor
	};
	long masks = VisualScreenMask | VisualDepthMask | VisualClassMask;
	int i, nitems;

	infos = XGetVisualInfo(dpy, masks, &tpl, &nitems);
	visual = NULL;
	for (i = 0; infos && i < nitems; i++) {
		fmt = XRenderFindVisualFormat(dpy, infos[i].visual);
		if (fmt && fmt->type == PictTypeDirect && fmt->direct.alphaMask) {
			visual = infos[i].visual;
			depth = infos[i].depth;
			cmap = XCreateColormap(dpy, root, visual, AllocNone);
			break;
		}
	}
	if (infos)
		XFree(infos);

	if (!visual) {
		visual = DefaultVisual(dpy, screen);
		depth = DefaultDepth(dpy, screen);
		cmap = DefaultColormap(dpy, screen);
	}
}
"""
    path.write_text(text, encoding="utf-8")


def port_manpage(path: Path) -> None:
    replace_once(
        path,
        ".RB [ \\-bfiv ]\n",
        ".RB [ \\-bcfiv ]\n",
        "center: synopsis flags",
    )
    replace_once(
        path,
        ".RB [ \\-sf\n.IR color ]\n.RB [ \\-w",
        ".RB [ \\-sf\n.IR color ]\n.RB [ \\-bw\n.IR width ]\n.RB [ \\-w",
        "border: synopsis option",
    )
    replace_once(
        path,
        ".B \\-b\ndmenu appears at the bottom of the screen.\n.TP\n.B \\-f",
        ".B \\-b\ndmenu appears at the bottom of the screen.\n.TP\n"
        ".B \\-c\ndmenu appears centered on the screen.\n.TP\n.B \\-f",
        "center: option documentation",
    )
    replace_once(
        path,
        ".BI \\-sf \" color\"\ndefines the selected foreground color.\n.TP\n.B \\-v",
        ".BI \\-sf \" color\"\ndefines the selected foreground color.\n.TP\n"
        ".BI \\-bw \" width\"\ndefines the width of the border around the menu window.\n.TP\n.B \\-v",
        "border: option documentation",
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} SOURCE_DIR", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    required = ["config.mk", "dmenu.c", "drw.c", "drw.h", "dmenu.1"]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise SystemExit(f"missing dmenu source files: {', '.join(missing)}")

    port_config_mk(root / "config.mk")
    port_drw_h(root / "drw.h")
    port_drw_c(root / "drw.c")
    port_dmenu_c(root / "dmenu.c")
    port_manpage(root / "dmenu.1")

    print("Applied dmenu 5.4 alpha, center and border ports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
