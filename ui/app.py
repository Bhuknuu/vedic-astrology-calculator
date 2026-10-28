# -*- coding: utf-8 -*-
"""
app.py  v6.0 — Windows XP Luna, perfected.
==========================================
New in v6
---------
* XPGradientHeader    — Luna deep-blue gradient (Canvas, resizes live)
* XPStatusBar         — Explorer multi-panel status strip
* Pure XP Classic     — theme switcher removed; one perfect theme
* Bhava Chalit tab    — planet shift table + cusp table
* Ashtakavarga tab    — planet selector, 12-sign bindu grid, Sarva view
* Gochara tab         — today's transits overlaid on natal chart + table
* Dasha balance       — "Xy Ym Zd" at birth in info bar
* Keyboard shortcuts  — Ctrl+G generate, Ctrl+S save, Ctrl+L load, F5 transit
* XP LabelFrame groups in input panel
* Sort bindings on all Treeview columns
* Bold chat (**text**) rendered with answer_bold tag
* Multiline chat input (tk.Text, Enter=send, Shift+Enter=newline)
* Geocoding ✓ flash confirmation label
"""

import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import json
import os
from datetime import datetime

from core.constants import (
    RASHI, RASHI_DEVA, GRAHA_DEVA, AVASTHA_DEVA, BALA_DEVA,
    ALL_GRAHAS, DASHA_KRAM,
    TZ_LABELS, TZ_VALUES,
    AYANAMSA_OPTIONS,
    DASHA_YEAR_OPTIONS, DASHA_YEAR_NAMES,
    XP_BG, XP_SURFACE, XP_BORDER, XP_FIELD, XP_BLUE, XP_BLUE2,
    XP_BTN, XP_GRAY, XP_WARN, XP_WARN_FG, XP_TEXT_D, XP_TEXT_M,
    ASHTAK_PLANETS,
)
from core.astro_engine import compute_chart, compute_transits, SWE_OK
from core.vedic_engine import (
    yoga as calc_yoga,
    dosha as calc_dosha,
    vimshottari,
    shadbala,
    sthiti,
    varga as calc_varga,
    navamsa,
    ashtakavarga,
    sarvashtakavarga,
    format_dasha_balance,
    panchanga,
    gemstone_prescription,
    compute_pratyantardasha_for_ad,
)
from ai.prediction_engine import PredictionEngine, ConversationManager
from ai.ollama_engine import OllamaEngine
from ui.ui_widgets import (
    xp_style, titled_frame, xp_labelframe,
    XPGradientHeader, XPStatusBar, XPTooltip,
    RashiChart, Geocoder,
    ser_dt, deser_dt, ensure_utf8_stdout, _resolve_devanagari_font,
    sort_treeview_col,
)

MONTHS = {
    "January":1,"February":2,"March":3,"April":4,"May":5,"June":6,
    "July":7,"August":8,"September":9,"October":10,"November":11,"December":12,
}
MONTH_NAMES = list(MONTHS.keys())

VARGA_LIST = [
    "D-1 (Rasi)","D-2 (Hora)","D-3 (Drekkana)","D-4 (Chaturthamsha)",
    "D-7 (Saptamsha)","D-9 (Navamsa)","D-10 (Dashamsha)",
    "D-12 (Dwadashamsha)","D-16 (Shodashamsha)","D-20 (Vimshamsha)",
    "D-24 (Chaturvimshamsha)","D-27 (Bhamsha)","D-30 (Trishamsha)",
    "D-40 (Khavedamsha)","D-45 (Akshavedamsha)","D-60 (Shashtiamsha)",
]
VARGA_DESC = {
    "D-1":"Body & personality","D-2":"Wealth","D-3":"Siblings & courage",
    "D-4":"Property","D-7":"Children","D-9":"Marriage & soul (Navamsa)",
    "D-10":"Career","D-12":"Parents","D-16":"Vehicles","D-20":"Spiritual practice",
    "D-24":"Education","D-27":"Strength","D-30":"Karmic debt",
    "D-40":"Maternal lineage","D-45":"Paternal lineage","D-60":"Past-life karma",
}


