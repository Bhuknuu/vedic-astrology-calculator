# -*- coding: utf-8 -*-
"""
ui_widgets.py  v6.0
====================
Windows XP Luna — perfected.

New in v6
---------
* draw_xp_gradient()   : horizontal colour interpolation on a Canvas
* XPGradientHeader     : Luna-style deep-blue gradient title bar
* XPStatusBar          : multi-panel sunken status bar (Explorer-style)
* XPTooltip            : classic yellow tooltip balloon
* xp_style()           : pixel-perfect Luna ttk.Style
* titled_frame()       : groove LabelFrame with blue caption header
* RashiChart           : SI chart — transit overlay, retrograde colour,
                         stellium guard, legend
* Geocoder             : debounce + HTTP-429 retry
* sort_treeview_col()  : click-to-sort with arrow indicator
* ser_dt / deser_dt    : date helpers
"""

import sys, time, math
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import urllib.request, urllib.error, urllib.parse
import json
from datetime import datetime

from core.constants import (
    RASHI_ABBR, RASHI_DEVA, GRAHA_SYMBOLS, ALL_GRAHAS, SI_GRID,
    XP_BG, XP_SURFACE, XP_BORDER, XP_FIELD, XP_BLUE, XP_BLUE2,
    XP_BTN, XP_GRAY, XP_WARN, XP_WARN_FG, XP_TEXT_D, XP_TEXT_M,
)

# ─── Font resolution ──────────────────────────────────────────────────────────
_DEVA_CANDIDATES = ["Arial Unicode MS","Nirmala UI","Mangal","FreeSans","DejaVu Sans"]
_DEVA_FONT = "Arial Unicode MS"

def _resolve_devanagari_font(root):
    global _DEVA_FONT
    try:
        avail = set(tkfont.families(root))
        for f in _DEVA_CANDIDATES:
            if f in avail:
                _DEVA_FONT = f; return
        _DEVA_FONT = "TkDefaultFont"
    except Exception: pass

def ensure_utf8_stdout():
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError: pass


# ══════════════════════════════════════════════════════════════════════════════
#  SOLID HEADER BAR  (brutalist — solid black, no gradient, no canvas)
# ══════════════════════════════════════════════════════════════════════════════
class XPGradientHeader(tk.Frame):
    """Solid black header bar. Title left, subtitle right. No canvas/gradient."""
    HEIGHT = 40

    def __init__(self, parent, title="", subtitle="", **kw):
        super().__init__(parent, bg="#000000", height=self.HEIGHT, **kw)
        self.pack_propagate(False)
        self._sub_var = tk.StringVar(value=subtitle)
        tk.Label(self, text=title, bg="#000000", fg="#FFFFFF",
                 font=("Tahoma", 11, "bold"), anchor="w",
                 padx=12).pack(side="left", fill="y")
        tk.Label(self, textvariable=self._sub_var, bg="#000000", fg=XP_BLUE2,
                 font=("Tahoma", 8), anchor="e",
                 padx=12).pack(side="right", fill="y")
        # 1px blue accent line at the bottom
        tk.Frame(self, bg=XP_BLUE, height=2).pack(side="bottom", fill="x")

    def set_subtitle(self, txt):
        self._sub_var.set(txt)


# ══════════════════════════════════════════════════════════════════════════════
#  STATUS BAR  (single row, dark background, no "grip" glyph)
# ══════════════════════════════════════════════════════════════════════════════
class XPStatusBar(tk.Frame):
    """Dark status bar. panels = list of (key, width_chars, initial_text)."""

    def __init__(self, parent, panels, **kw):
        super().__init__(parent, bg=XP_BTN, height=20, **kw)
        self.pack_propagate(False)
        self._vars, self._labels = {}, {}
        sep = XP_BORDER
        for key, width, init in panels:
            v = tk.StringVar(value=f" {init}")
            lbl = tk.Label(self, textvariable=v,
                           bg=XP_SURFACE, fg=XP_TEXT_M,
                           font=("Tahoma", 8), anchor="w",
                           relief="flat", bd=0, padx=6, width=width)
            lbl.pack(side="left", fill="y", padx=(1, 0))
            self._vars[key] = v
            self._labels[key] = lbl

    def set(self, key, text):
        if key in self._vars:
            self._vars[key].set(f" {text}")



# ══════════════════════════════════════════════════════════════════════════════
#  XP TOOLTIP
# ══════════════════════════════════════════════════════════════════════════════
class XPTooltip:
    """Classic Windows XP yellow tooltip balloon."""

    def __init__(self, widget, text, delay=600):
        self.widget  = widget
        self.text    = text
        self.delay   = delay
        self._tip    = None
        self._after  = None
        widget.bind("<Enter>",  self._schedule)
        widget.bind("<Leave>",  self._cancel)
        widget.bind("<Button>", self._cancel)

    def _schedule(self, _=None):
        self._cancel()
        self._after = self.widget.after(self.delay, self._show)

    def _cancel(self, _=None):
        if self._after:
            self.widget.after_cancel(self._after)
            self._after = None
        if self._tip:
            self._tip.destroy()
            self._tip = None

    def _show(self):
        if self._tip: return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 2
        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(self._tip, text=self.text,
                       bg="#000000", fg="#FFFFFF",
                       relief="solid", bd=1,
                       font=("Tahoma", 8),
                       padx=6, pady=3)
        lbl.pack()


