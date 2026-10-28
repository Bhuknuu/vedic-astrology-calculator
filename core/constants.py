# -*- coding: utf-8 -*-
"""
constants.py
============
All static data: Sanskrit lookup tables, UI palette, timezone catalogue,
Ollama/backend configuration.  No local imports — safe to import everywhere.
"""

# ══════════════════════════════════════════════════════════════════════════════
#  ASTRONOMICAL CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

# FIX: Use Tropical Solar Year, NOT Julian 365.25.
# Over a 60-year chart, 365.25 vs 365.24219 causes ~15-20 day Dasha drift.
TROPICAL_YEAR = 365.24219   # days per mean tropical solar year

RASHI = [
    "Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya",
    "Tula","Vrishchika","Dhanu","Makara","Kumbha","Meena",
]
RASHI_DEVA = [
    "\u092e\u0947\u0937","\u0935\u0943\u0937\u092d","\u092e\u093f\u0925\u0941\u0928",
    "\u0915\u0930\u094d\u0915","\u0938\u093f\u0902\u0939","\u0915\u0928\u094d\u092f\u093e",
    "\u0924\u0941\u0932\u093e","\u0935\u0943\u0936\u094d\u091a\u093f\u0915",
    "\u0927\u0928\u0941","\u092e\u0915\u0930","\u0915\u0941\u0902\u092d","\u092e\u0940\u0928",
]
RASHI_ABBR = [
    "\u092e\u0947\u0937","\u0935\u0943\u0937","\u092e\u093f\u0925\u0941",
    "\u0915\u0930\u094d\u0915","\u0938\u093f\u0902\u0939","\u0915\u0928\u094d\u092f\u093e",
    "\u0924\u0941\u0932\u093e","\u0935\u0943\u0936\u094d\u091a\u093f",
    "\u0927\u0928\u0941","\u092e\u0915\u0930","\u0915\u0941\u0902\u092d","\u092e\u0940\u0928",
]

NAKSHATRA = [
    "\u0905\u0936\u094d\u0935\u093f\u0928\u0940","\u092d\u0930\u0923\u0940",
    "\u0915\u0943\u0924\u094d\u0924\u093f\u0915\u093e","\u0930\u094b\u0939\u093f\u0923\u0940",
    "\u092e\u0943\u0917\u0936\u093f\u0930\u093e","\u0906\u0930\u094d\u0926\u094d\u0930\u093e",
    "\u092a\u0941\u0928\u0930\u094d\u0935\u0938\u0941","\u092a\u0941\u0937\u094d\u092f",
    "\u0906\u0936\u094d\u0932\u0947\u0937\u093e","\u092e\u0918\u093e",
    "\u092a\u0942\u0930\u094d\u0935 \u092b\u093e\u0932\u094d\u0917\u0941\u0928\u0940",
    "\u0909\u0924\u094d\u0924\u0930 \u092b\u093e\u0932\u094d\u0917\u0941\u0928\u0940",
    "\u0939\u0938\u094d\u0924","\u091a\u093f\u0924\u094d\u0930\u093e",
    "\u0938\u094d\u0935\u093e\u0924\u0940","\u0935\u093f\u0936\u093e\u0916\u093e",
    "\u0905\u0928\u0941\u0930\u093e\u0927\u093e","\u091c\u094d\u092f\u0947\u0937\u094d\u0920\u093e",
    "\u092e\u0942\u0932","\u092a\u0942\u0930\u094d\u0935\u093e\u0937\u093e\u0922\u093c",
    "\u0909\u0924\u094d\u0924\u0930\u093e\u0937\u093e\u0922\u093c",
    "\u0936\u094d\u0930\u0935\u0923","\u0927\u0928\u093f\u0937\u094d\u0920\u093e",
    "\u0936\u0924\u092d\u093f\u0937\u093e",
    "\u092a\u0942\u0930\u094d\u0935 \u092d\u093e\u0926\u094d\u0930\u092a\u0926",
    "\u0909\u0924\u094d\u0924\u0930 \u092d\u093e\u0926\u094d\u0930\u092a\u0926",
    "\u0930\u0947\u0935\u0924\u0940",
]

