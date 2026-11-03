# Vedic Astrology Calculator — Technical Architecture & Developer Reference

This document provides a technical reference for the modularized codebase of the Vedic Astrology Calculator (v6.0). It covers data flows, core mathematical mechanics, offline resilience design, and module-level API documentation.

---

## 1. System Architecture & Directory Layout

```
vedic-astrology-calculator/
├── main.py                     # Application entry point & DPI bootstrap
├── setup.sh                    # Environment, dependencies & Modelfile setup
├── run.sh                      # Shell launcher
├── core/                       # Astrometry & classical Parashari mathematical engine
│   ├── __init__.py             # Public API exports
│   ├── constants.py            # Astronomical constants, dignity tables, gemstone specs
│   ├── astro_engine.py         # Swiss Ephemeris driver, Keplerian fallback, DST resolver
│   └── vedic_engine.py         # 6-Fold Shadbala, Vargas, Dasha, Panchanga, Gemstones
├── ai/                         # Offline Neuro-Symbolic AI & RAG system
│   ├── __init__.py             # AI module exports
│   ├── ollama_engine.py        # Local Ollama streaming client & thread cancellation
│   ├── prediction_engine.py    # Minified chart JSON serialization & prompt builder
│   ├── rag_engine.py           # Manuscript retrieval & verse grounding
│   └── manuscript_rag.py       # Okapi BM25 scriptural retrieval engine
├── ui/                         # Presentation layer (Windows XP Luna Design System)
│   ├── __init__.py             # UI module exports
│   ├── app.py                  # Main Tkinter controller, tabs, background threads
│   └── ui_widgets.py           # XP Luna widgets, Canvas South-Indian chart, Geocoder
├── data/manuscripts/           # Canonical JSON corpora (BPHS, Phaladeepika)
├── tests/                      # Automated test suite (14 core tests, AI tests)
└── reference/                  # Architectural audits, scorecard, changelog
    ├── CHANGELOG.md            # Detailed release history & v6.0 milestone notes
    ├── IMPLEMENTATION_PLAN.md  # Multi-phase engineering roadmap
    └── DOCUMENTATION.md        # Technical API & architecture reference (this file)
```

---

## 2. Core Modules (`core/`)

### `core/constants.py`
Static tables, physical constants, and Sanskrit mappings:
- **`TROPICAL_YEAR`**: $365.24219\text{ days}$. Governs Vimshottari Dasha to prevent cumulative 15–20 day drift across 60-year spans.
- **Astrological Tables**: Signs (`RASHIS`), Nakshatras (`NAKSHATRAS`), Exaltation degrees (`UCHCHA_DEG`), Debilitation degrees (`NEECHA_DEG`), Swakshetra lords, and Moolatrikona boundaries.
- **`FUNC_BENEFIC_BY_LAGNA`**: Functional benefic mapping for all 12 ascendants, enforcing gemstone safety filters per BPHS.
- **`ASHTAK_BINDUS`**: Parashari bindu contribution rules across 8 contributors (7 planets + Lagna).
- **Astrometrical Thresholds**:
  - `STATIONARY_SPD_DEG = 0.001`: Threshold for 4-state stationary motion classification.
  - `POLAR_LATITUDE_THRESHOLD = 60.0`: Polar fallback boundary for house cusps.
  - `BOUNDARY_THRESHOLD = 0.05`: $3'$ boundary alert threshold for divisional charts.
- **Panchanga & Gemstone Data**: `TITHI_NAMES`, `VARA_NAMES`, `NITYA_YOGA_NAMES`, `KARANA_NAMES`, and `GEMSTONE_SPECS`.

### `core/astro_engine.py`
Astronomical coordinate calculation and ephemeris integration:
- **`SweEngine`**: High-precision driver utilizing `pyswisseph` in Moshier mode:
  - `compute(..., node_type="true", ayanamsa_key="lahiri")`: Sidereal coordinates for Sun through Ketu, Ascendant, and 12 Porphyry house cusps.
  - Independent Ketu velocity calculation derived from true orbital mechanics.
  - 4-state stationary motion detection (`direct`, `retrograde`, `stationary_direct`, `stationary_retrograde`).
  - High-latitude polar fallback (`equal_house_polar_fallback()`) ensuring stability at $|\text{lat}| \ge 60^\circ$.
- **`AstroEngine`**: Pure-Python Keplerian fallback calculating solar, lunar, and planetary coordinates using perturbation approximations when `pyswisseph` is unavailable.
- **`resolve_timezone(iana_tz_name, y, mo, d, h, mi)`**: Standard library `zoneinfo` resolver computing historical decimal UTC offsets, daylight saving status, and time abbreviations.
- **`compute_chart(name, y, mo, d, h, mi, lat, lon, tz_offset, ...)`**: Unified calculation dispatcher returning structured `chart` dictionary with planetary coordinates, house cusps, and metadata.