# ══════════════════════════════════════════════════════════════════════════════
class JyotishApp:

    def __init__(self, root):
        self.root = root
        ensure_utf8_stdout()
        _resolve_devanagari_font(root)

        self.root.title("Vedic Astrology Calculator  v6.0")
        self.root.configure(bg=XP_BG)
        self.root.geometry("1260x860")
        self.root.minsize(960, 680)

        # ── Chart state ────────────────────────────────────────────────────
        self.grahas  = {}; self.yogas  = []; self.doshas = []
        self.dashas  = []; self.janam_vivaran = ""
        self.chart_text = ""; self.chart_json_str = ""
        self.transit_grahas = {}
        self.panchanga_data = {}
        self.gemstones_data = []
        self.conv_manager = ConversationManager()
        self._current_gen_text = ""
        self._current_selected_md = None

        # ── UI variables ───────────────────────────────────────────────────
        self.ayanamsa_var   = tk.StringVar(value=AYANAMSA_OPTIONS[0])
        self.tz_label_var   = tk.StringVar(value=TZ_LABELS[0])
        self.tz_val         = tk.DoubleVar(value=5.5)
        self.varga_var      = tk.StringVar(value="D-9 (Navamsa)")
        self.ollama_model_var= tk.StringVar(value="qwen2.5:7b")
        self.chart_info_var = tk.StringVar(value="No chart generated yet.")
        self.dasha_info_var = tk.StringVar(value="Generate a chart to view Dasha periods.")
        self.varga_desc_var = tk.StringVar(value="Select a Varga and click Show.")
        self.dasha_year_var = tk.StringVar(value=DASHA_YEAR_NAMES[0])
        self.ashtak_var     = tk.StringVar(value="Sarva (All)")

        # ── Streaming state ────────────────────────────────────────────────
        self._cancel_event            = threading.Event()
        self._streaming               = False
        self._has_cleared_placeholder = False
        self._render_buf              = ""

        xp_style(root)
        self._build()
        self._bind_shortcuts()
        threading.Thread(target=self._check_ollama_bg, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════
    #  SHORTCUTS
    # ══════════════════════════════════════════════════════════════════════
    def _bind_shortcuts(self):
        self.root.bind("<Control-g>", lambda e: self._calculate())
        self.root.bind("<Control-G>", lambda e: self._calculate())
        self.root.bind("<Control-s>", lambda e: self._save_kundali())
        self.root.bind("<Control-S>", lambda e: self._save_kundali())
        self.root.bind("<Control-l>", lambda e: self._load_kundali())
        self.root.bind("<Control-L>", lambda e: self._load_kundali())
        self.root.bind("<F5>",        lambda e: self._refresh_transits())

    # ══════════════════════════════════════════════════════════════════════
    #  BUILD LAYOUT
    # ══════════════════════════════════════════════════════════════════════
    def _build(self):
        # ── Gradient header ────────────────────────────────────────────────
        self.header = XPGradientHeader(
            self.root,
            title="  Vedic Astrology Calculator  v6.0  ·  Qwen2.5-7B  ·  Offline AI",
            subtitle="pyswisseph active" if SWE_OK else "⚠ fallback math mode"
        )
        self.header.pack(fill="x")

        # ── Main area (Paned for adjustability) ───────────────────────────
        main = tk.PanedWindow(self.root, orient="horizontal", bg=XP_BORDER,
                              sashrelief="flat", sashwidth=3, bd=0)
        main.pack(fill="both", expand=True, padx=4, pady=4)

        # Left: input panel
        left = tk.Frame(main, bg=XP_BG, padx=4, pady=2)
        main.add(left, minsize=290, width=320)
        self._build_input(left)

        # Right: notebook
        right = tk.Frame(main, bg=XP_BG, padx=2, pady=2)
        main.add(right, minsize=500)
        self.nb = ttk.Notebook(right, style="XP.TNotebook")
        self.nb.pack(fill="both", expand=True)
        self._tab_rashi()
        self._tab_graha()
        self._tab_panchanga()
        self._tab_varga()
        self._tab_dasha()
        self._tab_remedies()
        self._tab_yoga()
        self._tab_shadbala()
        self._tab_chalit()
        self._tab_ashtak()
        self._tab_gochara()
        self._tab_phaladesh()

        # ── Status bar ─────────────────────────────────────────────────────
        self.sb = XPStatusBar(self.root, panels=[
            ("msg",   45, "Ready"),
            ("engine",18, "Engine: —"),
            ("ay",    22, "Ayanamsa: —"),
            ("yogas",  12, "Yogas: 0"),
            ("ollama", 18, "Ollama: checking"),
        ])
        self.sb.pack(fill="x", side="bottom")

    # ── Input panel ──────────────────────────────────────────────────────────
    def _lbl(self, p, t, **kw):  return ttk.Label(p, text=t, style="XP.TLabel", **kw)
    def _hlbl(self, p, t, **kw): return ttk.Label(p, text=t, style="Head.TLabel", **kw)

    def _build_input(self, parent):
        # ── DATE ──────────────────────────────────────────────────────────
        gf = xp_labelframe(parent, "Birth Date"); gf.pack(fill="x", pady=(0,4))
        r = 0
        self._lbl(gf,"Day:").grid(row=r,column=0,sticky="e",padx=(0,3))
        self.day_var = tk.StringVar(value="13")
        ttk.Combobox(gf,textvariable=self.day_var,width=4,
                     values=[str(i) for i in range(1,32)],
                     style="XP.TCombobox").grid(row=r,column=1,sticky="w",padx=(0,6))
        self._lbl(gf,"Month:").grid(row=r,column=2,sticky="e",padx=(0,3))
        self.month_var = tk.StringVar(value="December")
        ttk.Combobox(gf,textvariable=self.month_var,width=10,values=MONTH_NAMES,
                     style="XP.TCombobox",state="readonly").grid(row=r,column=3,sticky="w"); r+=1
        self._lbl(gf,"Year:").grid(row=r,column=0,sticky="e",padx=(0,3),pady=(4,0))
        self.year_var = tk.StringVar(value="2006")
        ttk.Entry(gf,textvariable=self.year_var,width=8,
                  style="XP.TEntry").grid(row=r,column=1,columnspan=3,sticky="w",pady=(4,0))
        gf.grid_columnconfigure(1,weight=1); gf.grid_columnconfigure(3,weight=1)

        # ── TIME ──────────────────────────────────────────────────────────
        tf = xp_labelframe(parent,"Birth Time"); tf.pack(fill="x",pady=(0,4))
        self._lbl(tf,"Hour:").grid(row=0,column=0,sticky="e",padx=(0,3))
        self.hour_var = tk.StringVar(value="16")
        ttk.Combobox(tf,textvariable=self.hour_var,width=4,
                     values=[f"{i:02d}" for i in range(24)],
                     style="XP.TCombobox").grid(row=0,column=1,sticky="w",padx=(0,6))
        self._lbl(tf,"Min:").grid(row=0,column=2,sticky="e",padx=(0,3))
        self.min_var = tk.StringVar(value="27")
        ttk.Combobox(tf,textvariable=self.min_var,width=4,
                     values=[f"{i:02d}" for i in range(60)],
                     style="XP.TCombobox").grid(row=0,column=3,sticky="w"); r=1
        self._lbl(tf,"Timezone:").grid(row=r,column=0,sticky="e",padx=(0,3),pady=(4,0))
        tz_cb = ttk.Combobox(tf,textvariable=self.tz_label_var,values=TZ_LABELS,
                             width=22,style="XP.TCombobox",state="readonly")
        tz_cb.grid(row=r,column=1,columnspan=3,sticky="ew",pady=(4,0))
        tz_cb.bind("<<ComboboxSelected>>",
                   lambda _: self.tz_val.set(TZ_VALUES.get(self.tz_label_var.get(),0.0)))
        tf.grid_columnconfigure(1,weight=1); tf.grid_columnconfigure(3,weight=1)

        # ── PLACE ─────────────────────────────────────────────────────────
        pf = xp_labelframe(parent,"Birth Place"); pf.pack(fill="x",pady=(0,4))
        self._lbl(pf,"City:").grid(row=0,column=0,sticky="e",padx=(0,3))
        self.place_var = tk.StringVar(value="Kanpur, India")
        ttk.Entry(pf,textvariable=self.place_var,width=20,
                  style="XP.TEntry").grid(row=0,column=1,columnspan=3,sticky="ew")
        # Geocode row
        geo_row = tk.Frame(pf,bg=XP_BG)
        geo_row.grid(row=1,column=0,columnspan=4,pady=(4,2),sticky="ew")
        geo_btn = ttk.Button(geo_row,text="Find Location  (Geocode)",
                             command=self._lookup_geo,style="XP.TButton")
        geo_btn.pack(side="left",fill="x",expand=True)
        XPTooltip(geo_btn,"Ctrl+F5: geocode city name → lat/lon")
        self.geo_ok_lbl = tk.Label(geo_row,text="",bg=XP_BG,fg="#4ADE80",
                                   font=("Tahoma",8,"bold"))
        self.geo_ok_lbl.pack(side="left",padx=4)
        self._lbl(pf,"Lat:").grid(row=2,column=0,sticky="e",padx=(0,3))
        self.lat_var = tk.StringVar(value="26.4499")
        ttk.Entry(pf,textvariable=self.lat_var,width=9,
                  style="XP.TEntry").grid(row=2,column=1,sticky="w",padx=(0,6))
        self._lbl(pf,"Lon:").grid(row=2,column=2,sticky="e",padx=(0,3))
        self.lon_var = tk.StringVar(value="80.3319")
        ttk.Entry(pf,textvariable=self.lon_var,width=9,
                  style="XP.TEntry").grid(row=2,column=3,sticky="w")
        pf.grid_columnconfigure(1,weight=1); pf.grid_columnconfigure(3,weight=1)

        # ── NATIVE & OPTIONS ──────────────────────────────────────────────
        nf = xp_labelframe(parent,"Native & Options"); nf.pack(fill="x",pady=(0,4))
        for ri,(lbl_txt,var_name,default,vals,ww) in enumerate([
            ("Name:", "name_var", "", None, 20),
            ("Ayanamsa:", "ayanamsa_var", AYANAMSA_OPTIONS[0],
             AYANAMSA_OPTIONS if SWE_OK else [AYANAMSA_OPTIONS[0]], 20),
            ("Dasha Year:", "dasha_year_var", DASHA_YEAR_NAMES[0], DASHA_YEAR_NAMES, 20),
        ]):
            self._lbl(nf,lbl_txt).grid(row=ri,column=0,sticky="e",padx=(0,3),pady=2)
            if vals is None:
                var = tk.StringVar(value=default)
                setattr(self, var_name, var)
                ttk.Entry(nf,textvariable=var,width=ww,
                          style="XP.TEntry").grid(row=ri,column=1,sticky="ew",pady=2)
            else:
                var = getattr(self, var_name, None) or tk.StringVar(value=default)
                setattr(self, var_name, var)
                ttk.Combobox(nf,textvariable=var,width=ww,values=vals,
                             style="XP.TCombobox",state="readonly"
                             ).grid(row=ri,column=1,sticky="ew",pady=2)
        nf.grid_columnconfigure(1,weight=1)

        # ── ACTION DOCK ───────────────────────────────────────────────────
        act = tk.Frame(parent, bg=XP_BG)
        act.pack(fill="x", pady=(6, 2))
        gen_btn = ttk.Button(act, text="⚡  CALCULATE CHART  (Ctrl+G)",
                             command=self._calculate, style="Blue.TButton")
        gen_btn.pack(fill="x", ipady=5)
        XPTooltip(gen_btn, "Ctrl+G — calculate planetary positions & dasha")

        sf = tk.Frame(act, bg=XP_BG)
        sf.pack(fill="x", pady=(4, 0))
        sv = ttk.Button(sf, text="💾 Save", command=self._save_kundali, style="XP.TButton")
        sv.pack(side="left", fill="x", expand=True, padx=(0, 2))
        XPTooltip(sv, "Ctrl+S — Save chart profile to JSON")
        ld = ttk.Button(sf, text="📂 Load", command=self._load_kundali, style="XP.TButton")
        ld.pack(side="left", fill="x", expand=True, padx=(2, 2))
        XPTooltip(ld, "Ctrl+L — Load saved chart profile")
        rep = ttk.Button(sf, text="📄 Report", command=self._export_report, style="XP.TButton")
        rep.pack(side="left", fill="x", expand=True, padx=(2, 0))
        XPTooltip(rep, "Export comprehensive horoscope summary report (.txt / .md)")

    # ══════════════════════════════════════════════════════════════════════
    #  TABS
    # ══════════════════════════════════════════════════════════════════════

    def _tab_rashi(self):
        f = tk.Frame(self.nb, bg=XP_BG)
        self.nb.add(f, text="Birth Chart")
        top = tk.Frame(f, bg=XP_BG)
        top.pack(fill="both", expand=True, padx=4, pady=4)
        top.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(1, weight=1)
        top.grid_rowconfigure(0, weight=1)

        d1o, d1i = titled_frame(top, "Rashi (D-1) — Birth Chart")
        d1o.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)
        self.rasi_chart = RashiChart(d1i, title="Birth Chart (D-1)", size=330)
        self.rasi_chart.pack(fill="both", expand=True, padx=2, pady=2)

        d9o, d9i = titled_frame(top, "Navamsa (D-9) — Marriage & Soul")
        d9o.grid(row=0, column=1, sticky="nsew", padx=3, pady=3)
        self.navamsa_chart = RashiChart(d9i, title="Navamsa (D-9)", size=330)
        self.navamsa_chart.pack(fill="both", expand=True, padx=2, pady=2)

        ib = tk.Frame(f, bg=XP_SURFACE, relief="solid", bd=1)
        ib.pack(fill="x", padx=6, pady=(0, 4))
        self.chart_info_lbl = tk.Label(ib, textvariable=self.chart_info_var,
                                       bg=XP_SURFACE, fg=XP_TEXT_D,
                                       font=("Tahoma", 8), anchor="w", justify="left")
        self.chart_info_lbl.pack(fill="x", padx=8, pady=4)
        ib.bind("<Configure>", lambda e: self.chart_info_lbl.config(wraplength=max(e.width - 24, 200)))

    def _tab_graha(self):
        f = tk.Frame(self.nb,bg=XP_BG); self.nb.add(f,text="Planets")
        o,i = titled_frame(f,"Planet Position Details",padx=5,pady=5)
        o.pack(fill="both",expand=True,padx=4,pady=4)
        cols = ("Graha","Lon °","Rashi","Ansha","Nakshatra","Pada","Nak.Lord","Bhava","Dignity","Speed","R?")
        self.g_tree = ttk.Treeview(i,columns=cols,show="headings",style="XP.Treeview",height=14)
        ws = [75,82,100,62,130,50,85,60,100,65,40]
        for c,w in zip(cols,ws):
            self.g_tree.heading(c,text=c,
                command=lambda col=c: sort_treeview_col(self.g_tree,col))
            self.g_tree.column(c,width=w,minwidth=35,stretch=True,anchor="center")
        vsb = ttk.Scrollbar(i,orient="vertical",command=self.g_tree.yview)
        self.g_tree.configure(yscrollcommand=vsb.set)
        self.g_tree.pack(side="left",fill="both",expand=True); vsb.pack(side="right",fill="y")
        for tag,bg,fg in [("uchcha","#DCFCE7","#14532D"),("neecha","#FEE2E2","#7F1D1D"),
                           ("swakshetra","#DBEAFE","#1E3A8A"),("vakri","#FEF3C7","#78350F")]:
            self.g_tree.tag_configure(tag,background=bg,foreground=fg)

    def _tab_varga(self):
        f = tk.Frame(self.nb,bg=XP_BG); self.nb.add(f,text="Divisional")
        tb = tk.Frame(f,bg=XP_BG); tb.pack(fill="x",padx=5,pady=4)
        self._lbl(tb,"Select Varga:").pack(side="left")
        ttk.Combobox(tb,textvariable=self.varga_var,values=VARGA_LIST,
                     width=24,style="XP.TCombobox",state="readonly").pack(side="left",padx=5)
        ttk.Button(tb,text="Show",style="XP.TButton",command=self._show_varga).pack(side="left",padx=3)
        ma = tk.Frame(f,bg=XP_BG); ma.pack(fill="both",expand=True,padx=4,pady=4)
        ma.grid_columnconfigure(0,weight=1)
        ma.grid_columnconfigure(1,weight=1)
        ma.grid_rowconfigure(0,weight=1)

        co,ci = titled_frame(ma,"Varga Chart"); co.grid(row=0,column=0,sticky="nsew",padx=3,pady=3)
        self.varga_chart = RashiChart(ci,title="",size=310); self.varga_chart.pack(fill="both",expand=True,padx=2,pady=2)

        to,ti = titled_frame(ma,"Planet Varga Status",padx=4,pady=4)
        to.grid(row=0,column=1,sticky="nsew",padx=3,pady=3)
        vc = ("Graha","D-1 Rashi","D-n Rashi","D-n Dignity")
        self.v_tree = ttk.Treeview(ti,columns=vc,show="headings",style="XP.Treeview",height=14)
        for c in vc:
            self.v_tree.heading(c,text=c,command=lambda col=c: sort_treeview_col(self.v_tree,col))
            self.v_tree.column(c,width=110,stretch=True,anchor="center")
        self.v_tree.pack(fill="both",expand=True)
        self.v_tree.tag_configure("uchcha",background="#DCFCE7",foreground="#14532D")
        self.v_tree.tag_configure("neecha",background="#FEE2E2",foreground="#7F1D1D")
        tk.Label(ti,textvariable=self.varga_desc_var,bg=XP_SURFACE,fg=XP_TEXT_D,font=("Tahoma",8,"italic"),
                 relief="solid",bd=1,anchor="w",padx=6,pady=3).pack(fill="x",pady=3)

    def _tab_dasha(self):
        f = tk.Frame(self.nb,bg=XP_BG); self.nb.add(f,text="Dasha")
        self.dasha_title_lbl = tk.Label(f,text="Vimshottari Dasha  (Tropical year basis)",
                 bg=XP_BG,font=("Tahoma",9,"bold"),fg=XP_TEXT_D)
        self.dasha_title_lbl.pack(anchor="w",padx=6,pady=3)
        pn = tk.PanedWindow(f,orient="horizontal",bg=XP_BORDER,sashrelief="flat",sashwidth=3,bd=0)
        pn.pack(fill="both",expand=True,padx=4,pady=3)
        mo,mi = titled_frame(pn,"Mahadasha (Main Period)",padx=3); pn.add(mo,stretch="always")
        mc = ("Lord","Start","End","Years","Status")
        self.md_tree = ttk.Treeview(mi,columns=mc,show="headings",style="XP.Treeview",height=12)
        for c,w in zip(mc,[80,90,90,55,80]):
            self.md_tree.heading(c,text=c); self.md_tree.column(c,width=w,stretch=True,anchor="center")
        sb1 = ttk.Scrollbar(mi,orient="vertical",command=self.md_tree.yview)
        self.md_tree.configure(yscrollcommand=sb1.set)
        self.md_tree.pack(side="left",fill="both",expand=True); sb1.pack(side="right",fill="y")
        self.md_tree.bind("<<TreeviewSelect>>",self._on_md_sel)
        self.md_tree.tag_configure("current",background="#FEF3C7",foreground="#78350F")
        self.md_tree.tag_configure("past",   foreground="#71717A")
        ao,ai = titled_frame(pn,"Antardasha (Sub-Period)",padx=3); pn.add(ao,stretch="always")
        ac = ("MD Lord","AD Lord","Start","End","Days","Status")
        self.ad_tree = ttk.Treeview(ai,columns=ac,show="headings",style="XP.Treeview",height=12)
        for c,w in zip(ac,[75,75,90,90,55,70]):
            self.ad_tree.heading(c,text=c); self.ad_tree.column(c,width=w,stretch=True,anchor="center")
        sb2 = ttk.Scrollbar(ai,orient="vertical",command=self.ad_tree.yview)
        self.ad_tree.configure(yscrollcommand=sb2.set)
        self.ad_tree.pack(side="left",fill="both",expand=True); sb2.pack(side="right",fill="y")
        self.ad_tree.tag_configure("current",background="#FEF3C7",foreground="#78350F")
        self.ad_tree.tag_configure("past",   foreground="#71717A")
        self.ad_tree.bind("<<TreeviewSelect>>", self._on_ad_sel)

        po,pi = titled_frame(pn,"Pratyantardasha (Level-3)",padx=3); pn.add(po,stretch="always")
        pc = ("PD Lord","Start","End","Days","Status")
        self.pd_tree = ttk.Treeview(pi,columns=pc,show="headings",style="XP.Treeview",height=12)
        for c,w in zip(pc,[65,80,80,45,60]):
            self.pd_tree.heading(c,text=c); self.pd_tree.column(c,width=w,stretch=True,anchor="center")
        sb3 = ttk.Scrollbar(pi,orient="vertical",command=self.pd_tree.yview)
        self.pd_tree.configure(yscrollcommand=sb3.set)
        self.pd_tree.pack(side="left",fill="both",expand=True); sb3.pack(side="right",fill="y")
        self.pd_tree.tag_configure("current",background="#FEF3C7",foreground="#78350F")
        self.pd_tree.tag_configure("past",   foreground="#71717A")

        ib2 = tk.Frame(f,bg=XP_SURFACE,relief="solid",bd=1); ib2.pack(fill="x",padx=6,pady=3)
        self.dasha_info_bar = tk.Label(ib2,textvariable=self.dasha_info_var,
                 bg=XP_SURFACE,fg=XP_TEXT_D,font=("Tahoma",8),anchor="w",padx=6,pady=3)
        self.dasha_info_bar.pack(fill="x")
        ib2.bind("<Configure>",lambda e: self.dasha_info_bar.config(wraplength=max(e.width-20,200)))

    def _tab_panchanga(self):
        f = tk.Frame(self.nb, bg=XP_BG)
        self.nb.add(f, text="Panchanga")
        to, ti = titled_frame(f, "Panchanga — The 5 Limbs of Vedic Time", padx=6, pady=6)
        to.pack(fill="both", expand=True, padx=4, pady=4)

        cols = ("Limb", "Name", "Details / Paksha", "Ruler / Lord", "Auspiciousness / Elapsed")
        self.panch_tree = ttk.Treeview(ti, columns=cols, show="headings", style="XP.Treeview", height=8)
        ws = [90, 140, 160, 120, 180]
        for c, w in zip(cols, ws):
            self.panch_tree.heading(c, text=c)
            self.panch_tree.column(c, width=w, stretch=True, anchor="center")
        self.panch_tree.pack(fill="both", expand=True, padx=2, pady=2)
        self.panch_tree.tag_configure("auspicious", background="#DCFCE7", foreground="#14532D")
        self.panch_tree.tag_configure("inauspicious", background="#FEE2E2", foreground="#7F1D1D")
        self.panch_tree.tag_configure("neutral", background="#FFFFFF", foreground="#000000")

        desc_box = tk.Frame(ti, bg=XP_SURFACE, relief="solid", bd=1)
        desc_box.pack(fill="x", padx=2, pady=(6, 2))
        self.panch_desc_var = tk.StringVar(value="Generate or load a chart to view the 5 Vedic time limbs.")
        tk.Label(desc_box, textvariable=self.panch_desc_var, bg=XP_SURFACE, fg=XP_TEXT_D,
                 font=("Tahoma", 8), anchor="w", justify="left").pack(fill="x", padx=8, pady=6)

    def _tab_remedies(self):
        f = tk.Frame(self.nb, bg=XP_BG)
        self.nb.add(f, text="Remedies & Gems")

        self.lagna_benefic_var = tk.StringVar(value="Lagna Functional Status: Generate a chart first.")
        top_b = tk.Frame(f, bg=XP_SURFACE, relief="solid", bd=1)
        top_b.pack(fill="x", padx=6, pady=(6, 3))
        tk.Label(top_b, textvariable=self.lagna_benefic_var, bg=XP_SURFACE, fg=XP_TEXT_D,
                 font=("Tahoma", 8, "bold"), anchor="w", justify="left").pack(fill="x", padx=8, pady=5)

        pn = tk.PanedWindow(f, orient="horizontal", bg=XP_BORDER, sashrelief="flat", sashwidth=3, bd=0)
        pn.pack(fill="both", expand=True, padx=4, pady=3)

        lo, li = titled_frame(pn, "Classical Gemstone Prescriptions (BPHS Safety Filter)", padx=4, pady=4)
        pn.add(lo, stretch="always")

        cols = ("Planet", "Prescription", "Primary Gem", "Weight", "Metal", "Finger", "Day")
        self.gem_tree = ttk.Treeview(li, columns=cols, show="headings", style="XP.Treeview", height=12)
        for c, w in zip(cols, [70, 110, 100, 80, 80, 85, 95]):
            self.gem_tree.heading(c, text=c)
            self.gem_tree.column(c, width=w, stretch=True, anchor="center")
        gsb = ttk.Scrollbar(li, orient="vertical", command=self.gem_tree.yview)
        self.gem_tree.configure(yscrollcommand=gsb.set)
        self.gem_tree.pack(side="left", fill="both", expand=True)
        gsb.pack(side="right", fill="y")
        self.gem_tree.bind("<<TreeviewSelect>>", self._on_gem_sel)
        self.gem_tree.tag_configure("prescribed", background="#DCFCE7", foreground="#14532D")
        self.gem_tree.tag_configure("contraindicated", background="#FEE2E2", foreground="#7F1D1D")

        ro, ri = titled_frame(pn, "Prescription Details & Safe Remedies", padx=4, pady=4)
        pn.add(ro, stretch="always")
        self.gem_detail_text = tk.Text(ri, wrap="word", bg=XP_FIELD, fg="#111111",
                                       font=("Tahoma", 9), relief="flat", bd=1, state="disabled")
        self.gem_detail_text.pack(fill="both", expand=True, padx=2, pady=2)

    def _tab_yoga(self):
        f = tk.Frame(self.nb,bg=XP_BG); self.nb.add(f,text="Yogas")
        pn = tk.PanedWindow(f,orient="vertical",bg=XP_BORDER,sashrelief="flat",sashwidth=3,bd=0)
        pn.pack(fill="both",expand=True,padx=4,pady=4)

        yo,yi = titled_frame(pn,"Planetary Yogas",padx=4); pn.add(yo,stretch="always")
        self.yoga_text = tk.Text(yi,wrap="word",height=9,relief="flat",bd=0,
                                 bg=XP_FIELD,fg="#000000",font=("Tahoma",9),
                                 state="disabled",cursor="arrow")
        ysb = ttk.Scrollbar(yi,orient="vertical",command=self.yoga_text.yview)
        self.yoga_text.configure(yscrollcommand=ysb.set)
        self.yoga_text.pack(side="left",fill="both",expand=True); ysb.pack(side="right",fill="y")
        self._cfg_card_tags(self.yoga_text)

        do,di = titled_frame(pn,"Planetary Doshas",padx=4); pn.add(do,stretch="always")
        self.dosha_text = tk.Text(di,wrap="word",height=7,relief="flat",bd=0,
                                  bg=XP_FIELD,fg="#000000",font=("Tahoma",9),
                                  state="disabled",cursor="arrow")
        dsb = ttk.Scrollbar(di,orient="vertical",command=self.dosha_text.yview)
        self.dosha_text.configure(yscrollcommand=dsb.set)
        self.dosha_text.pack(side="left",fill="both",expand=True); dsb.pack(side="right",fill="y")
        self._cfg_card_tags(self.dosha_text)

    def _cfg_card_tags(self, txt):
        txt.tag_configure("card_name",  font=("Tahoma",9,"bold"), foreground=XP_BLUE2)
        txt.tag_configure("card_good",  font=("Tahoma",8,"bold"), foreground="#16A34A")
        txt.tag_configure("card_bad",   font=("Tahoma",8,"bold"), foreground="#DC2626")
        txt.tag_configure("card_neu",   font=("Tahoma",8,"bold"), foreground="#A1A1AA")
        txt.tag_configure("card_desc",  font=("Tahoma",9),        foreground="#111111")
        txt.tag_configure("card_graha", font=("Tahoma",8,"bold"), foreground=XP_BLUE2)
        txt.tag_configure("card_sep",   font=("Tahoma",7),        foreground="#A1A1AA")

    def _tab_shadbala(self):
        f = tk.Frame(self.nb,bg=XP_BG); self.nb.add(f,text="Shadbala")
        disc = tk.Frame(f,bg=XP_WARN,relief="flat",bd=1)
        disc.pack(fill="x",padx=6,pady=(6,2))
        tk.Label(disc,
            text=("PARTIAL SHADBALA — 4 of 6 components only.  "
                  "Missing: Drik Bala & Ayana Bala.  "
                  "Total and Pass/Fail columns hidden to prevent misinterpretation."),
            bg=XP_WARN,font=("Tahoma",8),fg=XP_WARN_FG,anchor="w",justify="left"
        ).pack(fill="x",padx=6,pady=4)
        o,i = titled_frame(f,"Shadbala — Component Virupa Scores (4/6)",padx=5,pady=5)
        o.pack(fill="both",expand=True,padx=4,pady=4)
        sc = ("Graha","Uchcha B.","Saptav. B.","Kendradi B.","Cheshta B.","Naisarg. B.","Dignity","Bhava Method")
        self.sb_tree = ttk.Treeview(i,columns=sc,show="headings",style="XP.Treeview",height=10)
        for c,w in zip(sc,[75,72,78,80,72,78,100,100]):
            self.sb_tree.heading(c,text=c,command=lambda col=c: sort_treeview_col(self.sb_tree,col))
            self.sb_tree.column(c,width=w,stretch=True,anchor="center")
        vsb = ttk.Scrollbar(i,orient="vertical",command=self.sb_tree.yview)
        self.sb_tree.configure(yscrollcommand=vsb.set)
        self.sb_tree.pack(side="left",fill="both",expand=True); vsb.pack(side="right",fill="y")

    def _tab_chalit(self):
        """Bhava Chalit — planet shift comparison table + cusp listing."""
        f = tk.Frame(self.nb,bg=XP_BG); self.nb.add(f,text="Bhava Chalit")

        info = tk.Frame(f,bg=XP_SURFACE,relief="solid",bd=1)
        info.pack(fill="x",padx=6,pady=(6,2))
        info_lbl = tk.Label(info,
            text=("Bhava Chalit uses Porphyry (Sripathi) cusp degrees to re-assign planets to houses.  "
                  "A planet is in the Bhava whose cusp it has passed most recently.  "
                  "Planets that shift bhava from their Rashi position are highlighted in orange."),
            bg=XP_SURFACE,font=("Tahoma",8),fg=XP_TEXT_M,anchor="w",justify="left")
        info_lbl.pack(fill="x",padx=6,pady=4)
        info.bind("<Configure>",lambda e: info_lbl.config(wraplength=max(e.width-20,200)))

        pn = tk.PanedWindow(f,orient="horizontal",bg=XP_BORDER,sashrelief="flat",sashwidth=3,bd=0)
        pn.pack(fill="both",expand=True,padx=4,pady=4)

        # Left: planet shift table
        lo,li = titled_frame(pn,"Planet Bhava Comparison",padx=4,pady=4); pn.add(lo,stretch="always")
        cc = ("Graha","Longitude","Rashi","Rashi Bhava","Chalit Bhava","Shifted?")
        self.chalit_tree = ttk.Treeview(li,columns=cc,show="headings",style="XP.Treeview",height=14)
        for c,w in zip(cc,[85,90,110,100,100,70]):
            self.chalit_tree.heading(c,text=c); self.chalit_tree.column(c,width=w,stretch=True,anchor="center")
        csb = ttk.Scrollbar(li,orient="vertical",command=self.chalit_tree.yview)
        self.chalit_tree.configure(yscrollcommand=csb.set)
        self.chalit_tree.pack(side="left",fill="both",expand=True); csb.pack(side="right",fill="y")
        self.chalit_tree.tag_configure("shifted",  background="#FEF3C7",foreground="#78350F")
        self.chalit_tree.tag_configure("same",     background="#FFFFFF", foreground="#000000")

        # Right: cusp table
        ro,ri = titled_frame(pn,"Porphyry House Cusps",padx=4,pady=4); pn.add(ro,stretch="always")
        cpc = ("Bhava","Cusp Degree","Rashi","Sign Ansha")
        self.cusp_tree = ttk.Treeview(ri,columns=cpc,show="headings",style="XP.Treeview",height=14)
        for c,w in zip(cpc,[60,110,110,90]):
            self.cusp_tree.heading(c,text=c); self.cusp_tree.column(c,width=w,stretch=True,anchor="center")
        self.cusp_tree.pack(fill="both",expand=True)
        for i in range(12):
            bg = "#F4F4F5" if i%2==0 else "#FFFFFF"
            self.cusp_tree.tag_configure(f"r{i}",background=bg)

    def _tab_ashtak(self):
        """Ashtakavarga — planet selector, 12-sign bindu grid."""
        f = tk.Frame(self.nb,bg=XP_BG); self.nb.add(f,text="Ashtakavarga")

        # Toolbar
        tb = tk.Frame(f,bg=XP_BG); tb.pack(fill="x",padx=6,pady=(6,2))
        self._lbl(tb,"Show:").pack(side="left")
        ashtak_opts = ["Sarva (All)"] + [GRAHA_DEVA.get(p,p) for p in ASHTAK_PLANETS]
        self.ashtak_var = tk.StringVar(value="Sarva (All)")
        ttk.Combobox(tb,textvariable=self.ashtak_var,width=20,values=ashtak_opts,
                     style="XP.TCombobox",state="readonly").pack(side="left",padx=5)
        ttk.Button(tb,text="Show",style="XP.TButton",
                   command=self._show_ashtak).pack(side="left",padx=3)
        tk.Label(tb,text="Green ≥ 4 bindus  ·  Red < 4  ·  Max: 8 per planet",
                 bg=XP_BG,fg=XP_TEXT_M,font=("Tahoma",8)).pack(side="left",padx=12)

        # Grid
        o,i = titled_frame(f,"Bindu Scores per Rashi",padx=4,pady=4)
        o.pack(fill="both",expand=True,padx=4,pady=4)
        av_cols = ("Planet",) + tuple(RASHI)
        self.av_tree = ttk.Treeview(i,columns=av_cols,show="headings",style="XP.Treeview",height=10)
        self.av_tree.heading("Planet",text="Planet")
        self.av_tree.column("Planet",width=90,stretch=False,anchor="center")
        for r in RASHI:
            self.av_tree.heading(r,text=r[:4])
            self.av_tree.column(r,width=52,stretch=True,anchor="center")
        avsb = ttk.Scrollbar(i,orient="vertical",command=self.av_tree.yview)
        self.av_tree.configure(yscrollcommand=avsb.set)
        self.av_tree.pack(side="left",fill="both",expand=True); avsb.pack(side="right",fill="y")
        for tag,bg,fg in [("strong","#DCFCE7","#14532D"),("weak","#FEE2E2","#7F1D1D"),
                          ("mid","#FFFFFF","#000000"),("sarva","#DBEAFE","#1E3A8A")]:
            self.av_tree.tag_configure(tag,background=bg,foreground=fg)

    def _tab_gochara(self):
        """Gochara (Transit) — today's planets overlaid on natal chart + table."""
        f = tk.Frame(self.nb,bg=XP_BG); self.nb.add(f,text="Gochara")

        # Toolbar
        tb = tk.Frame(f,bg=XP_BG); tb.pack(fill="x",padx=6,pady=(6,2))
        self.transit_date_var = tk.StringVar(value="—")
        tk.Label(tb,text="Transit date (UTC):",bg=XP_BG,font=("Tahoma",9,"bold"),
                 fg=XP_TEXT_D).pack(side="left")
        tk.Label(tb,textvariable=self.transit_date_var,bg=XP_BG,
                 font=("Tahoma",9),fg=XP_TEXT_M).pack(side="left",padx=8)
        ref = ttk.Button(tb,text="⟳  Refresh  (F5)",style="XP.TButton",
                         command=self._refresh_transits)
        ref.pack(side="left",padx=3)
        XPTooltip(ref,"F5 — fetch current planetary positions")

        # Layout: chart + table (paned, draggable)
        pn = tk.PanedWindow(f,orient="horizontal",bg=XP_BORDER,sashrelief="flat",sashwidth=3,bd=0)
        pn.pack(fill="both",expand=True,padx=4,pady=4)

        co,ci = titled_frame(pn,"Natal + Transit Chart",padx=3,pady=3); pn.add(co,stretch="always")
        self.transit_chart = RashiChart(ci,title="Natal + Transits",size=340)
        self.transit_chart.pack(fill="both",expand=True,padx=2,pady=2)

        to,ti = titled_frame(pn,"Transit Planet Positions",padx=4,pady=4); pn.add(to,stretch="always")
        tc = ("Planet","Transit Sign","Transit Bhava","Natal Sign","Natal Bhava","Note")
        self.transit_tree = ttk.Treeview(ti,columns=tc,show="headings",style="XP.Treeview",height=14)
        for c,w in zip(tc,[85,110,100,110,100,120]):
            self.transit_tree.heading(c,text=c)
            self.transit_tree.column(c,width=w,stretch=True,anchor="center")
        tsb = ttk.Scrollbar(ti,orient="vertical",command=self.transit_tree.yview)
        self.transit_tree.configure(yscrollcommand=tsb.set)
        self.transit_tree.pack(side="left",fill="both",expand=True); tsb.pack(side="right",fill="y")
        self.transit_tree.tag_configure("notable",background="#FEF3C7",foreground="#78350F")
        self.transit_tree.tag_configure("normal", background="#FFFFFF", foreground="#000000")

    def _tab_phaladesh(self):
        f = tk.Frame(self.nb,bg=XP_BG); self.nb.add(f,text="AI Reading")

        # Ollama status strip
        sb_f = tk.Frame(f,bg=XP_SURFACE,relief="flat",bd=1)
        sb_f.pack(fill="x",padx=6,pady=(5,2))
        self.ollama_dot = tk.Label(sb_f,text="\u25cf",bg=XP_SURFACE,fg="#52525B",font=("Tahoma",12))
        self.ollama_dot.pack(side="left",padx=(6,2),pady=3)
        self.ollama_status_var = tk.StringVar(value="Checking Ollama...")
        tk.Label(sb_f,textvariable=self.ollama_status_var,bg=XP_SURFACE,
                 font=("Tahoma",9,"bold"),fg=XP_TEXT_M).pack(side="left",pady=3)
        ttk.Button(sb_f,text="Refresh",style="XP.TButton",
                   command=lambda: threading.Thread(target=self._check_ollama_bg,daemon=True).start()
                   ).pack(side="right",padx=6,pady=3)

        mc = tk.Frame(f,bg=XP_BG); mc.pack(fill="x",padx=6,pady=(2,0))
        tk.Label(mc,text="Model:",bg=XP_BG,font=("Tahoma",9),fg=XP_TEXT_M).pack(side="left")
        self.model_combo = ttk.Combobox(mc,textvariable=self.ollama_model_var,
                                        width=28,style="XP.TCombobox")
        self.model_combo.pack(side="left",padx=4)
        tk.Label(mc,text="Qwen2.5-7B-Q6_K recommended  ·  Offline GPU",
                 bg=XP_BG,font=("Tahoma",8),fg=XP_TEXT_M).pack(side="left")

        self.setup_frame = tk.Frame(f,bg=XP_SURFACE,relief="flat",bd=1)
        tk.Label(self.setup_frame,
            text=("Ollama is not running.\n\n"
                  "  1. Install Ollama: https://ollama.ai\n"
                  "  2. ollama create qwen2.5:7b -f Modelfile\n"
                  "  3. ollama serve\n  4. Click Refresh above."),
            bg=XP_SURFACE,font=("Tahoma",9),fg=XP_TEXT_D,anchor="w",justify="left"
        ).pack(fill="both",padx=10,pady=8)

        ar = tk.Frame(f,bg=XP_BG); ar.pack(fill="x",padx=6,pady=(4,0))
        ttk.Button(ar,text="⚡ Generate Full Reading",style="Blue.TButton",
                   command=self._auto_analyse).pack(side="left",padx=(0,6),ipady=4)
        self.stop_btn = ttk.Button(ar,text="\u25a0 Stop",style="Red.TButton",
                                   command=self._stop_generation)

        co,ci = titled_frame(f,"Vedic Predictions & Q&A",padx=5,pady=4)
        co.pack(fill="both",expand=True,padx=5,pady=3)
        self.chat = tk.Text(ci,font=("Tahoma",9),bg="#FFFFFE",fg="#111111",
                            wrap="word",height=15,relief="flat",bd=1,state="disabled")
        chat_sb = ttk.Scrollbar(ci,orient="vertical",command=self.chat.yview)
        self.chat.configure(yscrollcommand=chat_sb.set)
        self.chat.pack(side="left",fill="both",expand=True)
        chat_sb.pack(side="right",fill="y")
        self._configure_chat_tags()

        ir = tk.Frame(ci,bg=XP_BG); ir.pack(fill="x",pady=(4,0))
        tk.Label(ir,text="Enter ↵ send  ·  Shift+↵ newline",
                 bg=XP_BG,fg=XP_TEXT_M,font=("Tahoma",7)).pack(side="bottom",anchor="w",padx=2)
        self.chat_in = tk.Text(ir,height=3,font=("Tahoma",9),
                               bg="#FFFFFF",fg="#000000",wrap="word",relief="flat",bd=1)
        self.chat_in.pack(side="left",fill="x",expand=True,padx=(0,3))
        self.chat_in.bind("<Return>",self._on_chat_enter)
        ttk.Button(ir,text="Ask",style="Blue.TButton",command=self._send).pack(side="right",anchor="n")
        ttk.Button(ir,text="Clear",style="XP.TButton",command=self._clear_chat).pack(side="right",padx=3,anchor="n")

        self._chat_add("system",
            "Generate a chart first, then click 'Generate Full Reading' or ask any question.\n"
            "All inference runs locally on your GPU — no internet required.\n\n")

    def _configure_chat_tags(self):
        self.chat.tag_configure("question",    foreground=XP_BLUE2, font=("Tahoma",9,"bold"))
        self.chat.tag_configure("answer",      foreground="#111111", font=("Tahoma",9))
        self.chat.tag_configure("answer_bold", foreground="#111111", font=("Tahoma",9,"bold"))
        self.chat.tag_configure("system",      foreground="#71717A", font=("Tahoma",8,"italic"))
        self.chat.tag_configure("header",      foreground=XP_BLUE2, font=("Tahoma",9,"bold"))
        self.chat.tag_configure("error",       foreground="#DC2626", font=("Tahoma",9,"italic"))

    # ══════════════════════════════════════════════════════════════════════
    #  OLLAMA
    # ══════════════════════════════════════════════════════════════════════
    def _check_ollama_bg(self):
        alive  = OllamaEngine.ping()
        models = OllamaEngine.list_models() if alive else []
        self.root.after(0,lambda: self._apply_ollama_status(alive,models))

    def _apply_ollama_status(self,alive,models):
        if alive and models:
            self.ollama_dot.configure(fg="#22C55E")
            self.ollama_status_var.set(f"Ollama: Connected  —  {len(models)} model(s) available")
            self.model_combo.configure(values=models)
            if self.ollama_model_var.get() not in models:
                self.ollama_model_var.set(models[0])
            self.setup_frame.pack_forget()
            self.sb.set("ollama","Ollama: online")
        elif alive:
            self.ollama_dot.configure(fg="#EAB308")
            self.ollama_status_var.set("Ollama: Running — no models loaded.")
            self.setup_frame.pack(fill="x",padx=6,pady=3)
            self.sb.set("ollama","Ollama: no models")
        else:
            self.ollama_dot.configure(fg="#EF4444")
            self.ollama_status_var.set("Ollama: Not running — see setup guide.")
            self.setup_frame.pack(fill="x",padx=6,pady=3)
            self.sb.set("ollama","Ollama: offline")

    # ══════════════════════════════════════════════════════════════════════
    #  CHAT
    # ══════════════════════════════════════════════════════════════════════
    def _chat_add(self,tag,text):
        def _do():
            self.chat.configure(state="normal")
            self.chat.insert("end",text,tag)
            self.chat.see("end")
            self.chat.configure(state="disabled")
        self.root.after(0,_do)

    def _clear_chat(self):
        self.chat.configure(state="normal"); self.chat.delete("1.0","end")
        self.chat.configure(state="disabled")

    def _set_streaming(self,on):
        self._streaming = on
        if on: self.stop_btn.pack(side="left",padx=6)
        else:  self.stop_btn.pack_forget(); self._cancel_event.clear()

    def _stop_generation(self):
        self._cancel_event.set()
        OllamaEngine.request_stop(self.ollama_model_var.get())
        self._chat_add("system","\n[ Generation stopped ]\n\n")

    def _on_chat_enter(self,event):
        if event.state & 0x1: return
        self._send(); return "break"

    # ══════════════════════════════════════════════════════════════════════
    #  GEOCODE
    # ══════════════════════════════════════════════════════════════════════
    def _lookup_geo(self):
        def run():
            pl = self.place_var.get().strip()
            if not pl: return
            self.sb.set("msg",f"Searching: {pl}...")
            try:
                la,lo,nm = Geocoder.lookup(pl)
                self.lat_var.set(f"{la:.4f}"); self.lon_var.set(f"{lo:.4f}")
                self.sb.set("msg",f"Found: {nm[:50]}")
                self.root.after(0,self._flash_geo_ok)
            except Exception as e:
                self.sb.set("msg",f"Geocoding failed")
                self.root.after(0,lambda: messagebox.showinfo("Geocoding",f"Not found.\n\n{e}"))
        threading.Thread(target=run,daemon=True).start()

    def _flash_geo_ok(self):
        self.geo_ok_lbl.configure(text="  ✓ Found",fg="#4ADE80")
        self.root.after(2000,lambda: self.geo_ok_lbl.configure(text=""))

    # ══════════════════════════════════════════════════════════════════════
    #  CALCULATE
    # ══════════════════════════════════════════════════════════════════════
    def _calculate(self):
        def run():
            try:
                self.sb.set("msg","Calculating positions...")
                mo_raw = self.month_var.get().strip()
                mo     = MONTHS.get(mo_raw) or MONTHS.get(mo_raw.capitalize())
                if mo is None:
                    try: mo=int(mo_raw)
                    except: raise ValueError(f"Invalid month '{mo_raw}'")
                d     = int(self.day_var.get())
                y     = int(self.year_var.get())
                h     = int(self.hour_var.get())
                mi    = int(self.min_var.get())
                tz    = float(self.tz_val.get())
                lat   = float(self.lat_var.get())
                lon_g = float(self.lon_var.get())
                naam  = self.name_var.get() or "Native"
                ay_k  = self.ayanamsa_var.get()
                yd    = DASHA_YEAR_OPTIONS.get(self.dasha_year_var.get(),365.24219)

                self.janam_vivaran = (
                    f"{naam}  |  {d}/{mo}/{y}  {h:02d}:{mi:02d}  TZ:{tz:+.2f}  |  "
                    f"{self.place_var.get()}  |  Lat:{lat:.4f}  Lon:{lon_g:.4f}")
                self.root.after(0,lambda n=naam:
                    self.root.title(f"Vedic Astrology — {n}  v6.0"))

                self.grahas = compute_chart(y,mo,d,h,mi,tz,lat,lon_g,ay_k)
                lr = self.grahas.get("Lagna",{}).get("rashi",0)

                self.sb.set("msg","Analysing Yogas...")
                self.yogas  = calc_yoga(self.grahas,lr)
                self.doshas = calc_dosha(self.grahas,lr)

                self.sb.set("msg","Computing Dasha...")
                jd = self.grahas["_meta"]["jd"]
                cl = self.grahas["Chandra"]["longitude"]
                self.dashas = vimshottari(cl,jd,year_days=yd)

                self.sb.set("msg","Computing Panchanga & Remedies...")
                sl = self.grahas.get("Surya",{}).get("longitude",0)
                self.panchanga_data = panchanga(sl, cl, datetime(y, mo, d, h, mi))
                self.gemstones_data = [
                    gemstone_prescription(g, lr, body_weight_kg=60.0)
                    for g in ALL_GRAHAS[:7]
                ]

                # Flush AI cache and reset conversational memory for new chart
                chart_id = f"{naam}_{d}{mo}{y}_{h}{mi}"
                self.conv_manager.reset_for_new_chart(chart_id, naam)
                OllamaEngine.clear_cache(self.ollama_model_var.get())
                self._clear_chat()
                self._chat_add("system",
                    f"=== NEW CHART CALCULATED: {naam} ===\n"
                    f"Birth Details: {self.janam_vivaran}\n"
                    "[ AI Cache & KV state freshly initialized — zero cross-chart leakage ]\n\n")

                self.chart_text     = PredictionEngine.chart_text_full(
                    self.grahas,self.yogas,self.doshas,self.dashas,self.janam_vivaran)
                self.chart_json_str = PredictionEngine.chart_json(
                    self.grahas,self.yogas,self.doshas,self.dashas)

                ys = self.dasha_year_var.get().split("(")[0].strip()
                self.root.after(0,lambda: self.dasha_title_lbl.configure(
                    text=f"Vimshottari Dasha  ·  {ys}"))
                self.root.after(0,self._refresh_all)
            except Exception as e:
                import traceback
                err = traceback.format_exc()
                self.root.after(0,lambda: messagebox.showerror("Error",f"{e}\n\n{err[:500]}"))
                self.root.after(0,lambda: self.sb.set("msg",f"Error: {e}"))

        threading.Thread(target=run,daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════
    #  REFRESH PIPELINE
    # ══════════════════════════════════════════════════════════════════════
    def _refresh_all(self):
        delay = 0
        for fn in [self._upd_info,self._upd_charts,self._upd_grahas,
                   self._upd_panchanga,self._upd_remedies,
                   self._upd_dasha,self._upd_yoga,self._upd_shadbala,
                   self._upd_chalit,self._upd_ashtak]:
            self.root.after(delay,fn); delay+=20

    def _upd_info(self):
        lr  = self.grahas.get("Lagna",{}).get("rashi",0)
        ay  = self.grahas.get("_meta",{}).get("ay",0)
        eng = self.grahas.get("_meta",{}).get("engine","")
        bm  = self.grahas.get("Surya",{}).get("bhava_method","whole_sign")
        self.chart_info_var.set(
            f"  {self.janam_vivaran}  |  Engine: {eng}  |  Ayanamsa: {ay:.4f}°  |  "
            f"Lagna: {RASHI_DEVA[lr]}  |  Bhava: {bm}  |  "
            f"Yogas: {len(self.yogas)}  |  Doshas: {len(self.doshas)}")
        self.sb.set("engine",f"Engine: {eng}")
        self.sb.set("ay",    f"Ayanamsa: {ay:.2f}°")
        self.sb.set("yogas", f"Yogas: {len(self.yogas)}")

        mn  = self.grahas.get("Chandra",{}).get("nakshatra_naam","")
        ml  = self.grahas.get("Chandra",{}).get("nakshatra_swami","")
        bal_str = ""
        if self.dashas:
            first = self.dashas[0]
            # Compute birth datetime from input fields
            try:
                d   = int(self.day_var.get()); mo = MONTHS.get(self.month_var.get(),1)
                y   = int(self.year_var.get()); h  = int(self.hour_var.get())
                mi  = int(self.min_var.get());  tz = float(self.tz_val.get())
                from datetime import timezone, timedelta
                birth_dt = datetime(y,mo,d,h,mi) - timedelta(hours=tz)
                bal = format_dasha_balance(first["start"], birth_dt)
                bal_str = f"  |  Born: {GRAHA_DEVA.get(first['lord'],first['lord'])} MD, balance {bal}"
            except Exception:
                pass
        self.dasha_info_var.set(
            f"  Moon: {mn}  |  Lord: {GRAHA_DEVA.get(ml,ml)}{bal_str}"
            f"  |  Yogas: {len(self.yogas)}  |  Doshas: {len(self.doshas)}")
        self.sb.set("msg","Chart ready")

    def _upd_charts(self):
        self.rasi_chart.set_data(self.grahas,"Birth Chart (D-1)")
        nav = {}
        for gn,pd in self.grahas.items():
            if gn.startswith("_"): continue
            lon = pd.get("longitude")
            if lon is None: continue
            ns=navamsa(lon); nd=(lon%30)*9%30
            nav[gn]={**pd,"longitude":ns*30+nd,"rashi":ns,"rashi_naam":RASHI[ns],"rashi_ansh":nd}
        nav_lr=nav.get("Lagna",{}).get("rashi",0)
        for gn,pd in nav.items():
            if gn in ("Lagna","_meta"): continue
            pd["bhava"]=(pd["rashi"]-nav_lr)%12+1
        self.navamsa_chart.set_data(nav,"Navamsa (D-9)")

    def _upd_grahas(self):
        for r in self.g_tree.get_children(): self.g_tree.delete(r)
        for gn in ALL_GRAHAS+["Lagna"]:
            pd=self.grahas.get(gn,{})
            if not pd: continue
            lon=pd.get("longitude",0)
            d=int(lon%30); m=int((lon%30-d)*60)
            vk="R" if pd.get("retro") else ""
            st_k=sthiti(gn,pd.get("rashi",0)); st_d=AVASTHA_DEVA.get(st_k,st_k)
            tag=("uchcha" if st_k=="Uchcha" else "neecha" if st_k=="Neecha"
                 else "swakshetra" if st_k in ("Swakshetra","Moolatrikona")
                 else "vakri" if vk else "")
            self.g_tree.insert("","end",values=(
                GRAHA_DEVA.get(gn,gn),f"{lon:.4f}",RASHI_DEVA[pd.get("rashi",0)],
                f"{d}°{m:02d}'",pd.get("nakshatra_naam",""),pd.get("pada",""),
                GRAHA_DEVA.get(pd.get("nakshatra_swami",""),pd.get("nakshatra_swami","")),
                pd.get("bhava",""),st_d,f"{pd.get('speed',0):.3f}",vk,
            ),tags=(tag,))

    def _upd_dasha(self):
        for r in self.md_tree.get_children(): self.md_tree.delete(r)
        for r in self.ad_tree.get_children(): self.ad_tree.delete(r)
        for r in self.pd_tree.get_children(): self.pd_tree.delete(r)
        now = datetime.now()
        current_md_item = None
        for md in self.dashas:
            av=("Current" if md["start"]<=now<=md["end"] else "Past" if md["end"]<now else "Future")
            tag="current" if av=="Current" else ("past" if av=="Past" else "")
            iid = self.md_tree.insert("","end",values=(
                GRAHA_DEVA.get(md["lord"],md["lord"]),
                md["start"].strftime("%d %b %Y"),md["end"].strftime("%d %b %Y"),
                f"{md['varsh']:.2f}",av,
            ),tags=(tag,))
            if av == "Current":
                current_md_item = iid
        if current_md_item:
            self.md_tree.selection_set(current_md_item)
            self.md_tree.see(current_md_item)
            self._on_md_sel(None)  # auto-populate Antardasha

    def _on_md_sel(self,_):
        sel=self.md_tree.selection()
        if not sel: return
        idx=self.md_tree.index(sel[0])
        if idx>=len(self.dashas): return
        md=self.dashas[idx]; now=datetime.now()
        self._current_selected_md = md
        for r in self.ad_tree.get_children(): self.ad_tree.delete(r)
        for r in self.pd_tree.get_children(): self.pd_tree.delete(r)
        current_ad_item = None
        for ad in md["antardasha"]:
            av=("Current" if ad["start"]<=now<=ad["end"] else "Past" if ad["end"]<now else "Future")
            tag="current" if av=="Current" else ("past" if av=="Past" else "")
            iid = self.ad_tree.insert("","end",values=(
                GRAHA_DEVA.get(md["lord"],md["lord"]),GRAHA_DEVA.get(ad["lord"],ad["lord"]),
                ad["start"].strftime("%d %b %Y"),ad["end"].strftime("%d %b %Y"),
                (ad["end"]-ad["start"]).days,av,
            ),tags=(tag,))
            if av == "Current":
                current_ad_item = iid
        if current_ad_item:
            self.ad_tree.selection_set(current_ad_item)
            self.ad_tree.see(current_ad_item)
            self._on_ad_sel(None)

    def _on_ad_sel(self,_):
        sel = self.ad_tree.selection()
        if not sel or not self._current_selected_md: return
        idx = self.ad_tree.index(sel[0])
        md = self._current_selected_md
        if idx >= len(md["antardasha"]): return
        ad = md["antardasha"][idx]
        now = datetime.now()
        for r in self.pd_tree.get_children(): self.pd_tree.delete(r)
        try:
            pds = compute_pratyantardasha_for_ad(ad)
        except Exception:
            return
        for pd_item in pds:
            av=("Current" if pd_item["start"]<=now<=pd_item["end"]
                else "Past" if pd_item["end"]<now else "Future")
            tag="current" if av=="Current" else ("past" if av=="Past" else "")
            self.pd_tree.insert("","end",values=(
                GRAHA_DEVA.get(pd_item["lord"],pd_item["lord"]),
                pd_item["start"].strftime("%d %b %Y"),pd_item["end"].strftime("%d %b %Y"),
                (pd_item["end"]-pd_item["start"]).days,av,
            ),tags=(tag,))

    def _upd_yoga(self):
        def _render(txt,items,is_yoga):
            txt.configure(state="normal"); txt.delete("1.0","end")
            if not items:
                txt.insert("end","  None detected.\n","system")
                txt.configure(state="disabled"); return
            for item in items:
                txt.insert("end","  ","card_sep")
                txt.insert("end",item["naam"],"card_name")
                txt.insert("end","  ","card_sep")
                bala = item.get("bala","") if is_yoga else item.get("sthiti","")
                tag=("card_good" if bala in ("Uttam","Pratham","Khandit")
                     else "card_bad" if bala in ("Sakriya",) else "card_neu")
                bd=BALA_DEVA.get(bala,bala) if is_yoga else bala
                txt.insert("end",f"[{bd}]",tag)
                gs="  "+"  ".join(GRAHA_DEVA.get(g,g) for g in item.get("graha",[]))
                txt.insert("end",gs,"card_graha")
                txt.insert("end","\n","card_sep")
                txt.insert("end",f"  {item.get('vivaran','')}\n\n","card_desc")
            txt.configure(state="disabled")
        _render(self.yoga_text, self.yogas,  True)
        _render(self.dosha_text,self.doshas, False)

    def _upd_shadbala(self):
        for r in self.sb_tree.get_children(): self.sb_tree.delete(r)
        lr=self.grahas.get("Lagna",{}).get("rashi",0)
        for g in ["Surya","Chandra","Mangal","Budha","Guru","Shukra","Shani"]:
            sb=shadbala(g,self.grahas,lr)
            st_d=AVASTHA_DEVA.get(sb["sthiti_key"],sb["sthiti_key"])
            tag=("poorna" if sb["sthiti_key"]=="Uchcha"
                 else "durbal" if sb["sthiti_key"]=="Neecha" else "")
            self.sb_tree.insert("","end",values=(
                GRAHA_DEVA.get(g,g),sb["uchcha_bala"],sb["saptavarga"],
                sb["kendradi"],sb["cheshta"],sb["naisargika"],
                st_d,sb["bhava_method"],
            ),tags=(tag,))
        self.sb_tree.tag_configure("poorna",background="#DCFCE7")
        self.sb_tree.tag_configure("durbal",background="#FEE2E2")

    def _upd_chalit(self):
        """Populate Bhava Chalit comparison table and cusp table."""
        for r in self.chalit_tree.get_children(): self.chalit_tree.delete(r)
        for r in self.cusp_tree.get_children():   self.cusp_tree.delete(r)
        if not self.grahas: return

        cusps = self.grahas.get("_meta",{}).get("sidereal_cusps",[])

        for gn in ALL_GRAHAS+["Lagna"]:
            pd = self.grahas.get(gn,{})
            if not pd: continue
            lon = pd.get("longitude")
            if lon is None: continue
            rashi_bhava = pd.get("bhava","?")
            chalit_bhava= pd.get("bhava","?")  # already sripathi when pyswisseph active
            bm = pd.get("bhava_method","whole_sign")
            shifted = rashi_bhava != chalit_bhava and bm == "sripathi"
            tag = "shifted" if shifted else "same"
            d_  = int(lon%30); m_ = int((lon%30-d_)*60)
            self.chalit_tree.insert("","end",values=(
                GRAHA_DEVA.get(gn,gn),
                f"{lon:.3f}°",
                RASHI_DEVA[pd.get("rashi",0)],
                rashi_bhava,
                chalit_bhava,
                "YES ⚡" if shifted else "—",
            ),tags=(tag,))

        # Cusp table
        for idx,cusp_deg in enumerate(cusps):
            ri = int(cusp_deg/30) % 12
            ansh = cusp_deg % 30
            self.cusp_tree.insert("","end",values=(
                f"Bhava {idx+1}",
                f"{cusp_deg:.4f}°",
                RASHI_DEVA[ri],
                f"{ansh:.2f}°",
            ),tags=(f"r{idx%12}",))

    def _upd_ashtak(self):
        """Populate Ashtakavarga grid — initial load with Sarva."""
        if not self.grahas: return
        self._show_ashtak()

    def _show_ashtak(self):
        for r in self.av_tree.get_children(): self.av_tree.delete(r)
        if not self.grahas: return
        sel = self.ashtak_var.get()
        if sel.startswith("Sarva"):
            scores = sarvashtakavarga(self.grahas)
            row = [GRAHA_DEVA.get("Sarva","Sarva")] + scores
            tag = "sarva"
            self.av_tree.insert("","end",values=tuple(row),tags=(tag,))
        else:
            # Find matching planet key
            planet_key = next((p for p in ASHTAK_PLANETS if GRAHA_DEVA.get(p,p)==sel or p==sel), None)
            if planet_key is None: return
            scores = ashtakavarga(planet_key, self.grahas)
            for i,sc in enumerate(scores):
                tag = "strong" if sc>=4 else ("weak" if sc<4 else "mid")
            row = [GRAHA_DEVA.get(planet_key,planet_key)] + scores
            # Color each cell individually via tag on the whole row
            row_tag = "strong" if sum(scores)/12>=4 else "mid"
            self.av_tree.insert("","end",values=tuple(row),tags=(row_tag,))
            # Also insert individual sign strength annotations (separate visual rows)
        # Refresh to add all planets for "Sarva" comparison
        if sel.startswith("Sarva"):
            for planet in ASHTAK_PLANETS:
                sc = ashtakavarga(planet, self.grahas)
                tag = "strong" if sum(sc)/12>=4 else "mid"
                self.av_tree.insert("","end",
                    values=tuple([GRAHA_DEVA.get(planet,planet)]+sc),tags=(tag,))

    # ── Panchanga ──────────────────────────────────────────────────────────────
    def _upd_panchanga(self):
        """Populate the Panchanga tab with the 5 Vedic time limbs."""
        for r in self.panch_tree.get_children(): self.panch_tree.delete(r)
        pd = getattr(self, "panchanga_data", {})
        if not pd:
            self.panch_desc_var.set("Generate or load a chart to view the 5 Vedic time limbs.")
            return

        t  = pd.get("tithi",    {})
        v  = pd.get("vara",     {})
        nk = pd.get("nakshatra",{})
        yg = pd.get("yoga",     {})
        ka = pd.get("karana",   {})

        def _tag(nature):
            n = str(nature).lower()
            if any(x in n for x in ("auspicious","shubha","good","uttam","bhadra","mala")):
                return "auspicious"
            if any(x in n for x in ("inauspicious","ashubha","bad","vishti","rik")):
                return "inauspicious"
            return "neutral"

        rows = [
            ("Tithi",
             f"{t.get('name','')}  (#{t.get('index','')})",
             f"{t.get('paksha','')}  Paksha · T-{t.get('tithi_in_paksha','')}",
             "Chandra",
             f"Elapsed: {t.get('elapsed_pct',0):.1f}%",
             _tag(t.get("paksha",""))),
            ("Vara",
             v.get("name",""),
             v.get("english",""),
             v.get("ruler",""),
             "—",
             "neutral"),
            ("Nakshatra",
             f"{nk.get('name','')}  (#{nk.get('index','')})",
             f"Pada {nk.get('pada','')}",
             nk.get("lord",""),
             f"Elapsed: {nk.get('elapsed_pct',0):.1f}%",
             "neutral"),
            ("Nitya Yoga",
             f"{yg.get('name','')}  (#{yg.get('index','')})",
             yg.get("nature",""),
             yg.get("lord",""),
             f"Elapsed: {yg.get('elapsed_pct',0):.1f}%",
             _tag(yg.get("nature",""))),
            ("Karana",
             f"{ka.get('name','')}  (#{ka.get('index','')})",
             ka.get("type",""),
             "—",
             f"Vishti/Bhadra: {'YES ⚡' if ka.get('is_vishti_bhadra') else 'No'}",
             "inauspicious" if ka.get("is_vishti_bhadra") else "neutral"),
        ]
        for row in rows:
            self.panch_tree.insert("", "end",
                values=(row[0], row[1], row[2], GRAHA_DEVA.get(row[3], row[3]), row[4]),
                tags=(row[5],))

        # Summary description
        tithi_name = t.get("name","?")
        nak_name   = nk.get("name","?")
        vara_name  = v.get("english","?")
        vishti_warn = "  ⚡ Vishti Karana — avoid new beginnings." if ka.get("is_vishti_bhadra") else ""
        self.panch_desc_var.set(
            f"Birth on {vara_name}  ·  Tithi: {tithi_name} ({t.get('paksha','')})  "
            f"·  Nakshatra: {nak_name} Pada-{nk.get('pada','')}  "
            f"·  Yoga: {yg.get('name','')} ({yg.get('nature','')}).{vishti_warn}")

    # ── Remedies & Gemstones ───────────────────────────────────────────────────
    def _upd_remedies(self):
        """Populate Remedies & Gems tab with gemstone prescription data."""
        for r in self.gem_tree.get_children(): self.gem_tree.delete(r)
        lr = self.grahas.get("Lagna", {}).get("rashi", 0)
        from core.constants import RASHI
        lagna_name = RASHI[lr] if self.grahas else "—"
        self.lagna_benefic_var.set(
            f"Lagna: {RASHI_DEVA[lr]}  ({lagna_name})  —  "
            "Items in green are prescribed benefic gems; red are contraindicated malefics.")
        gems = getattr(self, "gemstones_data", [])
        for gd in gems:
            if not gd: continue
            graha   = gd.get("graha", "")
            if gd.get("prescribed"):
                rx   = "PRESCRIBED ✓"
                gem  = gd.get("gemstone","")
                wt   = f"{gd.get('recommended_carats',0):.2f} ct"
                metal= gd.get("metal","")
                fing = gd.get("finger","")
                day  = gd.get("wearing_day_time","")
                tag  = "prescribed"
            else:
                rx   = "Contraindicated ✗"
                gem  = gd.get("warning","")[:60]
                wt   = "—"
                metal= "—"
                fing = "—"
                day  = gd.get("safe_remedy",{}).get("daana_day","")
                tag  = "contraindicated"
            self.gem_tree.insert("", "end", values=(
                GRAHA_DEVA.get(graha, graha), rx, gem, wt, metal, fing, day
            ), tags=(tag,))

    def _on_gem_sel(self, _):
        """Show full prescription detail when a gem row is selected."""
        sel = self.gem_tree.selection()
        self.gem_detail_text.configure(state="normal")
        self.gem_detail_text.delete("1.0", "end")
        if not sel:
            self.gem_detail_text.configure(state="disabled"); return
        idx = self.gem_tree.index(sel[0])
        gems = getattr(self, "gemstones_data", [])
        if idx >= len(gems) or not gems[idx]:
            self.gem_detail_text.configure(state="disabled"); return
        gd = gems[idx]
        graha = gd.get("graha","")
        self.gem_detail_text.insert("end", f"Planet: {GRAHA_DEVA.get(graha,graha)}\n\n",)
        if gd.get("prescribed"):
            self.gem_detail_text.insert("end",
                f"✓ PRESCRIBED\n"
                f"   Primary Gem    : {gd.get('gemstone','')}\n"
                f"   Sanskrit Name  : {gd.get('sanskrit_name','')}\n"
                f"   Substitutes    : {', '.join(gd.get('substitutes',[]))}\n"
                f"   Metal          : {gd.get('metal','')}\n"
                f"   Finger         : {gd.get('finger','')}\n"
                f"   Wearing Day/Time: {gd.get('wearing_day_time','')}\n"
                f"   Weight         : {gd.get('recommended_carats',0):.2f} carats "
                f"/ {gd.get('recommended_ratti',0):.2f} ratti\n\n"
                f"Consecration Mantra:\n   {gd.get('consecration_mantra','')}\n")
        else:
            sr = gd.get("safe_remedy",{})
            self.gem_detail_text.insert("end",
                f"✗ CONTRAINDICATED\n\n"
                f"{gd.get('warning','')}\n\n"
                f"Safe Alternatives:\n"
                f"   Mantra   : {sr.get('mantra','')}\n"
                f"   Daana Day: {sr.get('daana_day','')}\n"
                f"   Guidance : {sr.get('recommended_action','')}\n")
        self.gem_detail_text.configure(state="disabled")

    # ── Report Export ──────────────────────────────────────────────────────────
    def _export_report(self):
        """Export a comprehensive plain-text Jyotish dossier."""
        if not self.grahas:
            messagebox.showinfo("No Chart", "Generate or load a chart first."); return
        naam = self.name_var.get().strip().replace(" ","_") or "chart"
        fp = filedialog.asksaveasfilename(
            title="Export Jyotish Report",
            defaultextension=".txt",
            initialfile=f"{naam}_report.txt",
            filetypes=[("Text Report","*.txt"),("All","*")])
        if not fp: return
        try:
            lines = []
            lines.append("=" * 72)
            lines.append("  VEDIC JYOTISH DOSSIER — Comprehensive Natal Analysis")
            lines.append("=" * 72)
            lines.append(f"  Native    : {self.name_var.get()}")
            lines.append(f"  Birth     : {self.janam_vivaran}")
            lines.append(f"  Generated : {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            lines.append("")

            # 1. Planetary positions
            lines.append("─" * 72)
            lines.append("1. PLANETARY POSITIONS")
            lines.append("─" * 72)
            lr = self.grahas.get("Lagna",{}).get("rashi",0)
            lines.append(f"  Lagna (Ascendant): {RASHI_DEVA[lr]}\n")
            from core.constants import RASHI
            for gn in ALL_GRAHAS + ["Lagna"]:
                pd = self.grahas.get(gn,{})
                if not pd: continue
                lon = pd.get("longitude",0)
                d = int(lon%30); m = int((lon%30-d)*60)
                vk = " (R)" if pd.get("retro") else ""
                st_k = sthiti(gn,pd.get("rashi",0))
                st_d = AVASTHA_DEVA.get(st_k,st_k)
                lines.append(
                    f"  {GRAHA_DEVA.get(gn,gn):<14} "
                    f"{RASHI_DEVA[pd.get('rashi',0)]:<12} "
                    f"Bhava {pd.get('bhava','?'):<4} "
                    f"{d:2d}°{m:02d}' {vk:<5} "
                    f"[{st_d}]")

            # 2. Panchanga
            lines.append("\n" + "─"*72)
            lines.append("2. PANCHANGA — FIVE LIMBS OF VEDIC TIME")
            lines.append("─"*72)
            pd_raw = getattr(self,"panchanga_data",{})
            if pd_raw:
                t  = pd_raw.get("tithi",{})
                v  = pd_raw.get("vara",{})
                nk = pd_raw.get("nakshatra",{})
                yg = pd_raw.get("yoga",{})
                ka = pd_raw.get("karana",{})
                lines.append(f"  Tithi    : {t.get('name','')} (#{t.get('index','')})  "
                              f"— {t.get('paksha','')} Paksha, day {t.get('tithi_in_paksha','')}  "
                              f"[{t.get('elapsed_pct',0):.1f}% elapsed]")
                lines.append(f"  Vara     : {v.get('name','')} ({v.get('english','')})  "
                              f"— Ruler: {v.get('ruler','')}")
                lines.append(f"  Nakshatra: {nk.get('name','')} (#{nk.get('index','')})  "
                              f"Pada {nk.get('pada','')}  — Lord: {nk.get('lord','')}  "
                              f"[{nk.get('elapsed_pct',0):.1f}% elapsed]")
                lines.append(f"  Yoga     : {yg.get('name','')} ({yg.get('nature','')})  "
                              f"— Lord: {yg.get('lord','')}")
                lines.append(f"  Karana   : {ka.get('name','')} ({ka.get('type','')})  "
                              f"Vishti/Bhadra: {'Yes ⚡' if ka.get('is_vishti_bhadra') else 'No'}")
            else:
                lines.append("  (Not available — load or generate full chart)")

            # 3. Yogas and Doshas
            lines.append("\n" + "─"*72)
            lines.append("3. YOGAS & DOSHAS")
            lines.append("─"*72)
            if self.yogas:
                lines.append("  YOGAS:")
                for yog in self.yogas:
                    bala = BALA_DEVA.get(yog.get("bala",""),yog.get("bala",""))
                    lines.append(f"   • {yog.get('naam',''):<30} [{bala}]  — {yog.get('vivaran','')}")
            else:
                lines.append("  No significant Yogas detected.")
            lines.append("")
            if self.doshas:
                lines.append("  DOSHAS:")
                for dos in self.doshas:
                    lines.append(f"   • {dos.get('naam',''):<30} [{dos.get('sthiti','')}]  — {dos.get('vivaran','')}")
            else:
                lines.append("  No major Doshas detected.")

            # 4. Vimshottari Dasha
            lines.append("\n" + "─"*72)
            lines.append("4. VIMSHOTTARI DASHA PERIODS")
            lines.append("─"*72)
            now = datetime.now()
            for md in self.dashas:
                av = ("CURRENT" if md["start"]<=now<=md["end"] else
                      "Past"   if md["end"]<now else "Future")
                prefix = "▶ " if av=="CURRENT" else "  "
                lines.append(
                    f"{prefix}Mahadasha: {GRAHA_DEVA.get(md['lord'],md['lord']):<14} "
                    f"{md['start'].strftime('%d %b %Y')} – {md['end'].strftime('%d %b %Y')}  [{av}]")
                if av == "CURRENT":
                    for ad in md.get("antardasha",[]):
                        av2 = ("CURRENT" if ad["start"]<=now<=ad["end"] else
                               "Past"   if ad["end"]<now else "Future")
                        p2 = "  ▷ " if av2=="CURRENT" else "    "
                        lines.append(
                            f"{p2}Antardasha: {GRAHA_DEVA.get(ad['lord'],ad['lord']):<12} "
                            f"{ad['start'].strftime('%d %b %Y')} – {ad['end'].strftime('%d %b %Y')}  [{av2}]")

            # 5. Gemstone Prescriptions
            lines.append("\n" + "─"*72)
            lines.append("5. GEMSTONE & REMEDY PRESCRIPTIONS (BPHS Safety Filter)")
            lines.append("─"*72)
            gems = getattr(self,"gemstones_data",[])
            for gd in gems:
                if not gd: continue
                graha = gd.get("graha","")
                if gd.get("prescribed"):
                    lines.append(
                        f"  ✓ {GRAHA_DEVA.get(graha,graha):<12} → {gd.get('gemstone',''):<18} "
                        f"{gd.get('recommended_carats',0):.2f} ct  ({gd.get('metal','')} / {gd.get('finger','')})")
                    lines.append(f"      Mantra: {gd.get('consecration_mantra','')}")
                else:
                    sr = gd.get("safe_remedy",{})
                    lines.append(f"  ✗ {GRAHA_DEVA.get(graha,graha):<12} — CONTRAINDICATED. "
                                  f"{sr.get('recommended_action','')}")

            lines.append("\n" + "=" * 72)
            lines.append("  End of Jyotish Dossier — Generated by Vedic Astrology Calculator")
            lines.append("=" * 72)

            with open(fp, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
            self.sb.set("msg", f"Report exported: {os.path.basename(fp)}")
            messagebox.showinfo("Report Saved", f"Comprehensive Jyotish report saved to:\n{fp}")
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            messagebox.showerror("Export Failed", f"Error: {e}\n\n{err[:400]}")

    # ── Varga ──────────────────────────────────────────────────────────────────
    def _show_varga(self):
        if not self.grahas: messagebox.showinfo("No Chart","Generate a chart first."); return
        sel=self.varga_var.get(); n=int(sel.split("-")[1].split(" ")[0])
        for r in self.v_tree.get_children(): self.v_tree.delete(r)
        vg={}
        for gn,pd in self.grahas.items():
            if gn.startswith("_"): continue
            lon=pd.get("longitude")
            if lon is None: continue
            vs=calc_varga(lon,n); vd=lon%30*n%30
            vg[gn]={**pd,"longitude":vs*30+vd,"rashi":vs,"rashi_naam":RASHI[vs],"rashi_ansh":vd}
        var=vg.get("Lagna",{}).get("rashi",0)
        for gn,pd in vg.items():
            if gn in ("Lagna","_meta"): continue
            pd["bhava"]=(pd["rashi"]-var)%12+1
        self.varga_chart.set_data(vg,sel)
        for gn in ALL_GRAHAS+["Lagna"]:
            pd1=self.grahas.get(gn,{}); pd2=vg.get(gn,{})
            if not pd1 or not pd2: continue
            st_k=sthiti(gn,pd2.get("rashi",0)); st_d=AVASTHA_DEVA.get(st_k,st_k)
            tag="uchcha" if st_k=="Uchcha" else ("neecha" if st_k=="Neecha" else "")
            self.v_tree.insert("","end",values=(
                GRAHA_DEVA.get(gn,gn),RASHI_DEVA[pd1.get("rashi",0)],
                RASHI_DEVA[pd2.get("rashi",0)],st_d,
            ),tags=(tag,))
        dk=sel.split(" ")[0]
        self.varga_desc_var.set(f"{sel}  —  {VARGA_DESC.get(dk,'')}")

    # ── Transits ───────────────────────────────────────────────────────────────
    def _refresh_transits(self):
        def run():
            try:
                ay_k = self.ayanamsa_var.get()
                self.transit_grahas = compute_transits(ay_k)
                self.root.after(0, self._upd_transit_display)
            except Exception as e:
                self.root.after(0, lambda: self.sb.set("msg",f"Transit error: {e}"))
        threading.Thread(target=run,daemon=True).start()

    def _upd_transit_display(self):
        from datetime import timezone
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d  %H:%M  UTC")
        self.transit_date_var.set(now_str)

        # Update chart overlay
        self.transit_chart.set_data(
            self.grahas if self.grahas else {},
            "Natal + Transits",
            transit_grahas=self.transit_grahas)

        # Update table
        for r in self.transit_tree.get_children(): self.transit_tree.delete(r)
        natal_lr = self.grahas.get("Lagna",{}).get("rashi",0)
        trans_lr = self.transit_grahas.get("Lagna",{}).get("rashi",0) or natal_lr

        for gn in ALL_GRAHAS:
            tpd = self.transit_grahas.get(gn,{})
            npd = self.grahas.get(gn,{}) if self.grahas else {}
            if not tpd: continue
            t_rashi = tpd.get("rashi",0)
            t_bhava = (t_rashi - natal_lr)%12+1
            n_rashi = npd.get("rashi",0) if npd else t_rashi
            n_bhava = npd.get("bhava","?") if npd else "?"
            # Flag notable transits (Shani/Guru over natal Moon/Lagna)
            notable = False
            if gn in ("Shani","Guru","Rahu"):
                moon_bhava = self.grahas.get("Chandra",{}).get("bhava",0) if self.grahas else 0
                if t_bhava in (moon_bhava, 1, 4, 7, 8, 12):
                    notable = True
            note = ""
            if gn=="Shani" and t_bhava==1: note="Sade Sati begin?"
            elif gn=="Guru" and t_bhava in (1,5,9): note="Guru Trikona"
            elif gn=="Rahu" and t_bhava in (1,3,6): note="Rahu transit"
            tag = "notable" if notable or note else "normal"
            self.transit_tree.insert("","end",values=(
                GRAHA_DEVA.get(gn,gn),
                RASHI_DEVA[t_rashi], t_bhava,
                RASHI_DEVA[n_rashi], n_bhava,
                note or "—",
            ),tags=(tag,))

    # ══════════════════════════════════════════════════════════════════════
    #  AI GENERATION  (bold streaming)
    # ══════════════════════════════════════════════════════════════════════
    def _flush_render_buf(self):
        text = self._render_buf; parts=[]; last=0
        for m in re.finditer(r'\*\*(.+?)\*\*',text,re.DOTALL):
            parts.append(("answer",text[last:m.start()]))
            parts.append(("answer_bold",m.group(1)))
            last=m.end()
        remaining=text[last:]
        op=remaining.rfind("**")
        if op!=-1:
            parts.append(("answer",remaining[:op]))
            self._render_buf=remaining[op:]
        else:
            parts.append(("answer",remaining))
            self._render_buf=""
        self.chat.configure(state="normal")
        for tag,content in parts:
            if content: self.chat.insert("end",content,tag)
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def _flush_remaining_buf(self):
        if self._render_buf:
            self.chat.configure(state="normal")
            self.chat.insert("end",self._render_buf,"answer")
            self.chat.see("end")
            self.chat.configure(state="disabled")
            self._render_buf=""

    def _run_generation(self,is_full,question=""):
        if not self.grahas: self._chat_add("system","Generate a chart first.\n\n"); return
        if not OllamaEngine.ping(): self._chat_add("error","Ollama is not running.\n\n"); return
        model  = self.ollama_model_var.get().strip() or "qwen2.5:7b"
        sys_p  = PredictionEngine.system_prompt()
        if is_full:
            user_p = PredictionEngine.user_prompt_full(self.chart_json_str)
            domain = "FULL_ANALYSIS"
        else:
            user_p, domain = self.conv_manager.build_qa_prompt(self.chart_json_str, question)

        self._cancel_event.clear(); self._has_cleared_placeholder=False; self._render_buf=""
        self._current_gen_text = ""
        self.root.after(0,lambda: self._set_streaming(True))
        self._chat_add("system","[ Generating... ]\n")

        def _token(t):
            if not self._has_cleared_placeholder:
                self._has_cleared_placeholder=True
                self.root.after(0,self._remove_thinking_marker)
            self._render_buf+=t
            self._current_gen_text+=t
            self.root.after(0,self._flush_render_buf)

        def _done(err):
            self.root.after(0,self._flush_remaining_buf)
            self.root.after(0,lambda: self._set_streaming(False))
            if err:
                self.root.after(0,lambda: self._chat_add("error",f"\n[ Error: {err} ]\n\n"))
            else:
                self.root.after(0,lambda: self._chat_add("system","\n\n"))
                if not is_full and question and self._current_gen_text:
                    self.conv_manager.record_turn(question, self._current_gen_text, domain)

        OllamaEngine.generate_stream(
            model=model,system_prompt=sys_p,user_prompt=user_p,
            token_cb=_token,done_cb=_done,cancel_event=self._cancel_event)

    def _remove_thinking_marker(self):
        try:
            self.chat.configure(state="normal")
            content=self.chat.get("1.0","end")
            idx=content.rfind("[ Generating... ]\n")
            if idx>=0:
                self.chat.delete(f"1.0+{idx}c",f"1.0+{idx+len('[ Generating... ]')+1}c")
            self.chat.configure(state="disabled")
        except Exception: pass

    def _auto_analyse(self):
        if self._streaming: self._chat_add("system","Stop generation first.\n\n"); return
        self._chat_add("header","=== COMPREHENSIVE JYOTISH READING ===\n")
        threading.Thread(target=self._run_generation,args=(True,),daemon=True).start()

    def _send(self):
        q=self.chat_in.get("1.0","end-1c").strip()
        if not q: return
        if self._streaming: self._chat_add("system","Stop generation first.\n\n"); return
        self.chat_in.delete("1.0","end")
        self._chat_add("question",f"You: {q}\n")
        threading.Thread(target=self._run_generation,args=(False,q),daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════
    #  SAVE / LOAD
    # ══════════════════════════════════════════════════════════════════════
    def _save_kundali(self):
        if not self.grahas: messagebox.showinfo("No Chart","Generate first."); return
        naam=self.name_var.get().strip().replace(" ","_") or "chart"
        fp=filedialog.asksaveasfilename(title="Save Chart",defaultextension=".jyotish",
            initialfile=f"{naam}.jyotish",
            filetypes=[("Jyotish Chart","*.jyotish"),("JSON","*.json"),("All","*")])
        if not fp: return
        try:
            d_ser=[{"lord":md["lord"],"start":ser_dt(md["start"]),"end":ser_dt(md["end"]),
                    "varsh":md["varsh"],
                    "antardasha":[{"lord":a["lord"],"start":ser_dt(a["start"]),
                                   "end":ser_dt(a["end"]),"varsh":a["varsh"]}
                                  for a in md["antardasha"]]} for md in self.dashas]
            data={"version":6,"janam_vivaran":self.janam_vivaran,
                  "birth_params":{"day":self.day_var.get(),"month":self.month_var.get(),
                      "year":self.year_var.get(),"hour":self.hour_var.get(),
                      "minute":self.min_var.get(),"tz":str(self.tz_val.get()),
                      "tz_label":self.tz_label_var.get(),
                      "lat":self.lat_var.get(),"lon":self.lon_var.get(),
                      "place":self.place_var.get(),"naam":self.name_var.get(),
                      "ayanamsa":self.ayanamsa_var.get(),"dasha_year":self.dasha_year_var.get()},
                  "grahas":{k:v for k,v in self.grahas.items() if not k.startswith("_")},
                  "yogas":self.yogas,"doshas":self.doshas,"dashas":d_ser,
                  "saved_at":datetime.now().strftime("%Y-%m-%d %H:%M")}
            with open(fp,"w",encoding="utf-8") as fh: json.dump(data,fh,indent=2,ensure_ascii=False)
            self.sb.set("msg",f"Saved: {os.path.basename(fp)}")
            messagebox.showinfo("Saved",f"Chart saved:\n{fp}")
        except Exception as e: messagebox.showerror("Save Failed",f"Error: {e}")

    def _load_kundali(self):
        fp=filedialog.askopenfilename(title="Load Chart",
            filetypes=[("Jyotish Chart","*.jyotish"),("JSON","*.json"),("All","*")])
        if not fp: return
        try:
            with open(fp,"r",encoding="utf-8") as fh: data=json.load(fh)
            bp=data.get("birth_params",{})
            if bp:
                self.day_var.set(bp.get("day","13")); self.month_var.set(bp.get("month","December"))
                self.year_var.set(bp.get("year","2006")); self.hour_var.set(bp.get("hour","16"))
                self.min_var.set(bp.get("minute","27"))
                tl=bp.get("tz_label",TZ_LABELS[0])
                if tl in TZ_VALUES: self.tz_label_var.set(tl); self.tz_val.set(TZ_VALUES[tl])
                else:
                    try: self.tz_val.set(float(bp.get("tz","5.5")))
                    except: pass
                self.lat_var.set(bp.get("lat","26.4499")); self.lon_var.set(bp.get("lon","80.3319"))
                self.place_var.set(bp.get("place","")); self.name_var.set(bp.get("naam",""))
                self.ayanamsa_var.set(bp.get("ayanamsa",AYANAMSA_OPTIONS[0]))
                dy=bp.get("dasha_year",DASHA_YEAR_NAMES[0])
                if dy in DASHA_YEAR_NAMES: self.dasha_year_var.set(dy)
            self.janam_vivaran=data.get("janam_vivaran","")
            self.grahas=data.get("grahas",{}); self.yogas=data.get("yogas",[])
            self.doshas=data.get("doshas",[]); parse_errors=[]; dashas_raw=data.get("dashas",[]); self.dashas=[]
            for md in dashas_raw:
                try:
                    ads=[{"lord":a["lord"],"start":deser_dt(a["start"]),"end":deser_dt(a["end"]),"varsh":a["varsh"]} for a in md.get("antardasha",[])]
                    self.dashas.append({"lord":md["lord"],"start":deser_dt(md["start"]),"end":deser_dt(md["end"]),"varsh":md["varsh"],"antardasha":ads})
                except ValueError as ve: parse_errors.append(str(ve))
            if parse_errors: messagebox.showwarning("Load Warning","Some Dasha dates failed:\n\n"+"\n".join(parse_errors[:3]))
            if self.grahas:
                self.grahas["_meta"]={"jd":0,"ay":0,"engine":"loaded","sidereal_cusps":[]}
                for gn,pd in self.grahas.items():
                    if gn.startswith("_"): continue
                    lon=pd.get("longitude",0); r=int(lon/30)
                    if "rashi" not in pd:      pd["rashi"]=r
                    if "rashi_naam" not in pd: pd["rashi_naam"]=RASHI[r]

                # Compute Panchanga and Gemstones for loaded chart
                lr = self.grahas.get("Lagna",{}).get("rashi",0)
                sl = self.grahas.get("Surya",{}).get("longitude",0)
                cl = self.grahas.get("Chandra",{}).get("longitude",0)
                try:
                    d_ = int(self.day_var.get()); mo_ = MONTHS.get(self.month_var.get(),1)
                    y_ = int(self.year_var.get()); h_ = int(self.hour_var.get()); mi_ = int(self.min_var.get())
                    dt_ = datetime(y_, mo_, d_, h_, mi_)
                except Exception:
                    dt_ = datetime.now()
                self.panchanga_data = panchanga(sl, cl, dt_)
                self.gemstones_data = [
                    gemstone_prescription(g, lr, body_weight_kg=60.0)
                    for g in ALL_GRAHAS[:7]
                ]

                # Clear AI cache and reset conversational context on load
                loaded_name = self.name_var.get().strip() or os.path.splitext(os.path.basename(fp))[0]
                chart_id = f"LOAD_{loaded_name}_{os.path.basename(fp)}"
                self.conv_manager.reset_for_new_chart(chart_id, loaded_name)
                OllamaEngine.clear_cache(self.ollama_model_var.get())
                self._clear_chat()
                self._chat_add("system",
                    f"=== CHART LOADED: {loaded_name} ===\n"
                    f"Source: {os.path.basename(fp)}\n"
                    f"Birth Details: {self.janam_vivaran}\n"
                    "[ AI Cache & KV state freshly cleared — zero cross-chart leakage ]\n\n")

            self.chart_text=PredictionEngine.chart_text_full(self.grahas,self.yogas,self.doshas,self.dashas,self.janam_vivaran)
            self.chart_json_str=PredictionEngine.chart_json(self.grahas,self.yogas,self.doshas,self.dashas)
            self.root.after(0,self._refresh_all)
            self.sb.set("msg",f"Loaded: {os.path.basename(fp)}")
        except Exception as e:
            import traceback; err=traceback.format_exc()
            messagebox.showerror("Load Failed",f"Error: {e}\n\n{err[:400]}")