NAK_LORDS = ["Ketu","Shukra","Surya","Chandra","Mangal",
             "Rahu","Guru","Shani","Budha"] * 3

GRAHA_DEVA = {
    "Surya":"\u0938\u0942\u0930\u094d\u092f",
    "Chandra":"\u091a\u0928\u094d\u0926\u094d\u0930",
    "Mangal":"\u092e\u0902\u0917\u0932",
    "Budha":"\u092c\u0941\u0927",
    "Guru":"\u0917\u0941\u0930\u0941",
    "Shukra":"\u0936\u0941\u0915\u094d\u0930",
    "Shani":"\u0936\u0928\u093f",
    "Rahu":"\u0930\u093e\u0939\u0941",
    "Ketu":"\u0915\u0947\u0924\u0941",
    "Lagna":"\u0932\u0917\u094d\u0928",
}
GRAHA_SYMBOLS = {
    "Surya":"\u0938\u0942","Chandra":"\u091a\u0902","Mangal":"\u092e\u0902",
    "Budha":"\u092c\u0941","Guru":"\u0917\u0941","Shukra":"\u0936\u0941",
    "Shani":"\u0936","Rahu":"\u0930\u093e","Ketu":"\u0915\u0947",
    "Lagna":"\u0932",
}
AVASTHA_DEVA = {
    "Uchcha":"\u0909\u091a\u094d\u091a",
    "Neecha":"\u0928\u0940\u091a",
    "Swakshetra":"\u0938\u094d\u0935\u0915\u094d\u0937\u0947\u0924\u094d\u0930",
    "Moolatrikona":"\u092e\u0942\u0932\u0924\u094d\u0930\u093f\u0915\u094b\u0923",
    "Mitra":"\u092e\u093f\u0924\u094d\u0930",
    "Shatru":"\u0936\u0924\u094d\u0930\u0941",
    "Sama":"\u0938\u092e",
    "--":"--",
}
BALA_DEVA = {
    "Uttam":"\u0909\u0924\u094d\u0924\u092e",
    "Pratham":"\u092a\u094d\u0930\u0925\u092e",
    "Shubha":"\u0936\u0941\u092d",
    "Madhyam":"\u092e\u0927\u094d\u092f\u092e",
    "Vishesh":"\u0935\u093f\u0936\u0947\u0937",
}

DASHA_VARSH = {
    "Ketu":7,"Shukra":20,"Surya":6,"Chandra":10,
    "Mangal":7,"Rahu":18,"Guru":16,"Shani":19,"Budha":17,
}
DASHA_KRAM = ["Ketu","Shukra","Surya","Chandra","Mangal","Rahu","Guru","Shani","Budha"]

RASHI_SWAMI = [
    "Mangal","Shukra","Budha","Chandra","Surya","Budha",
    "Shukra","Mangal","Guru","Shani","Shani","Guru",
]

# FIX: Nodes now have proper exaltation degrees (Phaladeepika school).
# Rahu exalted Taurus ~15 deg = absolute 45 deg
# Ketu exalted Scorpio ~15 deg = absolute 225 deg
UCHCHA_DEG = {
    "Surya":10,"Chandra":33,"Mangal":298,"Budha":165,
    "Guru":95,"Shukra":357,"Shani":200,"Rahu":45,"Ketu":225,
}
NEECHA_DEG = {k: (v + 180) % 360 for k, v in UCHCHA_DEG.items()}

