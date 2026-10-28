#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py  v6.0
=============
Entry point for Vedic Astrology Calculator v6.0.

Monorepo package layout
-----------------------
  main.py            — application launcher
  core/              — constants, astro_engine (Swiss Ephemeris), vedic_engine
  ai/                — ollama_engine, prediction_engine
  ui/                — app (JyotishApp), ui_widgets (XP Luna components)
  reference/         — audits, implementation plan, architecture docs
  tests/             — unit & regression tests
"""

import sys
import os

# ── Ensure package root is on the path so sibling imports work ─────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from ui.app import JyotishApp


def main():
    root = tk.Tk()
    root.title("Vedic Astrology Calculator")

    # Centre window
    root.update_idletasks()
    sw = root.winfo_screenwidth(); sh = root.winfo_screenheight()
    w, h = 1260, 860
    root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # Windows: disable auto-scaling so Luna pixel grid stays crisp
    try:
        from ctypes import windll; windll.shcore.SetProcessDpiAwareness(1)
    except Exception: pass

    app = JyotishApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