# ══════════════════════════════════════════════════════════════════════════════
#  TTK STYLE  (pixel-perfect XP Luna with Dynamic Font Scaling)
# ══════════════════════════════════════════════════════════════════════════════
def xp_style(root, scale=1.0):
    """Brutalist minimalist ttk.Style with dynamic scaling for accessibility."""
    s = ttk.Style(root)
    try: s.theme_use("clam")
    except: pass

    # Compute scaled font sizes
    f_base  = max(7, int(round(9 * scale)))
    f_bold  = max(7, int(round(9 * scale)))
    f_small = max(6, int(round(8 * scale)))

    btn_pad_x = max(4, int(round(8 * scale)))
    btn_pad_y = max(2, int(round(4 * scale)))
    row_h     = max(18, int(round(22 * scale)))
    tab_pad_x = max(6, int(round(10 * scale)))
    tab_pad_y = max(2, int(round(4 * scale)))

    # Configure standard Tk named fonts so plain Tkinter widgets also scale
    try:
        for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkCaptionFont", "TkMenuFont"):
            try:
                f = tkfont.nametofont(name)
                orig = 9 if "Heading" not in name else 11
                f.configure(size=int(round(orig * scale)))
            except Exception:
                pass
    except Exception:
        pass

    # ── Core frames / labels ──
    s.configure("XP.TFrame",   background=XP_BG)
    s.configure("XP.TLabel",   background=XP_BG,      font=("Tahoma", f_base),        foreground=XP_TEXT_D)
    s.configure("Head.TLabel", background=XP_BG,      font=("Tahoma", f_bold, "bold"), foreground=XP_BLUE2)
    s.configure("Small.TLabel",background=XP_BG,      font=("Tahoma", f_small),       foreground=XP_TEXT_M)
    s.configure("White.TLabel",background=XP_FIELD,   font=("Tahoma", f_base),        foreground="#000000")

    # ── Buttons: flat, sharp corners ──
    s.configure("XP.TButton",
        background=XP_BTN, font=("Tahoma", f_base), padding=(btn_pad_x, btn_pad_y),
        relief="flat", borderwidth=1, foreground=XP_TEXT_D)
    s.map("XP.TButton",
        background=[("active","#3A3A3A"),("pressed","#1A1A1A")],
        foreground=[("active",XP_TEXT_D)])

    # Primary action button (blue, bold)
    s.configure("Blue.TButton",
        background=XP_BLUE, font=("Tahoma", f_base, "bold"),
        foreground="#FFFFFF", padding=(btn_pad_x + 2, btn_pad_y + 1), relief="flat", borderwidth=0)
    s.map("Blue.TButton",
        background=[("active",XP_BLUE2),("pressed","#1D4ED8")])

    # Stop/danger button
    s.configure("Red.TButton",
        background="#991B1B", font=("Tahoma", f_base, "bold"),
        foreground="#FFFFFF", padding=(btn_pad_x, btn_pad_y), relief="flat", borderwidth=0)
    s.map("Red.TButton",
        background=[("active","#B91C1C"),("pressed","#7F1D1D")])

    # ── Entry / Combobox — white field, black text ──
    s.configure("XP.TEntry",
        fieldbackground=XP_FIELD, foreground="#000000",
        font=("Tahoma", f_base), padding=3, relief="flat", borderwidth=1)
    s.configure("XP.TCombobox",
        fieldbackground=XP_FIELD, foreground="#000000", font=("Tahoma", f_base))
    s.map("XP.TCombobox",
        fieldbackground=[("readonly",XP_BTN)],
        foreground=[("readonly",XP_TEXT_D)])

    # ── Notebook tabs: dark with blue active indicator ──
    s.configure("XP.TNotebook", background=XP_BG, tabmargins=[0,4,0,0])
    s.configure("XP.TNotebook.Tab",
        background=XP_BTN, font=("Tahoma", f_base), padding=[tab_pad_x, tab_pad_y],
        foreground=XP_TEXT_M)
    s.map("XP.TNotebook.Tab",
        background=[("selected",XP_SURFACE),("active",XP_BTN)],
        foreground=[("selected",XP_BLUE2),("active",XP_TEXT_D)],
        padding=[("selected",[tab_pad_x, tab_pad_y + 1])])

    # ── Treeview: white rows, dark heading, blue selection ──
    s.configure("XP.Treeview",
        background=XP_FIELD, font=("Tahoma", f_base),
        rowheight=row_h, fieldbackground=XP_FIELD, foreground="#000000")
    s.configure("XP.Treeview.Heading",
        background=XP_SURFACE, font=("Tahoma", f_bold, "bold"),
        relief="flat", foreground=XP_TEXT_D)
    s.map("XP.Treeview",
        background=[("selected",XP_BLUE)],
        foreground=[("selected","#FFFFFF")])

    # ── Scrollbar: slim, dark ──
    s.configure("XP.Vertical.TScrollbar",
        background=XP_SURFACE, arrowcolor=XP_TEXT_M,
        troughcolor=XP_BG, width=10, relief="flat")
    s.configure("XP.Horizontal.TScrollbar",
        background=XP_SURFACE, arrowcolor=XP_TEXT_M,
        troughcolor=XP_BG, width=10, relief="flat")

    return s