SWAKSHETRA = {
    "Surya":[4],"Chandra":[3],"Mangal":[0,7],"Budha":[2,5],
    "Guru":[8,11],"Shukra":[1,6],"Shani":[9,10],
}
MOOLTRIKONA = {
    "Surya":4,"Chandra":1,"Mangal":0,"Budha":5,"Guru":8,"Shukra":6,"Shani":10,
}
MITRA = {
    "Surya":["Chandra","Mangal","Guru"],
    "Chandra":["Surya","Budha"],
    "Mangal":["Surya","Chandra","Guru"],
    "Budha":["Surya","Shukra"],
    "Guru":["Surya","Chandra","Mangal"],
    "Shukra":["Budha","Shani"],
    "Shani":["Budha","Shukra"],
}
SHATRU = {
    "Surya":["Shukra","Shani"],"Chandra":[],"Mangal":["Budha"],"Budha":["Chandra"],
    "Guru":["Budha","Shukra"],"Shukra":["Surya","Chandra"],
    "Shani":["Surya","Chandra","Mangal"],
}

SI_GRID = {
    (0,0):11,(0,1):0,(0,2):1,(0,3):2,
    (1,0):10,                (1,3):3,
    (2,0):9,                 (2,3):4,
    (3,0):8,(3,1):7,(3,2):6,(3,3):5,
}
ALL_GRAHAS = ["Surya","Chandra","Mangal","Budha","Guru","Shukra","Shani","Rahu","Ketu"]

# FIX: Remedy suggestions filtered through this table — prevents prescribing
# pearls (Chandra) when Chandra rules a dusthana for the native's lagna.
FUNC_BENEFIC_BY_LAGNA = {
    "Mesha":      ["Surya","Chandra","Mangal","Guru"],
    "Vrishabha":  ["Budha","Shani","Shukra"],
    "Mithuna":    ["Shukra","Shani","Budha"],
    "Karka":      ["Chandra","Mangal","Guru"],
    "Simha":      ["Surya","Mangal","Guru"],
    "Kanya":      ["Budha","Shukra","Shani"],
    "Tula":       ["Shani","Budha","Shukra"],
    "Vrishchika": ["Guru","Chandra","Surya"],
    "Dhanu":      ["Surya","Mangal","Guru"],
    "Makara":     ["Shani","Shukra","Budha"],
    "Kumbha":     ["Shani","Shukra","Budha"],
    "Meena":      ["Guru","Chandra","Mangal"],
}

TIMEZONE_LIST = [
    ("IST   +5:30  India Standard Time",          5.5),
    ("NPT   +5:45  Nepal",                         5.75),
    ("PKT   +5:00  Pakistan",                      5.0),
    ("BST   +6:00  Bangladesh",                    6.0),
    ("UTC   +0:00  Universal / GMT",               0.0),
    ("WET   +0:00  London, Lisbon (Winter)",       0.0),
    ("BST   +1:00  London, Dublin (Summer)",       1.0),
    ("CET   +1:00  Paris, Berlin (Winter)",        1.0),
    ("CEST  +2:00  Paris, Berlin (Summer)",        2.0),
    ("EET   +2:00  Athens, Cairo, Istanbul",       2.0),
    ("MSK   +3:00  Moscow",                        3.0),
    ("GST   +4:00  Dubai, Abu Dhabi",              4.0),
    ("AFT   +4:30  Kabul",                         4.5),
    ("ICT   +7:00  Bangkok, Jakarta",              7.0),
    ("SGT   +8:00  Singapore, KL",                 8.0),
    ("CST   +8:00  China, Hong Kong",              8.0),
    ("JST   +9:00  Japan, Korea",                  9.0),
    ("ACST  +9:30  Adelaide",                      9.5),
    ("AEST +10:00  Sydney (Winter)",              10.0),
    ("AEDT +11:00  Sydney (Summer)",              11.0),
    ("NZST +12:00  Auckland",                     12.0),
    ("EST   -5:00  New York (Winter)",            -5.0),
    ("EDT   -4:00  New York (Summer)",            -4.0),
    ("CST   -6:00  Chicago (Winter)",             -6.0),
    ("MST   -7:00  Denver (Winter)",              -7.0),
    ("PST   -8:00  Los Angeles (Winter)",         -8.0),
    ("PDT   -7:00  Los Angeles (Summer)",         -7.0),
    ("AKST  -9:00  Alaska",                       -9.0),
    ("HST  -10:00  Hawaii",                      -10.0),
]
TZ_LABELS = [t[0] for t in TIMEZONE_LIST]
TZ_VALUES  = {t[0]: t[1] for t in TIMEZONE_LIST}

