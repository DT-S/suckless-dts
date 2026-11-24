#!/usr/bin/env python3
"""Port the active local DWM features onto the pristine DWM 6.8 source.

Every replacement is intentionally strict: if upstream text does not match
exactly once, the script stops instead of silently producing a half-patched
window manager.
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


def port_alpha(root: Path) -> None:
    config_mk = root / "config.mk"
    drw_c = root / "drw.c"
    drw_h = root / "drw.h"
    dwm_c = root / "dwm.c"

    replace_once(
        config_mk,
        "LIBS = -L${X11LIB} -lX11 ${XINERAMALIBS} ${FREETYPELIBS}\n",
        "LIBS = -L${X11LIB} -lX11 ${XINERAMALIBS} ${FREETYPELIBS} -lXrender\n",
        "alpha: link Xrender",
    )

    replace_once(
        drw_h,
        "\tWindow root;\n\tDrawable drawable;\n",
        "\tWindow root;\n\tVisual *visual;\n\tunsigned int depth;\n\tColormap cmap;\n\tDrawable drawable;\n",
        "alpha: Drw visual fields",
    )
    replace_once(
        drw_h,
        "Drw *drw_create(Display *dpy, int screen, Window win, unsigned int w, unsigned int h);\n",
        "Drw *drw_create(Display *dpy, int screen, Window win, unsigned int w, unsigned int h, Visual *visual, unsigned int depth, Colormap cmap);\n",
        "alpha: drw_create declaration",
    )
    replace_once(
        drw_h,
        "void drw_clr_create(Drw *drw, Clr *dest, const char *clrname);\n"
        "void drw_clr_free(Drw *drw, Clr *c);\n"
        "Clr *drw_scm_create(Drw *drw, const char *clrnames[], size_t clrcount);\n",
        "void drw_clr_create(Drw *drw, Clr *dest, const char *clrname, unsigned int alpha);\n"
        "void drw_clr_free(Drw *drw, Clr *c);\n"
        "Clr *drw_scm_create(Drw *drw, const char *clrnames[], const unsigned int alphas[], size_t clrcount);\n",
        "alpha: colorscheme declarations",
    )

    replace_once(
        drw_c,
        "drw_create(Display *dpy, int screen, Window root, unsigned int w, unsigned int h)\n",
        "drw_create(Display *dpy, int screen, Window root, unsigned int w, unsigned int h, Visual *visual, unsigned int depth, Colormap cmap)\n",
        "alpha: drw_create signature",
    )
    replace_once(
        drw_c,
        "\tdrw->w = w;\n"
        "\tdrw->h = h;\n"
        "\tdrw->drawable = XCreatePixmap(dpy, root, w, h, DefaultDepth(dpy, screen));\n"
        "\tdrw->gc = XCreateGC(dpy, root, 0, NULL);\n",
        "\tdrw->w = w;\n"
        "\tdrw->h = h;\n"
        "\tdrw->visual = visual;\n"
        "\tdrw->depth = depth;\n"
        "\tdrw->cmap = cmap;\n"
        "\tdrw->drawable = XCreatePixmap(dpy, root, w, h, depth);\n"
        "\tdrw->gc = XCreateGC(dpy, drw->drawable, 0, NULL);\n",
        "alpha: initialize drawing visual",
    )
    replace_once(
        drw_c,
        "\tdrw->drawable = XCreatePixmap(drw->dpy, drw->root, w, h, DefaultDepth(drw->dpy, drw->screen));\n",
        "\tdrw->drawable = XCreatePixmap(drw->dpy, drw->root, w, h, drw->depth);\n",
        "alpha: resize pixmap depth",
    )
    replace_once(
        drw_c,
        "void\n"
        "drw_clr_create(Drw *drw, Clr *dest, const char *clrname)\n"
        "{\n"
        "\tif (!drw || !dest || !clrname)\n"
        "\t\treturn;\n\n"
        "\tif (!XftColorAllocName(drw->dpy, DefaultVisual(drw->dpy, drw->screen),\n"
        "\t                       DefaultColormap(drw->dpy, drw->screen),\n"
        "\t                       clrname, dest))\n"
        "\t\tdie(\"error, cannot allocate color '%s'\", clrname);\n"
        "}\n",
        "void\n"
        "drw_clr_create(Drw *drw, Clr *dest, const char *clrname, unsigned int alpha)\n"
        "{\n"
        "\tif (!drw || !dest || !clrname)\n"
        "\t\treturn;\n\n"
        "\tif (!XftColorAllocName(drw->dpy, drw->visual, drw->cmap, clrname, dest))\n"
        "\t\tdie(\"error, cannot allocate color '%s'\", clrname);\n\n"
        "\tdest->pixel = (dest->pixel & 0x00ffffffU) | (alpha << 24);\n"
        "}\n",
        "alpha: allocate ARGB colors",
    )
    replace_once(
        drw_c,
        "drw_scm_create(Drw *drw, const char *clrnames[], size_t clrcount)\n",
        "drw_scm_create(Drw *drw, const char *clrnames[], const unsigned int alphas[], size_t clrcount)\n",
        "alpha: colorscheme signature",
    )
    replace_once(
        drw_c,
        "\tfor (i = 0; i < clrcount; i++)\n"
        "\t\tdrw_clr_create(drw, &ret[i], clrnames[i]);\n",
        "\tfor (i = 0; i < clrcount; i++)\n"
        "\t\tdrw_clr_create(drw, &ret[i], clrnames[i], alphas[i]);\n",
        "alpha: colorscheme alpha values",
    )
    replace_once(
        drw_c,
        "\tXftColorFree(drw->dpy, DefaultVisual(drw->dpy, drw->screen),\n"
        "\t             DefaultColormap(drw->dpy, drw->screen), c);\n",
        "\tXftColorFree(drw->dpy, drw->visual, drw->cmap, c);\n",
        "alpha: free ARGB colors",
    )
    replace_once(
        drw_c,
        "\t\td = XftDrawCreate(drw->dpy, drw->drawable,\n"
        "\t\t                  DefaultVisual(drw->dpy, drw->screen),\n"
        "\t\t                  DefaultColormap(drw->dpy, drw->screen));\n",
        "\t\td = XftDrawCreate(drw->dpy, drw->drawable, drw->visual, drw->cmap);\n",
        "alpha: draw with ARGB visual",
    )

    replace_once(
        dwm_c,
        "#define TEXTW(X)                (drw_fontset_getwidth(drw, (X)) + lrpad)\n",
        "#define TEXTW(X)                (drw_fontset_getwidth(drw, (X)) + lrpad)\n"
        "#define OPAQUE                  0xffU\n",
        "alpha: opaque constant",
    )
    replace_once(
        dwm_c,
        "static int xerrorstart(Display *dpy, XErrorEvent *ee);\n"
        "static void zoom(const Arg *arg);\n",
        "static int xerrorstart(Display *dpy, XErrorEvent *ee);\n"
        "static void xinitvisual(void);\n"
        "static void zoom(const Arg *arg);\n",
        "alpha: xinitvisual declaration",
    )
    replace_once(
        dwm_c,
        "static Monitor *mons, *selmon;\n"
        "static Window root, wmcheckwin;\n",
        "static Monitor *mons, *selmon;\n"
        "static Window root, wmcheckwin;\n\n"
        "static int useargb = 0;\n"
        "static Visual *visual;\n"
        "static int depth;\n"
        "static Colormap cmap;\n",
        "alpha: visual globals",
    )
    replace_once(
        dwm_c,
        "\troot = RootWindow(dpy, screen);\n"
        "\tdrw = drw_create(dpy, screen, root, sw, sh);\n",
        "\troot = RootWindow(dpy, screen);\n"
        "\txinitvisual();\n"
        "\tdrw = drw_create(dpy, screen, root, sw, sh, visual, depth, cmap);\n",
        "alpha: initialize visual",
    )
    replace_once(
        dwm_c,
        "\tfor (i = 0; i < LENGTH(colors); i++)\n"
        "\t\tscheme[i] = drw_scm_create(drw, colors[i], 3);\n",
        "\tfor (i = 0; i < LENGTH(colors); i++)\n"
        "\t\tscheme[i] = drw_scm_create(drw, colors[i], alphas[i], 3);\n",
        "alpha: create translucent schemes",
    )
    replace_once(
        dwm_c,
        "\tXSetWindowAttributes wa = {\n"
        "\t\t.override_redirect = True,\n"
        "\t\t.background_pixmap = ParentRelative,\n"
        "\t\t.event_mask = ButtonPressMask|ExposureMask\n"
        "\t};\n",
        "\tXSetWindowAttributes wa = {\n"
        "\t\t.override_redirect = True,\n"
        "\t\t.background_pixel = 0,\n"
        "\t\t.border_pixel = 0,\n"
        "\t\t.colormap = cmap,\n"
        "\t\t.event_mask = ButtonPressMask|ExposureMask\n"
        "\t};\n",
        "alpha: bar attributes",
    )
    replace_once(
        dwm_c,
        "\t\tm->barwin = XCreateWindow(dpy, root, m->wx, m->by, m->ww, bh, 0, DefaultDepth(dpy, screen),\n"
        "\t\t\t\tCopyFromParent, DefaultVisual(dpy, screen),\n"
        "\t\t\t\tCWOverrideRedirect|CWBackPixmap|CWEventMask, &wa);\n",
        "\t\tm->barwin = XCreateWindow(dpy, root, m->wx, m->by, m->ww, bh, 0, depth,\n"
        "\t\t\t\tInputOutput, visual,\n"
        "\t\t\t\tCWOverrideRedirect|CWBackPixel|CWBorderPixel|CWColormap|CWEventMask, &wa);\n",
        "alpha: create ARGB bar window",
    )
    replace_once(
        dwm_c,
        "void\n"
        "zoom(const Arg *arg)\n",
        "void\n"
        "xinitvisual(void)\n"
        "{\n"
        "\tXVisualInfo *infos;\n"
        "\tXRenderPictFormat *fmt;\n"
        "\tint nitems;\n"
        "\tint i;\n\n"
        "\tXVisualInfo tpl = {\n"
        "\t\t.screen = screen,\n"
        "\t\t.depth = 32,\n"
        "\t\t.class = TrueColor\n"
        "\t};\n"
        "\tlong masks = VisualScreenMask | VisualDepthMask | VisualClassMask;\n\n"
        "\tinfos = XGetVisualInfo(dpy, masks, &tpl, &nitems);\n"
        "\tvisual = NULL;\n"
        "\tfor (i = 0; i < nitems; i++) {\n"
        "\t\tfmt = XRenderFindVisualFormat(dpy, infos[i].visual);\n"
        "\t\tif (fmt->type == PictTypeDirect && fmt->direct.alphaMask) {\n"
        "\t\t\tvisual = infos[i].visual;\n"
        "\t\t\tdepth = infos[i].depth;\n"
        "\t\t\tcmap = XCreateColormap(dpy, root, visual, AllocNone);\n"
        "\t\t\tuseargb = 1;\n"
        "\t\t\tbreak;\n"
        "\t\t}\n"
        "\t}\n\n"
        "\tXFree(infos);\n\n"
        "\tif (!visual) {\n"
        "\t\tvisual = DefaultVisual(dpy, screen);\n"
        "\t\tdepth = DefaultDepth(dpy, screen);\n"
        "\t\tcmap = DefaultColormap(dpy, screen);\n"
        "\t}\n"
        "}\n\n"
        "void\n"
        "zoom(const Arg *arg)\n",
        "alpha: xinitvisual implementation",
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} DWM_SOURCE_DIR", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    if not (root / "dwm.c").is_file():
        raise FileNotFoundError(f"not a DWM source directory: {root}")

    port_alpha(root)
    print("Applied DWM 6.8 alpha port")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