# ══════════════════════════════════════════════════════════════════════════════
#  TITLED FRAME  (dark header band + inner content area)
# ══════════════════════════════════════════════════════════════════════════════
def titled_frame(parent, title="", padx=4, pady=4, **kw):
    """Dark-surface panel with a solid accent-color title band. Returns (outer, inner)."""
    outer = tk.Frame(parent, bg=XP_BORDER, bd=1, relief="flat")
    if title:
        hdr = tk.Frame(outer, bg=XP_SURFACE, height=22)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text=f"  {title}", bg=XP_SURFACE, fg=XP_TEXT_M,
                 font=("Tahoma",8,"bold")).pack(side="left", pady=2)
    inner = tk.Frame(outer, bg=XP_BG, padx=padx, pady=pady)
    inner.pack(fill="both", expand=True)
    return outer, inner


def xp_labelframe(parent, title, padx=6, pady=4):
    """Dark-surface group box with muted caption."""
    f = tk.LabelFrame(parent, text=f" {title} ",
                      bg=XP_BG, fg=XP_TEXT_M,
                      font=("Tahoma",8,"bold"),
                      relief="flat", bd=1,
                      padx=padx, pady=pady)
    return f


# ══════════════════════════════════════════════════════════════════════════════
#  RASHI CHART CANVAS (Interchangeable North & South Indian Styles)
# ══════════════════════════════════════════════════════════════════════════════
class RashiChart(tk.Canvas):
    """
    Vedic Astrology Kundali Canvas.
    Supports interchangeable North Indian (Diamond / Rhombus) and
    South Indian (Square Box) styles with one click.

    Features:
    * North Indian Style: Fixed houses 1-12 (counter-clockwise), Lagna at top diamond,
      moving Rashis (zodiac numbers 1-12), and natal/transit planetary placements.
    * South Indian Style: Fixed signs (clockwise), Lagna marked in ascendant sign box.
    * Interactive Style Switching: Clickable toggle badge on canvas + set_style() API.
    * Transit Overlay: Blue 'T·' prefixed transit grahas.
    * Retrograde Highlight: Dark-red color (#CC2200).
    * Stellium Guard: >4 planets shows '+N more'.
    * Dynamic Resizing: Crisp vector geometry adapting to window scaling.
    """

    def __init__(self, parent, title="", size=330, chart_style="North Indian", font_scale=1.0, **kw):
        super().__init__(parent, width=size, height=size+36,
                         bg="#FFFFFF", highlightthickness=1,
                         highlightbackground=XP_BORDER, **kw)
        self.size        = size
        self.title       = title
        self.chart_style = chart_style
        self.font_scale  = font_scale
        self.grahas      = {}
        self.t_grahas    = {}   # transit planets
        self.cell        = size // 4
        self.bind("<Configure>", self._resize)
        self.draw()

    def _resize(self, e):
        self.size = min(e.width, e.height) - 36
        self.cell = max(self.size // 4, 1)
        self.draw()

    def set_font_scale(self, scale):
        self.font_scale = max(0.6, min(scale, 2.5))
        self.draw()

    def zoom_in_font(self):
        self.set_font_scale(self.font_scale + 0.15)

    def zoom_out_font(self):
        self.set_font_scale(self.font_scale - 0.15)

    def zoom_reset_font(self):
        self.set_font_scale(1.0)

    def set_style(self, style):
        if style in ("North Indian", "South Indian") and style != self.chart_style:
            self.chart_style = style
            self.draw()

    def toggle_style(self):
        new_style = "South Indian" if self.chart_style == "North Indian" else "North Indian"
        self.chart_style = new_style
        self.draw()

    def set_data(self, grahas, title=None, transit_grahas=None, chart_style=None, font_scale=None):
        self.grahas   = grahas
        self.t_grahas = transit_grahas or {}
        if title: self.title = title
        if chart_style: self.chart_style = chart_style
        if font_scale is not None: self.font_scale = font_scale
        self.draw()

    def draw(self):
        self.delete("all")
        if self.chart_style == "North Indian":
            self._draw_north_indian()
        else:
            self._draw_south_indian()

    def _draw_north_indian(self):
        w = max(self.winfo_width(), self.size + 16)
        h = max(self.winfo_height(), self.size + 36)
        y_top = 22
        bottom_pad = 26
        s = max(min(w - 20, h - y_top - bottom_pad), 120)

        x0 = (w - s) // 2
        x1 = x0 + s
        y0 = y_top + 2
        y1 = y0 + s

        mx = (x0 + x1) // 2
        my = (y0 + y1) // 2

        fs = getattr(self, "font_scale", 1.0)
        f_title = max(8, int(round(9 * fs)))
        f_rashi = max(7, int(round(7.5 * fs)))
        f_lagna = max(8, int(round(8.5 * fs)))
        f_planet = max(8, int(round(9.5 * fs)))
        f_planet_sm = max(7, int(round(8 * fs)))
        f_tran = max(6, int(round(7 * fs)))
        f_leg = max(6, int(round(7 * fs)))

        # Header Title
        self.create_text(w // 2, 11, text=f"{self.title}  ·  North Indian",
                         font=("Tahoma", f_title, "bold"), fill="#262626")

        # ── Ascendant Rashi ──
        asc_rashi = None
        if self.grahas:
            al = self.grahas.get("Lagna", {}).get("longitude")
            if al is not None:
                asc_rashi = int(al / 30) % 12
            elif "rashi" in self.grahas.get("Lagna", {}):
                asc_rashi = int(self.grahas["Lagna"]["rashi"]) % 12
        if asc_rashi is None:
            asc_rashi = 0

        # Key points of North Indian Geometry
        T = (mx, y0)
        R = (x1, my)
        B = (mx, y1)
        L = (x0, my)

        TL_c = (x0, y0)
        TR_c = (x1, y0)
        BR_c = (x1, y1)
        BL_c = (x0, y1)

        TL_m = ((x0 + mx) // 2, (y0 + my) // 2)
        TR_m = ((x1 + mx) // 2, (y0 + my) // 2)
        BR_m = ((x1 + mx) // 2, (y1 + my) // 2)
        BL_m = ((x0 + mx) // 2, (y1 + my) // 2)

        M = (mx, my)

        # 12 Houses: Polygons, Centroids, and Rashi label positions
        houses_poly = {
            1:  [T, TR_m, M, TL_m],
            2:  [TL_c, T, TL_m],
            3:  [TL_c, TL_m, L],
            4:  [L, TL_m, M, BL_m],
            5:  [L, BL_m, BL_c],
            6:  [BL_c, BL_m, B],
            7:  [B, BL_m, M, BR_m],
            8:  [B, BR_m, BR_c],
            9:  [BR_c, R, BR_m],
            10: [R, TR_m, M, BR_m],
            11: [R, TR_c, TR_m],
            12: [TR_c, T, TR_m],
        }

        # Sign label positions (numbers 1-12)
        rashi_lbl_pos = {
            1:  (mx, my - 13),
            2:  ((TL_c[0] + T[0]) // 2, y0 + 10),
            3:  (x0 + 11, (TL_c[1] + L[1]) // 2),
            4:  (mx - 14, my),
            5:  (x0 + 11, (L[1] + BL_c[1]) // 2),
            6:  ((BL_c[0] + B[0]) // 2, y1 - 10),
            7:  (mx, my + 13),
            8:  ((B[0] + BR_c[0]) // 2, y1 - 10),
            9:  (x1 - 11, (R[1] + BR_c[1]) // 2),
            10: (mx + 14, my),
            11: (x1 - 11, (TR_c[1] + R[1]) // 2),
            12: ((T[0] + TR_c[0]) // 2, y0 + 10),
        }

        # ── Map natal planets into houses (1-12) ──
        house_natal = {h: [] for h in range(1, 13)}
        for gn in ALL_GRAHAS + ["Lagna"]:
            pd = self.grahas.get(gn, {})
            if not pd:
                continue
            bhava = pd.get("bhava")
            if bhava is not None and str(bhava).isdigit() and 1 <= int(bhava) <= 12:
                h = int(bhava)
            else:
                lon = pd.get("longitude")
                if lon is None:
                    continue
                sign = int(lon / 30) % 12
                h = (sign - asc_rashi) % 12 + 1
            sym = GRAHA_SYMBOLS.get(gn, gn[:2])
            is_retro = bool(pd.get("retro"))
            house_natal[h].append((sym, is_retro))

        # ── Map transit planets into houses (1-12) ──
        house_transit = {h: [] for h in range(1, 13)}
        for gn in ALL_GRAHAS:
            pd = self.t_grahas.get(gn, {})
            if not pd:
                continue
            lon = pd.get("longitude")
            if lon is None:
                continue
            t_sign = int(lon / 30) % 12
            h = (t_sign - asc_rashi) % 12 + 1
            sym = GRAHA_SYMBOLS.get(gn, gn[:2])
            house_transit[h].append(sym)

        # ── Draw 12 House Compartments ──
        for h, pts in houses_poly.items():
            flat = [coord for pt in pts for coord in pt]
            bg = "#FFFCE8" if h == 1 else "#FFFFFF"
            self.create_polygon(flat, fill=bg, outline="#DDDDDD", width=1)

        # ── Draw Structural Diamond & Diagonal Lines ──
        # Outer boundary
        self.create_rectangle(x0, y0, x1, y1, outline="#262626", width=2)
        # Inner diamond
        self.create_line(T[0], T[1], R[0], R[1], B[0], B[1], L[0], L[1], T[0], T[1],
                         fill="#262626", width=1.5)
        # Diagonals
        self.create_line(TL_c[0], TL_c[1], BR_c[0], BR_c[1], fill="#262626", width=1.5)
        self.create_line(TR_c[0], TR_c[1], BL_c[0], BL_c[1], fill="#262626", width=1.5)

        # ── Place Labels and Planets ──
        for h in range(1, 13):
            pts = houses_poly[h]
            cx = sum(p[0] for p in pts) // len(pts)
            cy = sum(p[1] for p in pts) // len(pts)

            r_idx = (asc_rashi + h - 1) % 12
            sign_num = r_idx + 1

            # Rashi number (1-12)
            lx, ly = rashi_lbl_pos[h]
            self.create_text(lx, ly, text=str(sign_num), font=("Tahoma", f_rashi, "bold"), fill="#71717A")

            # In House 1, mark Ascendant
            if h == 1:
                self.create_text(T[0], T[1] + 11, text="लग्न", font=(_DEVA_FONT, f_lagna, "bold"), fill="#B45309")

            # Natal Planets
            nat = house_natal[h]
            n_planets = len(nat)
            if n_planets == 1:
                sym, retro = nat[0]
                col = "#CC2200" if retro else "#111111"
                self.create_text(cx, cy, text=sym, font=(_DEVA_FONT, f_planet, "bold"), fill=col)
            elif n_planets == 2:
                col0 = "#CC2200" if nat[0][1] else "#111111"
                col1 = "#CC2200" if nat[1][1] else "#111111"
                dx = int(round(14 * min(fs, 1.4)))
                self.create_text(cx - dx, cy, text=nat[0][0], font=(_DEVA_FONT, f_planet_sm, "bold"), fill=col0)
                self.create_text(cx + dx, cy, text=nat[1][0], font=(_DEVA_FONT, f_planet_sm, "bold"), fill=col1)
            elif n_planets == 3:
                col0 = "#CC2200" if nat[0][1] else "#111111"
                col1 = "#CC2200" if nat[1][1] else "#111111"
                col2 = "#CC2200" if nat[2][1] else "#111111"
                dx = int(round(14 * min(fs, 1.4)))
                dy = int(round(8 * min(fs, 1.4)))
                self.create_text(cx, cy - dy, text=nat[0][0], font=(_DEVA_FONT, f_planet_sm, "bold"), fill=col0)
                self.create_text(cx - dx, cy + dy, text=nat[1][0], font=(_DEVA_FONT, f_planet_sm, "bold"), fill=col1)
                self.create_text(cx + dx, cy + dy, text=nat[2][0], font=(_DEVA_FONT, f_planet_sm, "bold"), fill=col2)
            elif n_planets >= 4:
                vis = nat[:4]
                dx = int(round(13 * min(fs, 1.4)))
                dy = int(round(7 * min(fs, 1.4)))
                dxs = [-dx, dx, -dx, dx]
                dys = [-dy, -dy, dy, dy]
                for (sym, retro), p_dx, p_dy in zip(vis, dxs, dys):
                    col = "#CC2200" if retro else "#111111"
                    self.create_text(cx + p_dx, cy + p_dy, text=sym, font=(_DEVA_FONT, f_planet_sm, "bold"), fill=col)
                if n_planets > 4:
                    self.create_text(cx, cy + int(round(16 * min(fs, 1.3))), text=f"+{n_planets-4}", font=("Tahoma", f_rashi, "bold"), fill="#CC2200")

            # Transit Planets (small blue text)
            tran = house_transit[h]
            if tran:
                txt = "·".join(tran[:3])
                offset_y = int(round((15 if n_planets <= 2 else 19) * min(fs, 1.3)))
                self.create_text(cx, cy + offset_y, text=f"T·{txt}", font=(_DEVA_FONT, f_tran, "bold"), fill=XP_BLUE2)

        # ── Legend row & Interactive Toggle Badge ──
        leg_y = y1 + 14
        if self.t_grahas:
            self.create_text(x0 + 4, leg_y, text="● Natal  ●· Transit (blue)  ● Retro (red)",
                             font=("Tahoma", f_leg), fill="#52525B", anchor="w")
        else:
            self.create_text(x0 + 4, leg_y, text="● Natal (black)   ● Retrograde (red)",
                             font=("Tahoma", f_leg), fill="#52525B", anchor="w")

        # Interactive Switch Button Badge (Bottom Right)
        bw = int(round(88 * min(fs, 1.3)))
        bx1 = x1
        bx0 = bx1 - bw
        self.create_rectangle(bx0, leg_y - 8, bx1, leg_y + 8, fill="#F4F4F5", outline="#D4D4D8", width=1, tags="style_toggle")
        self.create_text((bx0 + bx1) // 2, leg_y, text="⇄ South Indian", font=("Tahoma", f_leg, "bold"), fill="#2563EB", tags="style_toggle")
        self.tag_bind("style_toggle", "<Button-1>", lambda e: self.toggle_style())
        self.tag_bind("style_toggle", "<Enter>", lambda e: self.config(cursor="hand2"))
        self.tag_bind("style_toggle", "<Leave>", lambda e: self.config(cursor=""))

    def _draw_south_indian(self):
        w = max(self.winfo_width(), self.size + 16)
        h = max(self.winfo_height(), self.size + 36)
        y_top = 22
        bottom_pad = 26
        s = max(min(w - 20, h - y_top - bottom_pad), 120)
        c = s // 4
        x0 = (w - s) // 2
        y0 = y_top + 2
        x1 = x0 + s
        y1 = y0 + s

        fs = getattr(self, "font_scale", 1.0)
        f_title = max(8, int(round(9 * fs)))
        f_abbr = max(6, int(round(7.5 * fs)))
        f_planet = max(7, int(round(8.5 * fs)))
        f_tran = max(6, int(round(7 * fs)))
        f_center_lg = max(7, int(round(8.5 * fs)))
        f_center_nm = max(8, int(round(10.5 * fs)))
        f_center_dg = max(6, int(round(8 * fs)))
        f_leg = max(6, int(round(7 * fs)))

        self.create_text(w // 2, 11, text=f"{self.title}  ·  South Indian",
                         font=("Tahoma", f_title, "bold"), fill="#262626")

        # Collect natal planets per sign
        sg_n = {i: [] for i in range(12)}
        asc_rashi = None
        if self.grahas:
            al = self.grahas.get("Lagna", {}).get("longitude")
            if al is not None:
                asc_rashi = int(al / 30) % 12
            elif "rashi" in self.grahas.get("Lagna", {}):
                asc_rashi = int(self.grahas["Lagna"]["rashi"]) % 12

        for gn in ALL_GRAHAS + ["Lagna"]:
            pd = self.grahas.get(gn, {})
            if not pd: continue
            lon = pd.get("longitude")
            if lon is not None:
                sign = int(lon / 30) % 12
            elif "rashi" in pd:
                sign = int(pd["rashi"]) % 12
            else:
                continue
            sg_n[sign].append((GRAHA_SYMBOLS.get(gn, gn[:2]), bool(pd.get("retro"))))

        # Collect transit planets per sign
        sg_t = {i: [] for i in range(12)}
        for gn in ALL_GRAHAS:
            pd = self.t_grahas.get(gn, {})
            if not pd: continue
            lon = pd.get("longitude")
            if lon is None: continue
            sg_t[int(lon / 30) % 12].append(GRAHA_SYMBOLS.get(gn, gn[:2]))

        # Draw cells
        for (row, col_), rn in SI_GRID.items():
            cx0 = x0 + col_ * c
            cy0 = y0 + row * c
            cx1 = cx0 + c
            cy1 = cy0 + c
            bg = "#FFFCE8" if rn == asc_rashi else "#FFFFFF"
            self.create_rectangle(cx0, cy0, cx1, cy1, fill=bg, outline="#CCCCCC", width=1)

            fw = "bold" if rn == asc_rashi else "normal"
            fc = "#B45309" if rn == asc_rashi else "#555555"
            lbl = f"{RASHI_ABBR[rn]} ({rn+1})" if rn == asc_rashi else RASHI_ABBR[rn]
            self.create_text((cx0 + cx1) // 2, cy0 + 10, text=lbl,
                             font=(_DEVA_FONT, f_abbr, fw), fill=fc)

            nat = sg_n.get(rn, [])
            visible = nat[:5]
            for i, (sym, retro) in enumerate(visible):
                px_ = cx0 + 4 + (i % 3) * (c // 3)
                py_ = cy0 + 23 + (i // 3) * 14
                col_ = "#CC2200" if retro else "#111111"
                self.create_text(px_, py_, text=sym, font=(_DEVA_FONT, f_planet, "bold"), fill=col_, anchor="w")
            if len(nat) > 5:
                self.create_text(cx1 - 4, cy1 - 5, text=f"+{len(nat)-5}",
                                 font=("Tahoma", f_abbr, "bold"), fill="#CC2200", anchor="e")

            tran = sg_t.get(rn, [])
            if tran:
                txt = "·".join(tran[:3])
                self.create_text(cx0 + 4, cy1 - 8, text=f"T·{txt}",
                                 font=(_DEVA_FONT, f_tran), fill=XP_BLUE2, anchor="w")

        # Centre box
        ccx0 = x0 + c
        ccy0 = y0 + c
        ccx1 = x0 + 3 * c
        ccy1 = y0 + 3 * c
        self.create_rectangle(ccx0, ccy0, ccx1, ccy1, fill="#F8FAFC", outline="#CCCCCC", width=1)
        lg = RASHI_DEVA[asc_rashi] if asc_rashi is not None else "---"
        ld = self.grahas.get("Lagna", {}).get("rashi_ansh", 0)
        cmx = (ccx0 + ccx1) // 2
        cmy = (ccy0 + ccy1) // 2
        self.create_text(cmx, cmy - 14, text="\u0932\u0917\u094d\u0928 (Lagna)",
                         font=(_DEVA_FONT, f_center_lg, "bold"), fill="#2563EB")
        self.create_text(cmx, cmy + 2, text=lg, font=(_DEVA_FONT, f_center_nm, "bold"), fill="#000000")
        self.create_text(cmx, cmy + 18, text=f"{ld:.1f}°", font=(_DEVA_FONT, f_center_dg), fill="#555555")

        # Legend row & Interactive Toggle Badge
        leg_y = y1 + 14
        if self.t_grahas:
            self.create_text(x0 + 4, leg_y, text="● Natal  ●· Transit (blue)  ● Retro (red)",
                             font=("Tahoma", f_leg), fill="#52525B", anchor="w")
        else:
            self.create_text(x0 + 4, leg_y, text="● Natal (black)   ● Retrograde (red)",
                             font=("Tahoma", f_leg), fill="#52525B", anchor="w")

        # Interactive Switch Button Badge (Bottom Right)
        bw = int(round(88 * min(fs, 1.3)))
        bx1 = x1
        bx0 = bx1 - bw
        self.create_rectangle(bx0, leg_y - 8, bx1, leg_y + 8, fill="#F4F4F5", outline="#D4D4D8", width=1, tags="style_toggle")
        self.create_text((bx0 + bx1) // 2, leg_y, text="⇄ North Indian", font=("Tahoma", f_leg, "bold"), fill="#2563EB", tags="style_toggle")
        self.tag_bind("style_toggle", "<Button-1>", lambda e: self.toggle_style())
        self.tag_bind("style_toggle", "<Enter>", lambda e: self.config(cursor="hand2"))
        self.tag_bind("style_toggle", "<Leave>", lambda e: self.config(cursor=""))


# ══════════════════════════════════════════════════════════════════════════════
#  GEOCODER
# ══════════════════════════════════════════════════════════════════════════════
class Geocoder:
    _last_call: float = 0.0
    _MIN_INTERVAL: float = 1.5

    @classmethod
    def lookup(cls, place):
        elapsed = time.monotonic() - cls._last_call
        if elapsed < cls._MIN_INTERVAL:
            time.sleep(cls._MIN_INTERVAL - elapsed)
        cls._last_call = time.monotonic()

        url  = (f"https://nominatim.openstreetmap.org/search?"
                f"q={urllib.parse.quote(place)}&format=json&limit=1")
        req  = urllib.request.Request(url, headers={"User-Agent":"JyotishHelper/6.0"})

        def _fetch():
            with urllib.request.urlopen(req, timeout=8) as r:
                return json.loads(r.read())

        try:
            data = _fetch()
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                time.sleep(2.0); cls._last_call = time.monotonic()
                try: data = _fetch()
                except urllib.error.HTTPError as e2:
                    if e2.code == 429:
                        raise ValueError("Nominatim rate limit. Wait ~10 s and retry.") from e2
                    raise
            else:
                raise ValueError(f"HTTP {exc.code}: {exc.reason}") from exc

        if not data:
            raise ValueError(f"Location not found: '{place}'")
        return float(data[0]["lat"]), float(data[0]["lon"]), data[0]["display_name"]


# ══════════════════════════════════════════════════════════════════════════════
#  SORTABLE TREEVIEW
# ══════════════════════════════════════════════════════════════════════════════
def sort_treeview_col(tree, col, reverse=False):
    items = [(tree.set(k,col),k) for k in tree.get_children("")]
    def _key(v):
        try: return (0, float(v.replace("°","").replace("'","").strip()))
        except: return (1, str(v).lower())
    items.sort(key=lambda t:_key(t[0]), reverse=reverse)
    for i,(_,k) in enumerate(items): tree.move(k,"",i)
    for c in tree["columns"]:
        tree.heading(c, text=tree.heading(c)["text"].rstrip(" ↑↓"))
    arrow = " ↓" if reverse else " ↑"
    tree.heading(col, text=tree.heading(col)["text"]+arrow,
                 command=lambda: sort_treeview_col(tree,col,not reverse))


# ══════════════════════════════════════════════════════════════════════════════
#  DATE HELPERS
# ══════════════════════════════════════════════════════════════════════════════
_DT_FMT = "%Y-%m-%d %H:%M"

def ser_dt(dt):  return dt.strftime(_DT_FMT) if isinstance(dt,datetime) else str(dt)

def deser_dt(s):
    for fmt in (_DT_FMT,"%Y-%m-%d %H:%M:%S","%Y-%m-%dT%H:%M"):
        try: return datetime.strptime(s,fmt)
        except: continue
    raise ValueError(f"Cannot parse date '{s}' (expected {_DT_FMT}).")


# ══════════════════════════════════════════════════════════════════════════════
#  STREAMING STRUCTURED RENDERER (Dual-Layer Explainable AI)
# ══════════════════════════════════════════════════════════════════════════════
class StreamingStructuredRenderer:
    """
    Progressively parses incoming LLM stream tokens into high-contrast, dual-layer
    styled segments (Domain headers, Predictions, Kundli Alignment, Classical Sutras).
    Avoids monolithic text walls and allows interactive view filtering.
    """

    def __init__(self, text_widget, scroll_cb=None):
        self.text_widget = text_widget
        self.scroll_cb = scroll_cb
        self.buffer = ""
        self.active_tag = "answer"

    def reset(self):
        self.buffer = ""
        self.active_tag = "answer"

    def feed(self, token):
        if not token:
            return
        self.buffer += token
        self._drain()

    def _drain(self):
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            self._render_line(line)

    def _render_line(self, line):
        clean = line.strip()
        if not clean:
            self._insert("\n", "answer")
            return

        # 1. Section Header: [SECTION: CAREER] or ### CAREER
        if clean.startswith("[SECTION:") or clean.startswith("### "):
            title = clean.replace("[SECTION:", "").replace("###", "").rstrip("]").strip()
            self._insert(f"\n\n❖  {title.upper()}\n", "section_header")
            return

        # 2. Prediction: [PREDICTION]: ... or • PREDICTION: ...
        if clean.startswith("[PREDICTION]:") or clean.startswith("• PREDICTION:"):
            text = clean.replace("[PREDICTION]:", "").replace("• PREDICTION:", "").strip()
            self._insert("\n• PREDICTION: ", "pred_badge")
            self._render_inline(f"{text}\n", "prediction")
            return

        # 3. Kundli Basis: [KUNDLI BASIS]: ... or ↳ KUNDLI BASIS: ...
        if clean.startswith("[KUNDLI BASIS]:") or clean.startswith("↳ KUNDLI BASIS:"):
            text = clean.replace("[KUNDLI BASIS]:", "").replace("↳ KUNDLI BASIS:", "").strip()
            self._insert("  🪐 KUNDLI ALIGNMENT: ", "basis_badge")
            self._render_inline(f"{text}\n", "kundli_basis")
            return

        # 4. Practical Guidance / Remedy: [PRACTICAL GUIDANCE]: ... or [REMEDY]: ...
        if (clean.startswith("[PRACTICAL GUIDANCE]:") or clean.startswith("[REMEDY]:")
            or clean.startswith("• REMEDY:") or clean.startswith("↳ REMEDY:")):
            prefix = "[PRACTICAL GUIDANCE]:" if clean.startswith("[PRACTICAL GUIDANCE]:") else (
                "[REMEDY]:" if clean.startswith("[REMEDY]:") else (
                    "• REMEDY:" if clean.startswith("• REMEDY:") else "↳ REMEDY:"
                )
            )
            text = clean[len(prefix):].strip()
            self._insert("  🌿 ACTIONABLE GUIDANCE: ", "remedy_badge")
            self._render_inline(f"{text}\n", "remedy")
            return

        # 5. Classical Sutra: [SUTRA]: ... or ↳ SUTRA: ...
        if clean.startswith("[SUTRA]:") or clean.startswith("↳ SUTRA:"):
            text = clean.replace("[SUTRA]:", "").replace("↳ SUTRA:", "").strip()
            self._insert("  📜 CLASSICAL SUTRA: ", "sutra_badge")
            self._render_inline(f"{text}\n", "sutra")
            return

        # 6. Normal text or bullet line
        self._render_inline(f"{line}\n", "answer")

    def _render_inline(self, text, base_tag):
        """Render text, parsing **bold** spans if present."""
        import re
        if "**" not in text:
            self._insert(text, base_tag)
            return

        parts = []
        last = 0
        for m in re.finditer(r'\*\*(.+?)\*\*', text, re.DOTALL):
            if m.start() > last:
                parts.append((text[last:m.start()], base_tag))
            parts.append((m.group(1), "answer_bold"))
            last = m.end()
        if last < len(text):
            parts.append((text[last:], base_tag))

        for content, tag in parts:
            if content:
                self._insert(content, tag)

    def _insert(self, text, tag):
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", text, tag)
        self.text_widget.configure(state="disabled")
        if self.scroll_cb:
            self.scroll_cb()

    def finish(self):
        if self.buffer:
            self._render_line(self.buffer)
            self.buffer = ""