# ══════════════════════════════════════════════════════════════════════════════
#  UI PALETTE — Brutalist Minimalist (High-Contrast Monochrome / Sharp Corners)
# ══════════════════════════════════════════════════════════════════════════════
XP_BG      = "#121212"   # Deep dark canvas/window background
XP_SURFACE = "#1E1E1E"   # Container and panel surface (Zinc 900)
XP_BORDER  = "#333333"   # Sharp 1px solid borders
XP_FIELD   = "#FFFFFF"   # White background for data tables, charts, text logs, inputs
XP_TEXT_D  = "#F5F5F5"   # High-contrast light text for dark surfaces
XP_TEXT_M  = "#A1A1AA"   # Muted label text
XP_BLUE    = "#3B82F6"   # Sharp blue accent
XP_BLUE2   = "#60A5FA"   # Secondary accent
XP_BTN     = "#262626"   # Dark button surface
XP_GRAY    = "#333333"   # Neutral border / separator
XP_WARN    = "#2D2614"   # Dark amber warning banner
XP_WARN_FG = "#FDE68A"   # Warning text

# ══════════════════════════════════════════════════════════════════════════════
#  OLLAMA / BACKEND CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
# FIX: All endpoint config centralised — switch backends in one place.
# LM Studio: OLLAMA_BASE_URL = "http://localhost:1234"
# (also update ollama_engine.py payload format for OpenAI-compat schema)
OLLAMA_BASE_URL          = "http://localhost:11434"
OLLAMA_MODEL             = "qwen2.5:7b"
OLLAMA_GPU_LAYERS        = 33
OLLAMA_TEMPERATURE       = 0.30
OLLAMA_REPEAT_PENALTY    = 1.1
OLLAMA_TOP_P             = 0.9
OLLAMA_MAX_PREDICT       = 2500   # Raised from 1200 to prevent mid-sentence cutoff
OLLAMA_MAX_PREDICT_FULL  = 3800   # High-headroom budget for full 7-domain comprehensive readings

# ══════════════════════════════════════════════════════════════════════════════
#  ASTROMETRIC CONSTANTS FOR PHASE 1 IMPLEMENTATION
# ══════════════════════════════════════════════════════════════════════════════

# Planetary motion detection
STATIONARY_SPD_DEG = 0.001  # degrees/day threshold for stationary planets

# Node type configuration
NODE_TYPE_MEAN = "Mean"
NODE_TYPE_TRUE = "True"
NODE_TYPE = NODE_TYPE_MEAN  # Default to Mean Nodes for backward compatibility

# Geographic latitude protection
POLAR_LATITUDE_THRESHOLD = 60.0  # degrees - threshold for polar latitude protection

# Divisional chart boundary detection
BOUNDARY_THRESHOLD = 0.05  # degrees - proximity to sign boundaries

# Dynamic context bounds (computed per-call from payload token estimate)
OLLAMA_CTX_MIN = 1024
OLLAMA_CTX_MAX = 8192   # Expanded to 8k to accommodate RAG classical context & deep readings

# ══════════════════════════════════════════════════════════════════════════════
#  READING UI THEMES & ACCESSIBILITY TYPOGRAPHY
# ══════════════════════════════════════════════════════════════════════════════
READING_FONTS = ["Segoe UI", "Georgia", "Helvetica", "Verdana", "Consolas", "Tahoma"]
READING_DEFAULT_FONT = "Segoe UI"
READING_DEFAULT_SIZE = 11
READING_SIZES = [9, 10, 11, 12, 13, 14, 16, 18, 20]

