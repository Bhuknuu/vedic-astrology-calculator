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
#  TTK STYLE  (pixel-perfect XP Luna)
# ══════════════════════════════════════════════════════════════════════════════
def xp_style(root):
    """Brutalist minimalist ttk.Style — dark surfaces, white data areas, sharp corners."""
    s = ttk.Style(root)
    try: s.theme_use("clam")
    except: pass

    # ── Core frames / labels ──
    s.configure("XP.TFrame",   background=XP_BG)
    s.configure("XP.TLabel",   background=XP_BG,      font=("Tahoma",9),        foreground=XP_TEXT_D)
    s.configure("Head.TLabel", background=XP_BG,      font=("Tahoma",9,"bold"), foreground=XP_BLUE2)
    s.configure("Small.TLabel",background=XP_BG,      font=("Tahoma",8),        foreground=XP_TEXT_M)
    s.configure("White.TLabel",background=XP_FIELD,   font=("Tahoma",9),        foreground="#000000")

    # ── Buttons: flat, sharp corners ──
    s.configure("XP.TButton",
        background=XP_BTN, font=("Tahoma",9), padding=(8,4),
        relief="flat", borderwidth=1, foreground=XP_TEXT_D)
    s.map("XP.TButton",
        background=[("active","#3A3A3A"),("pressed","#1A1A1A")],
        foreground=[("active",XP_TEXT_D)])

    # Primary action button (blue, bold)
    s.configure("Blue.TButton",
        background=XP_BLUE, font=("Tahoma",9,"bold"),
        foreground="#FFFFFF", padding=(10,5), relief="flat", borderwidth=0)
    s.map("Blue.TButton",
        background=[("active",XP_BLUE2),("pressed","#1D4ED8")])

    # Stop/danger button
    s.configure("Red.TButton",
        background="#991B1B", font=("Tahoma",9,"bold"),
        foreground="#FFFFFF", padding=(8,4), relief="flat", borderwidth=0)
    s.map("Red.TButton",
        background=[("active","#B91C1C"),("pressed","#7F1D1D")])

    # ── Entry / Combobox — white field, black text ──
    s.configure("XP.TEntry",
        fieldbackground=XP_FIELD, foreground="#000000",
        font=("Tahoma",9), padding=3, relief="flat", borderwidth=1)
    s.configure("XP.TCombobox",
        fieldbackground=XP_FIELD, foreground="#000000", font=("Tahoma",9))
    s.map("XP.TCombobox",
        fieldbackground=[("readonly",XP_BTN)],
        foreground=[("readonly",XP_TEXT_D)])

    # ── Notebook tabs: dark with blue active indicator ──
    s.configure("XP.TNotebook", background=XP_BG, tabmargins=[0,4,0,0])
    s.configure("XP.TNotebook.Tab",
        background=XP_BTN, font=("Tahoma",9), padding=[10,4],
        foreground=XP_TEXT_M)
    s.map("XP.TNotebook.Tab",
        background=[("selected",XP_SURFACE),("active",XP_BTN)],
        foreground=[("selected",XP_BLUE2),("active",XP_TEXT_D)],
        padding=[("selected",[10,5])])

    # ── Treeview: white rows, dark heading, blue selection ──
    s.configure("XP.Treeview",
        background=XP_FIELD, font=("Tahoma",9),
        rowheight=22, fieldbackground=XP_FIELD, foreground="#000000")
    s.configure("XP.Treeview.Heading",
        background=XP_SURFACE, font=("Tahoma",9,"bold"),
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
#  RASHI CHART CANVAS
# ══════════════════════════════════════════════════════════════════════════════
class RashiChart(tk.Canvas):
    """
    South-Indian static rashi chart.

    v6 features:
    * Transit overlay: pass transit_grahas= dict to overlay 'T·' prefixed
      planets in XP_BLUE2 color, so natal + transit are on the same canvas.
    * Retrograde in dark-red color (no 'v' suffix).
    * Stellium guard: >5 planets shows '+N more'.
    * Retrograde legend at bottom.
    """

    def __init__(self, parent, title="", size=330, **kw):
        super().__init__(parent, width=size, height=size+34,
                         bg="#FFFFFF", highlightthickness=1,
                         highlightbackground=XP_BORDER, **kw)
        self.size    = size
        self.title   = title
        self.grahas  = {}
        self.t_grahas= {}   # transit planets
        self.cell    = size // 4
        self.bind("<Configure>", self._resize)
        self.draw()

    def _resize(self, e):
        self.size = min(e.width, e.height) - 34
        self.cell = max(self.size // 4, 1)
        self.draw()

    def set_data(self, grahas, title=None, transit_grahas=None):
        self.grahas   = grahas
        self.t_grahas = transit_grahas or {}
        if title: self.title = title
        self.draw()

    def draw(self):
        self.delete("all")
        c = self.cell; s = self.size; p = 2

        self.create_text(s//2+p, 12, text=self.title,
                         font=("Tahoma",9,"bold"), fill="#333333")

        # ── Collect natal planets per sign ──
        sg_n = {i:[] for i in range(12)}
        asc_rashi = None
        if self.grahas:
            al = self.grahas.get("Lagna",{}).get("longitude")
            if al is not None: asc_rashi = int(al/30)
        for gn in ALL_GRAHAS + ["Lagna"]:
            pd = self.grahas.get(gn,{})
            if not pd: continue
            lon = pd.get("longitude")
            if lon is None: continue
            sg_n[int(lon/30)].append((GRAHA_SYMBOLS.get(gn,gn[:2]), bool(pd.get("retro"))))

        # ── Collect transit planets per sign ──
        sg_t = {i:[] for i in range(12)}
        for gn in ALL_GRAHAS:
            pd = self.t_grahas.get(gn,{})
            if not pd: continue
            lon = pd.get("longitude")
            if lon is None: continue
            sg_t[int(lon/30)].append(GRAHA_SYMBOLS.get(gn,gn[:2]))

        # ── Draw cells ──
        for (row,col_),rn in SI_GRID.items():
            x0=col_*c+p; y0=row*c+24+p; x1=x0+c; y1=y0+c
            bg = "#FFFCE8" if rn==asc_rashi else "#FFFFFF"
            self.create_rectangle(x0,y0,x1,y1,fill=bg,outline="#CCCCCC",width=1)

            fw = "bold" if rn==asc_rashi else "normal"
            fc = "#000000" if rn==asc_rashi else "#555555"
            self.create_text((x0+x1)//2, y0+10, text=RASHI_ABBR[rn],
                             font=(_DEVA_FONT,7,fw), fill=fc)

            # Natal planets
            nat = sg_n.get(rn,[]); visible = nat[:5]
            for i,(sym,retro) in enumerate(visible):
                px_=x0+4+(i%3)*(c//3); py_=y0+23+(i//3)*14
                col_="#CC2200" if retro else "#000000"
                self.create_text(px_,py_,text=sym,font=(_DEVA_FONT,9),fill=col_,anchor="w")
            if len(nat)>5:
                self.create_text(x1-4,y1-5,text=f"+{len(nat)-5}",
                                 font=("Tahoma",7),fill="#CC2200",anchor="e")

            # Transit planets (small, blue, bottom of cell)
            tran = sg_t.get(rn,[])
            if tran:
                txt = "·".join(tran[:3])
                self.create_text(x0+4,y1-8,text=txt,
                                 font=(_DEVA_FONT,7),fill=XP_BLUE2,anchor="w")

        # ── Centre box ──
        cx0=c+p; cy0=c+24+p; cx1=3*c+p; cy1=3*c+24+p
        self.create_rectangle(cx0,cy0,cx1,cy1,fill="#F0F0F0",outline="#CCCCCC",width=1)
        lg  = RASHI_DEVA[asc_rashi] if asc_rashi is not None else "---"
        ld  = self.grahas.get("Lagna",{}).get("rashi_ansh",0)
        mx  = (cx0+cx1)//2; my=(cy0+cy1)//2
        self.create_text(mx,my-14,text="\u0932\u0917\u094d\u0928",
                         font=(_DEVA_FONT,9,"bold"),fill="#000000")
        self.create_text(mx,my+2, text=lg,  font=(_DEVA_FONT,10,"bold"),fill="#000000")
        self.create_text(mx,my+18,text=f"{ld:.1f}°",font=(_DEVA_FONT,8),fill="#555555")

        # ── Legend row ──
        if self.t_grahas:
            self.create_text(s//2+p,s+38,
                text="● Natal   \u25cf\u00b7 Transit (blue)   ● Retro (red)",
                font=("Tahoma",7),fill="#555555",anchor="center")
        else:
            self.create_text(s//2+p,s+38,
                text="● Retro = red",
                font=("Tahoma",7),fill="#CC2200",anchor="center")


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