### `core/vedic_engine.py`
Classical Parashari interpretative mathematical mechanics:
- **`sthiti(planet, lon, rashi)`**: Dignity classification (Exalted, Debilitated, Moolatrikona, Own Sign, Friend, Enemy, Neutral).
- **`varga(lon, n, return_boundary=False)`**: Harmonic division for charts D-1 through D-60. When `return_boundary=True`, checks if longitude lies within $\pm 0.05^\circ$ of a division boundary.
- **`compute_varga_chart(grahas, n)`**: Generates complete divisional chart with planet positions, relative bhavas, and boundary sensitivity warnings.
- **`vimshottari(chandra_lon, jd, year_days=365.24219, depth=2)`**: Multi-level dasha hierarchy (Level 1 Mahadasha through Level 4 Sookshmadasha).
- **`compute_pratyantardasha_for_ad(ad_dict, year_days=365.24219)`**: On-demand expansion of Antardashas into 9 Pratyantardashas.
- **`shadbala(grahas, cusps, lat, lon, jd)`**: Complete 6-fold strength analysis:
  - *Sthana Bala:* Uchcha, Ojhayugmarashi, Drekkana, Kendradi, Saptavargaja.
  - *Dig Bala:* Directional strength on cardinal cusps.
  - *Kala Bala:* Diurnal, tri-bhaga, and cyclic temporal strength.
  - *Chesta Bala:* Motional strength (enhanced for retrograde/stationary).
  - *Naisargika Bala:* Natural planetary luminosity constant.
  - *Drik Bala:* Mutual angular aspects using classical special aspect rules (Mars 4/7/8, Jupiter 5/7/9, Saturn 3/7/10).
  - *Ayana Bala:* Declination strength ($\delta$) via Swiss Ephemeris equatorial sidereal flag.
- **`panchanga(sun_lon, moon_lon, jd)`**: Computes the 5 classical limbs: Tithi, Vara, Nakshatra, Nitya Yoga, and Karana.
- **`gemstone_prescription(lagna_rashi, grahas)`**: Generates tailored gemstone recommendations and enforces the BPHS safety filter to contraindicate gems for functional malefics.
- **`yoga(grahas, cusps)` & `dosha(grahas, cusps)`**: Algorithmic detection of classical planetary combinations (Gaja Kesari, Raja Yogas, Mangal, Kaal Sarp).
- **`ashtakavarga(grahas, cusps)` & `sarvashtakavarga(av_dict)`**: 8-contributor bindu grids and total Sarva index per sign.

---

## 3. AI & Knowledge Retrieval Layer (`ai/`)

### `ai/ollama_engine.py`
Manages offline LLM inference via the local Ollama daemon:
- **`OllamaEngine`**:
  - `ping()` & `list_models()`: Non-blocking service discovery.
  - `generate_stream()`: Streams token responses over HTTP chunked transfer.
  - `request_stop()`: Immediate cancellation of running generation via server-side DELETE requests.
  - `_dynamic_ctx()`: Dynamically scales Ollama context buffer (1024–3072 tokens) based on estimated prompt length to protect GPU VRAM.

### `ai/prediction_engine.py`
Context compression and prompt engineering:
- **`chart_json(chart)`**: Serializes complex chart states into dense, minified JSON (~40% token savings over raw text).
- **`system_prompt()`**: Establishes astrologer identity, ethical guidelines, psychological framing, and non-fatalistic guidelines.
- **`user_prompt_full()` & `user_prompt_qa()`**: Task-specific prompt constructors.

### `ai/rag_engine.py` & `ai/manuscript_rag.py`
Grounded scriptural knowledge retrieval:
- Ingests canonical JSON manuscripts (`data/manuscripts/bphs_foundations.json`, `data/manuscripts/phaladeepika_principles.json`).
- Utilizes Okapi BM25 rankers to retrieve relevant Sanskrit shastras and English translations for planetary combinations before generating interpretations.

---

## 4. Presentation Layer (`ui/`)

### `ui/ui_widgets.py`
Windows XP Luna design system and custom Tkinter components:
- **`XPGradientHeader`**: Renders the royal Luna blue linear gradient banner (`#0A246A` → `#A6CAF0`).
- **`XPStatusBar`**: Multi-panel inset status bar.
- **`XPTooltip`**: Hover help text for UI controls.
- **`RashiChart`**: Custom canvas rendering traditional South-Indian diamond charts with retrograde badges (`[R]`), stationary markers (`[SD]`/`[SR]`), and transit overlays.
- **`Geocoder`**: Asynchronous OpenStreetMap Nominatim client featuring a 1.5s debounce and exponential backoff retry.

### `ui/app.py`
Primary application controller:
- **`JyotishApp`**:
  - Configures the 1260×860 layout, menu bars, and 10 analytical tabs (Rashi, Graha, Varga, Dasha, Yoga/Dosha, Shadbala, Chalit, Ashtakavarga, Gochara, AI Reading).
  - Spawns background worker threads for geocoding and Ollama streaming.
  - Implements `.jyotish` JSON chart file serialization and deserialization.

---

## 5. Verification & Testing (`tests/`)

- Run the test suite:
  ```bash
  python3 -m unittest discover -s tests
  ```
- **`tests/test_core.py`**: 14 tests validating mathematical engines:
  - Swiss Ephemeris sidereal coordinate accuracy.
  - 6-fold Shadbala components (Drik, Ayana, Sthana).
  - True Node vectors and independent Ketu velocity.
  - 4-state stationary motion detection.
  - Polar latitude equal-house fallback.
  - Multi-level Vimshottari Dasha calculations.
  - Divisional chart boundary warnings.
  - Panchanga 5 limbs calculation.
  - Gemstone prescription safety filtering.
  - Historical timezone and DST resolution.
- **`tests/test_ai.py`**: Offline prompt generation and token compression tests.