READING_THEMES = {
    "Dark Studio": {
        "bg": "#141416",
        "fg": "#EDEDED",
        "card_bg": "#1C1C20",
        "border": "#2E2E36",
        "header_fg": "#60A5FA",
        "pred_fg": "#F4F4F5",
        "basis_fg": "#FBBF24",
        "basis_bg": "#222018",
        "sutra_fg": "#A78BFA",
        "remedy_fg": "#34D399",
        "system_fg": "#71717A",
        "thinking_fg": "#94A3B8",
        "thinking_bg": "#1A1D27",
    },
    "Parchment Book": {
        "bg": "#FAF7F2",
        "fg": "#262320",
        "card_bg": "#F2EDE4",
        "border": "#E3DCCF",
        "header_fg": "#1D4ED8",
        "pred_fg": "#1F1D1B",
        "basis_fg": "#B45309",
        "basis_bg": "#FEF3C7",
        "sutra_fg": "#6D28D9",
        "remedy_fg": "#047857",
        "system_fg": "#78716C",
        "thinking_fg": "#475569",
        "thinking_bg": "#E2E8F0",
    },
    "Classic Clean": {
        "bg": "#FFFFFF",
        "fg": "#111827",
        "card_bg": "#F8FAFC",
        "border": "#E2E8F0",
        "header_fg": "#2563EB",
        "pred_fg": "#0F172A",
        "basis_fg": "#D97706",
        "basis_bg": "#FFFBEB",
        "sutra_fg": "#7C3AED",
        "remedy_fg": "#059669",
        "system_fg": "#64748B",
        "thinking_fg": "#334155",
        "thinking_bg": "#F1F5F9",
    },
    "Cosmic Midnight": {
        "bg": "#0A0E17",
        "fg": "#E2E8F0",
        "card_bg": "#111827",
        "border": "#1E293B",
        "header_fg": "#38BDF8",
        "pred_fg": "#F8FAFC",
        "basis_fg": "#FCD34D",
        "basis_bg": "#1C1917",
        "sutra_fg": "#C084FC",
        "remedy_fg": "#4ADE80",
        "system_fg": "#64748B",
        "thinking_fg": "#94A3B8",
        "thinking_bg": "#131C2E",
    },
}

AYANAMSA_OPTIONS = ["Lahiri (Chitrapaksha)", "Raman", "KP (Krishnamurti)"]

# Dasha year system (see vedic_engine.vimshottari year_days param)
DASHA_YEAR_OPTIONS = {
    "Tropical  (365.24219d)": 365.24219,
    "Savana    (360.000000d)": 360.0,
    "Sidereal  (365.25636d)": 365.25636,
    "Julian    (365.25000d)": 365.25,
}
DASHA_YEAR_NAMES = list(DASHA_YEAR_OPTIONS.keys())
DEFAULT_THEME = "XP Classic"
DEFAULT_SCALE = "Normal"

# ── Solid header colors (brutalist, zero-gradient) ───────────────────────────
XP_HDR_L  = "#000000"   # solid black header bar
XP_HDR_R  = "#000000"   # solid black header bar
XP_HDR_H  = "#262626"   # bottom 1px divider border

