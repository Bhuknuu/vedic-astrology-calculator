# Vedic Astrology Calculator & Offline AI Jyotishi 🪐

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Ephemeris](https://img.shields.io/badge/Ephemeris-Swiss%20Ephemeris%20(pyswisseph)-orange.svg)](https://www.astro.com/swisseph/)
[![AI](https://img.shields.io/badge/AI-Local%20Ollama%20(Offline)-green.svg)](https://ollama.ai/)
[![UI](https://img.shields.io/badge/UI-Brutalist%20Minimalist%20Tkinter-lightgrey.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A high-precision Vedic Astrology (Parashari Jyotish) calculation engine and local AI reasoning system. Designed for astrologers, researchers, and developers who demand astronomical precision, classical BPHS algorithmic fidelity, responsive UI architecture, and 100% offline, privacy-first AI analysis.

---

## ✨ Features & Capabilities

### 🔭 Astronomical & Mathematical Engine (`core/`)
- **Swiss Ephemeris Precision**: High-accuracy planetary calculations via `pyswisseph` (<0.1 arcsec), with an automatic internal Moshier analytical fallback.
- **Multiple Ayanamsas**: Lahiri (Chitrapaksha), Raman, Krishnamurti (KP), and Fagan-Bradley.
- **Panchanga (5 Limbs of Vedic Time)**:
  - **Tithi**: 30 lunar phases (Shukla/Krishna paksha, elapsed degree & percentage).
  - **Vara**: Solar weekday with ruling graha lord.
  - **Nakshatra**: 27 lunar mansions with exact 4-pada breakdown and nakshatra lord.
  - **Nitya Yoga**: 27 solilunar combinations with auspicious/inauspicious (*Shubha/Ashubha*) classification.
  - **Karana**: 60 half-tithis (7 movable chara + 4 fixed sthira), highlighting inauspicious *Vishti (Bhadra)*.
- **Vimshottari Dasha Engine**:
  - Full 120-year cycle breakdown: **Mahadasha → Antardasha → Pratyantardasha**.
  - Configurable year length: *365.2422d Solar Tropical*, *360d Savana*, or *354.36d Lunar Synodic*.
  - Dasha balance at birth computed down to exact years, months, and days.
- **Bhava Chalit & Sripathi Cusps**:
  - Exact Sripathi unequal house division with mid-cusps (*Bhava Madhya*) and sandhi boundaries.
  - Automatic detection of sign-to-house shifting planets.
- **Ashtakavarga & Sarvashtakavarga**:
  - 12-sign bindu point matrices for all 7 classical planets.
  - Comprehensive Sarvashtakavarga (SAV) aggregate strength scoring.
- **Shodashavarga (16 Divisional Charts)**:
  - D-1 (Rasi), D-2 (Hora), D-3 (Drekkana), D-4 (Chaturthamsha), D-7 (Saptamsha), D-9 (Navamsa), D-10 (Dashamsha), D-12 (Dwadashamsha), D-16 (Shodashamsha), D-20 (Vimshamsha), D-24 (Chaturvimshamsha), D-27 (Bhamsha), D-30 (Trishamsha), D-40 (Khavedamsha), D-45 (Akshavedamsha), and D-60 (Shashtiamsha).
- **Shadbala (6-Fold Planetary Strength)**:
  - Sthana Bala (Uchcha, Saptavargaja, Kendradi), Cheshta Bala, Naisargika Bala, and overall dignity.
- **Classical Gemstone Prescriptions (BPHS Safety Filter)**:
  - Enforces Brihat Parashara Hora Shastra functional benefic/malefic rules per ascendant (*Lagna*).
  - Categorically warns against wearing gemstones of functional malefics (6th, 8th, 12th lords).
  - Prescribes weight scaled to native's body weight, setting metal, auspicious finger, wearing day/time, and Vedic consecration mantra. Provides safe alternatives (*Mantra Japa*, *Daana*, charity) for malefic planets.
- **Transit Overlay (Gochara)**:
  - Real-time planetary transits overlaid directly on the natal chart.

---

### 🧠 Offline Local AI Jyotish Engine (`ai/`)
- **100% Offline & Private**: Powered by local Ollama instances (e.g., `qwen2.5:7b-instruct`). No data ever leaves your computer.
- **Zero Cross-Chart Leakage**: Model KV cache is evicted (`keep_alive: 0` + `DELETE /api/generate`) whenever a new chart is calculated or imported, preventing context bleed between native profiles.
- **Intelligent Semantic Context Compression**:
  - Categorizes queries into domains: `CAREER`, `RELATIONSHIPS`, `FINANCE`, `HEALTH`, `EDUCATION`, `TIMING_DASHA`, `REMEDIES`, or `GENERAL`.
  - Prunes irrelevant chart nodes while retaining full precision for pertinent houses and significators (*Karaka*).
  - Rolling multi-turn extractive summarization retains salient takeaways across questions without overflowing context windows.

---

### 🖥️ Brutalist Minimalist UI Architecture (`ui/`)
- High-contrast brutalist aesthetic: solid dark frames (`#121212`, `#1E1E1E`, `#333333`), crisp white content fields (`#FFFFFF`), bold headers, and zero blurry gradients.
- Fully responsive layout: proportional dual-pane partition via `tk.PanedWindow(stretch="always")` that expands cleanly to any screen resolution.
- Live resizing custom Canvas charts (North Indian Diamond Chart format).
- Complete dossier report export: Instant generation of comprehensive plain-text/markdown consultation dossiers (`.txt`/`.md`).

---

## 📂 Repository Structure

```
vedic-astrology-calculator/
├── core/                        # Astronomical & Jyotish computation engines
│   ├── astro_engine.py          # Swiss Ephemeris & Moshier ephemeris wrappers
│   ├── vedic_engine.py          # Parashari logic, Panchanga, Dasha, Shadbala, Gems
│   └── constants.py             # Sanskritic constants, palettes, definitions
├── ai/                          # Offline AI intelligence & context management
│   ├── ollama_engine.py         # Streaming HTTP client & KV cache eviction
│   └── prediction_engine.py     # Domain classifier, chart pruner, conversation manager
├── ui/                          # Brutalist Minimalist graphical interface
│   ├── app.py                   # Main Jyotish application window & controller
│   └── ui_widgets.py            # Custom Tkinter controls, responsive charts, styles
├── tests/                       # Unit test suite
│   ├── test_core.py             # Math, ephemeris, and astrological accuracy tests
│   └── test_ai.py               # AI prompt compression and domain routing tests
├── reference/                   # Classical references, audit reports, proposals
├── main.py                      # Application entry point
├── run.sh                       # Automated environment manager & runner
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+**
- **Tkinter**:
  - **Arch Linux / Manjaro**: `sudo pacman -S tk`
  - **Debian / Ubuntu**: `sudo apt install python3-tk python3-tk-dev`
  - **Fedora**: `sudo dnf install python3-tkinter`
  - **macOS / Windows**: Bundled automatically with Python installers.

### 2. Quick Launch
The included `run.sh` script handles virtual environment creation, wheel installation (`pyswisseph`), and execution automatically:

```bash
chmod +x run.sh
./run.sh
```

### 3. Running Unit Tests
To run the automated test suite:

```bash
./run.sh --test
```

---

## 🤖 Configuring Local AI (Ollama)

1. Install [Ollama](https://ollama.ai/):
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```
2. Pull the recommended Jyotish model:
   ```bash
   ollama pull qwen2.5:7b
   ```
3. Start the Ollama server:
   ```bash
   ollama serve
   ```
4. Launch the application. In the **AI Jyotishi** tab, click **Refresh** to connect.

---

## 📄 License
Released under the [MIT License](LICENSE).