# ── Ashtakavarga BPHS benefic house tables ────────────────────────────────────
# [planet][contributor] = 1-based houses from contributor giving a bindu
ASHTAK_BINDUS = {
    "Surya":  {"Surya":[1,2,4,7,8,9,10,11],"Chandra":[3,6,10,11],"Mangal":[1,2,4,7,8,9,10,11],"Budha":[3,5,6,9,10,11,12],"Guru":[5,6,9,11],"Shukra":[6,7,12],"Shani":[1,2,4,7,8,9,10,11],"Lagna":[3,4,6,10,11,12]},
    "Chandra":{"Surya":[3,6,7,8,10,11],"Chandra":[1,3,6,7,10,11],"Mangal":[2,3,5,6,9,10,11],"Budha":[1,3,4,5,7,8,10,11],"Guru":[1,4,7,8,10,11,12],"Shukra":[3,4,5,7,9,10,11],"Shani":[3,5,6,11],"Lagna":[3,6,10,11]},
    "Mangal": {"Surya":[3,5,6,10,11],"Chandra":[3,6,11],"Mangal":[1,2,4,7,8,10,11],"Budha":[3,5,6,11],"Guru":[6,10,11,12],"Shukra":[6,8,11,12],"Shani":[1,4,7,8,9,10,11],"Lagna":[1,4,7,8,9,10,11]},
    "Budha":  {"Surya":[5,6,9,11,12],"Chandra":[2,4,6,8,10,11],"Mangal":[1,2,4,7,8,9,10,11],"Budha":[1,3,5,6,9,10,11,12],"Guru":[6,8,11,12],"Shukra":[1,2,3,4,5,8,9,11],"Shani":[1,2,4,7,8,9,10,11],"Lagna":[1,2,4,6,8,10,11]},
    "Guru":   {"Surya":[1,2,3,4,7,8,9,10,11],"Chandra":[2,5,7,9,11],"Mangal":[1,2,4,7,8,10,11],"Budha":[1,2,4,5,6,9,10,11],"Guru":[1,2,3,4,7,8,10,11],"Shukra":[2,5,6,9,10,11],"Shani":[3,5,6,12],"Lagna":[1,2,4,5,6,7,9,10,11]},
    "Shukra": {"Surya":[8,11,12],"Chandra":[1,2,3,4,5,8,9,11,12],"Mangal":[3,4,6,9,11,12],"Budha":[3,5,6,9,11],"Guru":[5,8,9,10,11],"Shukra":[1,2,3,4,5,8,9,10,11],"Shani":[3,4,5,8,9,10,11],"Lagna":[1,2,3,4,5,8,9,11]},
    "Shani":  {"Surya":[1,2,4,7,8,10,11],"Chandra":[3,6,11],"Mangal":[3,5,6,10,11,12],"Budha":[6,8,9,10,11,12],"Guru":[5,6,11,12],"Shukra":[6,11,12],"Shani":[3,5,6,11],"Lagna":[1,3,4,6,10,11]},
}
ASHTAK_PLANETS = ["Surya","Chandra","Mangal","Budha","Guru","Shukra","Shani"]

# ══════════════════════════════════════════════════════════════════════════════
#  PANCHANGA LOOKUP TABLES (5 Limbs of Vedic Time)
# ══════════════════════════════════════════════════════════════════════════════

TITHI_NAMES = [
    # Shukla Paksha (1 - 15)
    "Shukla Pratipada", "Shukla Dvitiya", "Shukla Tritiya", "Shukla Chaturthi",
    "Shukla Panchami", "Shukla Shashthi", "Shukla Saptami", "Shukla Ashtami",
    "Shukla Navami", "Shukla Dashami", "Shukla Ekadashi", "Shukla Dvadashi",
    "Shukla Trayodashi", "Shukla Chaturdashi", "Purnima",
    # Krishna Paksha (16 - 30)
    "Krishna Pratipada", "Krishna Dvitiya", "Krishna Tritiya", "Krishna Chaturthi",
    "Krishna Panchami", "Krishna Shashthi", "Krishna Saptami", "Krishna Ashtami",
    "Krishna Navami", "Krishna Dashami", "Krishna Ekadashi", "Krishna Dvadashi",
    "Krishna Trayodashi", "Krishna Chaturdashi", "Amavasya",
]

NITYA_YOGAS = [
    {"name": "Vishkambha", "nature": "Ashubha", "lord": "Shani"},
    {"name": "Priti",       "nature": "Shubha",   "lord": "Budha"},
    {"name": "Ayushman",    "nature": "Shubha",   "lord": "Ketu"},
    {"name": "Saubhagya",   "nature": "Shubha",   "lord": "Shukra"},
    {"name": "Shobhana",    "nature": "Shubha",   "lord": "Surya"},
    {"name": "Atiganda",    "nature": "Ashubha", "lord": "Chandra"},
    {"name": "Sukarma",     "nature": "Shubha",   "lord": "Mangal"},
    {"name": "Dhriti",      "nature": "Shubha",   "lord": "Rahu"},
    {"name": "Shula",       "nature": "Ashubha", "lord": "Guru"},
    {"name": "Ganda",       "nature": "Ashubha", "lord": "Shani"},
    {"name": "Vriddhi",     "nature": "Shubha",   "lord": "Budha"},
    {"name": "Dhruva",      "nature": "Shubha",   "lord": "Ketu"},
    {"name": "Vyaghata",    "nature": "Ashubha", "lord": "Shukra"},
    {"name": "Harshana",    "nature": "Shubha",   "lord": "Surya"},
    {"name": "Vajra",       "nature": "Ashubha", "lord": "Chandra"},
    {"name": "Siddhi",      "nature": "Shubha",   "lord": "Mangal"},
    {"name": "Vyatipata",   "nature": "Ashubha", "lord": "Rahu"},
    {"name": "Variyan",     "nature": "Shubha",   "lord": "Guru"},
    {"name": "Parigha",     "nature": "Ashubha", "lord": "Shani"},
    {"name": "Shiva",       "nature": "Shubha",   "lord": "Budha"},
    {"name": "Siddha",      "nature": "Shubha",   "lord": "Ketu"},
    {"name": "Sadhya",      "nature": "Shubha",   "lord": "Shukra"},
    {"name": "Shubha",      "nature": "Shubha",   "lord": "Surya"},
    {"name": "Shukla",      "nature": "Shubha",   "lord": "Chandra"},
    {"name": "Brahma",      "nature": "Shubha",   "lord": "Mangal"},
    {"name": "Indra",       "nature": "Shubha",   "lord": "Rahu"},
    {"name": "Vaidhriti",   "nature": "Ashubha", "lord": "Guru"},
]

CHARA_KARANAS = [
    "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti (Bhadra)",
]
STHIRA_KARANAS = {
    57: "Shakuni",
    58: "Chatushpada",
    59: "Naga",
    0:  "Kintughna",  # First half of Shukla Pratipada
}

VARA_NAMES = [
    {"name": "Somavara",    "graha": "Chandra", "english": "Monday"},
    {"name": "Mangalavara", "graha": "Mangal",  "english": "Tuesday"},
    {"name": "Budhavara",   "graha": "Budha",   "english": "Wednesday"},
    {"name": "Guruvara",    "graha": "Guru",    "english": "Thursday"},
    {"name": "Shukravara",  "graha": "Shukra",  "english": "Friday"},
    {"name": "Shanivara",   "graha": "Shani",   "english": "Saturday"},
    {"name": "Ravivara",    "graha": "Surya",   "english": "Sunday"},
]

# ══════════════════════════════════════════════════════════════════════════════
#  GEMSTONE PRESCRIPTION SPECIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════

GEMSTONE_SPECS = {
    "Surya": {
        "gemstone": "Ruby", "sanskrit": "Manikya",
        "uparatna": ["Red Garnet", "Red Spinel"],
        "metal": "Gold or Copper",
        "finger": "Ring finger (Anamika) of right hand",
        "day": "Sunday morning at sunrise during Shukla Paksha",
        "min_carat_divisor": 12.0,
        "min_carats": 3.0,
        "mantra": "Om Hram Hreem Hroum Sah Suryaya Namah (7,000 repetitions)",
    },
    "Chandra": {
        "gemstone": "Natural Pearl", "sanskrit": "Mukta",
        "uparatna": ["Moonstone"],
        "metal": "Silver",
        "finger": "Little finger (Kanishtha) of right hand",
        "day": "Monday evening or morning during Shukla Paksha",
        "min_carat_divisor": 11.0,
        "min_carats": 4.0,
        "mantra": "Om Shram Shreem Shroum Sah Chandraya Namah (11,000 repetitions)",
    },
    "Mangal": {
        "gemstone": "Red Coral", "sanskrit": "Moonga",
        "uparatna": ["Carnelian"],
        "metal": "Gold, Copper, or Panchadhatu",
        "finger": "Ring finger (Anamika) of right hand",
        "day": "Tuesday morning during Shukla Paksha",
        "min_carat_divisor": 10.0,
        "min_carats": 5.0,
        "mantra": "Om Kram Kreem Kroum Sah Bhaumaya Namah (10,000 repetitions)",
    },
    "Budha": {
        "gemstone": "Emerald", "sanskrit": "Panna",
        "uparatna": ["Peridot", "Green Tourmaline"],
        "metal": "Gold or Bronze",
        "finger": "Little finger (Kanishtha) of right hand",
        "day": "Wednesday morning during Shukla Paksha",
        "min_carat_divisor": 12.0,
        "min_carats": 3.0,
        "mantra": "Om Bram Breem Broum Sah Budhaya Namah (9,000 repetitions)",
    },
    "Guru": {
        "gemstone": "Yellow Sapphire", "sanskrit": "Pukhraj",
        "uparatna": ["Yellow Topaz", "Citrine"],
        "metal": "Gold",
        "finger": "Index finger (Tarjani) of right hand",
        "day": "Thursday morning during Shukla Paksha",
        "min_carat_divisor": 11.0,
        "min_carats": 3.5,
        "mantra": "Om Gram Greem Groum Sah Gurave Namah (19,000 repetitions)",
    },
    "Shukra": {
        "gemstone": "Diamond / White Sapphire", "sanskrit": "Heera / Safed Pukhraj",
        "uparatna": ["White Zircon", "Opal"],
        "metal": "Platinum, White Gold, or Silver",
        "finger": "Middle finger (Madhyama) or Little finger (Kanishtha)",
        "day": "Friday morning during Shukla Paksha",
        "min_carat_divisor": 50.0,
        "min_carats": 0.5,
        "mantra": "Om Dram Dreem Droum Sah Shukraya Namah (16,000 repetitions)",
    },
    "Shani": {
        "gemstone": "Blue Sapphire", "sanskrit": "Neelam",
        "uparatna": ["Amethyst", "Blue Topaz", "Iolite"],
        "metal": "Panchadhatu, Iron, or White Gold",
        "finger": "Middle finger (Madhyama) of right hand",
        "day": "Saturday evening/twilight during Shukla Paksha",
        "min_carat_divisor": 12.0,
        "min_carats": 4.0,
        "mantra": "Om Pram Preem Proum Sah Shanaishcharaya Namah (23,000 repetitions)",
    },
    "Rahu": {
        "gemstone": "Hessonite Garnet", "sanskrit": "Gomed",
        "uparatna": ["Orange Zircon"],
        "metal": "Silver or Ashtadhatu",
        "finger": "Middle finger (Madhyama) of right hand",
        "day": "Saturday night during Krishna Paksha",
        "min_carat_divisor": 11.0,
        "min_carats": 4.5,
        "mantra": "Om Bhram Bhreem Bhroum Sah Rahave Namah (18,000 repetitions)",
    },
    "Ketu": {
        "gemstone": "Cat's Eye Chrysoberyl", "sanskrit": "Vaidurya / Lahsuniya",
        "uparatna": ["Cat's Eye Quartz", "Tiger Eye"],
        "metal": "Silver or Panchadhatu",
        "finger": "Little finger (Kanishtha) or Ring finger (Anamika)",
        "day": "Thursday or Tuesday night during Krishna Paksha",
        "min_carat_divisor": 12.0,
        "min_carats": 3.5,
        "mantra": "Om Stram Streem Stroum Sah Ketave Namah (17,000 repetitions)",
    },
}

