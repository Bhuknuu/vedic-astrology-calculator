# Vedic Astrology Calculator v6.0 — Master Implementation Plan & Engineering Audit

> Generated from architectural analysis of `PROJECT_SCORECARD.md`, `DEVILS_ADVOCATE_REPORT.md`,
> `BETTERMENT_PROPOSAL.md`, and `MULTI_AGENT_ARCHITECTURE.md`.

---

## Table of Contents

1. [Strategic Priority](#1-strategic-priority)
2. [Phased Roadmap Overview](#2-phased-roadmap-overview)
3. [Phase 1 — Astrometry & Mathematical Integrity](#3-phase-1--astrometry--mathematical-integrity)
4. [Phase 2 — Core Engineering & Offline Resilience](#4-phase-2--core-engineering--offline-resilience)
5. [Phase 3 — Multi-Agent AI Pipeline & Sutra RAG](#5-phase-3--multi-agent-ai-pipeline--sutra-rag)
6. [Phase 4 — Interactive UX & Windows XP Polish](#6-phase-4--interactive-ux--windows-xp-polish)
7. [Phase 5 — Trust, Consultation & Deliverables](#7-phase-5--trust-consultation--deliverables)
8. [Quality & Test Strategy](#8-quality--test-strategy)
9. [Ponytail-Audit: Over-Engineering Findings](#9-ponytail-audit-over-engineering-findings)

---

## 1. Strategic Priority

**The single most impactful upgrade is the completion of the mathematical core (full 6-fold Shadbala + historical DST resolver + True Node toggle), paired immediately with the upgrade of the LLM layer from a monolithic single-prompt design to a 5-stage, sutra-grounded Cognitive Pipeline.**

**Reason:** The AI reading layer operates on the `grahas` dictionary produced by `astro_engine.py` and `vedic_engine.py`. If either of these contains incomplete or misrepresented data (e.g. a Shadbala "pass/fail" total based on only 4 of 6 components, a 1-hour DST offset error that shifts the ascendant by ~15°, or hardcoded Ketu retrograde with cloned Rahu speed), the LLM will generate articulate but structurally incorrect interpretations. Accuracy of the foundation must precede the quality of what is built upon it.

```
Mathematical Ground Truth
        ↓
Engine Stability & Concurrency
        ↓
Cognitive AI Pipeline
        ↓
Interactive UX
        ↓
Client Deliverables
```

---

## 2. Phased Roadmap Overview

| Phase | Theme | Key Deliverables | Files Affected | Risk |
|:---:|:---|:---|:---|:---:|
| 1 | Astrometry & Mathematical Rigor | 6-fold Shadbala, True Nodes, Pratyantardasha, polar latitudes | `astro_engine.py`, `vedic_engine.py` | Low |
| 2 | Core Engineering & Offline Resilience | SQLite geocache, Auto-DST, thread locks, input validation | `ui_widgets.py`, `app.py` | Low |
| 3 | Cognitive AI Pipeline & Sutra RAG | 5-stage agent pipeline, verse citations, minified JSON | `prediction_engine.py`, `ollama_engine.py` | Medium |
| 4 | Interactive XP Presentation | DPI scaling, chart hover/clicks, scroll fix, theme switcher | `ui_widgets.py`, `constants.py`, `app.py` | Low |
| 5 | Trust & Consultation Tools | Rectification slider, Math Proof panel, PDF export | `app.py`, new `report_generator.py` | Medium |

---

## 3. Phase 1 — Astrometry & Mathematical Integrity

**Objective:** Complete all missing classical Jyotish mathematical components so downstream AI features and interpretations operate on authentic, uncompromised ground truth.

**Status: COMPLETED (Core Mathematical Engine) — Tasks 1.1–1.6, plus Panchanga & Gemstone Engines implemented and verified.**

---

### Task 1.1: Complete 6-Fold Shadbala Engine ✅

**Files:** `vedic_engine.py:443`, `constants.py`, `app.py:883`  
**Scorecard Rating:** 5/10 → Target 9/10 (Core Complete)

**Implemented:**
- **Drik Bala:** Mutual aspect angles between all 7 grahas. Classical special aspect rules (Mars: 4th, 7th, 8th; Jupiter: 5th, 7th, 9th; Saturn: 3rd, 7th, 10th; all others: 7th only). Net virupa calculated from benefics minus malefics.
- **Ayana Bala:** Swiss Ephemeris `FLG_EQUATORIAL | FLG_SIDEREAL` for planetary declination δ. Score based on obliquity of the ecliptic (ε ≈ 23.44°). Natural benefics receive maximum strength with northern declination, malefics with southern declination.
- **Ojhayugmarashi Bala:** Odd/even sign placement rules per BPHS.
- **Drekkana Bala:** Decanate lordship dignity checks.
- **Kendradi Bala:** Cusp-based quadrant placement.
- **Full Sthana Bala:** Complete aggregate of Uchcha, Ojhayugmarashi, Drekkana, and Kendradi.
- Total Shadbala score now incorporates all 6 classical components; removed misleading partial totals.

---

### Task 1.2: Lunar True Nodes & Independent Ketu Vector ✅

**Files:** `astro_engine.py:134`, `constants.py`, `app.py`  
**Scorecard Rating:** Bug → Fixed (Core Complete)

**Implemented:**
- Added `NODE_TYPE_MEAN` and `NODE_TYPE_TRUE` configuration in `constants.py`.
- When `"True"` is active, uses `swe.TRUE_NODE` for Rahu and computes Ketu's velocity independently via opposite node ephemeris position (`xx_k[3]`), rather than cloning Rahu's speed vector.
- Graceful backward compatibility with `"Mean"` mode.

---

### Task 1.3: Stationary Planetary Motion Detection ✅

**Files:** `astro_engine.py:150`  
**Scorecard Rating:** 9/10 → Target 10/10 (Core Complete)

**Implemented:**
- Added stationary threshold constant: `STATIONARY_SPD_DEG = 0.001` (degrees/day) in `constants.py`.
- Classifies planetary motion into four discrete classical states: `"D"` (Direct), `"R"` (Retrograde), `"SD"` (Stationary Direct), `"SR"` (Stationary Retrograde).
- Stored as `"motion_state"` in each planet's dictionary.

---

### Task 1.4: High-Latitude Polar Quadrant Protection ✅

**Files:** `astro_engine.py:175`, `app.py`  
**Scorecard Rating:** 9/10 → Target 10/10 (Core Complete)

**Implemented:**
- Added `POLAR_LATITUDE_THRESHOLD = 60.0` degrees in `constants.py`.
- At polar latitudes (`abs(lat) > 60.0`), falls back to geometric Equal House cusps (30° increments from Ascendant) to prevent tangent math domain errors.
- Annotates `_meta` with `"bhava_method": "equal_house_polar_fallback"`.

---

### Task 1.5: Pratyantardasha (Level 3) & Sookshmadasha (Level 4) ✅

**Files:** `vedic_engine.py:330`, `app.py:840`  
**Scorecard Rating:** 5/10 → Target 8/10 (Core Complete)

**Implemented:**
- Expanded `vimshottari(chandra_lon, jd, year_days=365.24219, depth=2, current_only_sub=False)` with configurable nesting depth (1 through 4).
- Added `compute_pratyantardasha_for_ad(ad_dict, year_days=365.24219, include_sookshma=False)` for on-demand Level 3 and Level 4 expansion when user double-clicks an Antardasha row in the UI.
- Rigorously validates classical dasha proportions ($Y_{sub} = Y_{parent} \times \text{DASHA\_VARSH}[lord] / 120.0$) and ensures continuous start/end datetime intervals with zero rounding drift.

---

### Task 1.6: Divisional Chart Boundary Proximity Warnings ✅

**Files:** `vedic_engine.py`, `app.py`  
**Scorecard Rating:** Devil's Advocate 3.3 (Core Complete)

**Implemented:**
- Added `BOUNDARY_THRESHOLD = 0.05` degrees in `constants.py`.
- Enhanced `varga(lon, n, return_boundary=False)` to optionally return `(rashi, is_near_boundary, deg_in_varga)`.
- Added `check_varga_boundary(lon, n, threshold=BOUNDARY_THRESHOLD)` to test if a natal longitude sits within ±0.05° of a division boundary.
- Added `compute_varga_chart(grahas, n, threshold=BOUNDARY_THRESHOLD)` returning complete divisional chart placements with `"boundary_flag"`, `"boundary_dist"`, `"varga_rashi"`, `"varga_ansh"`, `"varga_longitude"`, and `"bhava"` relative to divisional Lagna.

---

### Additional Mathematical Modules Implemented:

#### Task 1.7: Classical Panchanga Engine (5 Limbs of Time) ✅
**Files:** `vedic_engine.py`, `constants.py`  
- Computes **Tithi** (1–30, Shukla/Krishna paksha, elapsed percentage).
- Computes **Vara** (Sanskrit weekday & ruling graha).
- Computes **Nakshatra** (1–27, pada 1–4, ruler, elapsed percentage).
- Computes **Nitya Yoga** (27 solilunar yogas, auspicious/inauspicious classification, ruler).
- Computes **Karana** (60 half-tithis mapped to 4 fixed and 7 repeating karanas, identifying Vishti/Bhadra).

#### Task 1.8: Gemstone Prescription Specifications & Safety Filter ✅
**Files:** `vedic_engine.py`, `constants.py`  
- Comprehensive gemstone specifications: primary gem, Sanskrit name, uparatna substitutes, metal, finger, day/hora, consecration mantra.
- Body-weight-based carat and ratti calculation formula.
- Strict safety filter: automatically contraindicates gemstones for functional malefics of the native's Lagna, prescribing safe alternative remedies (mantra japa, charity, puja).

---

## 4. Phase 2 — Core Engineering & Offline Resilience

**Objective:** Eliminate race conditions, ensure the application works 100% offline, and prevent crashes from input boundary conditions or network failures.

---

### Task 2.1: Local SQLite Geocoding Cache & City Fallback

**Files:** `ui_widgets.py:442`  
**Scorecard Ratings:** 18/10 (6/10 → 9/10), 34/10 (2/10 → 7/10)

**Current issue (Devil's Advocate 2.1):** Every location search in `Geocoder.lookup()` fires a live HTTP request to OpenStreetMap Nominatim. There is no local cache. Repeating lookups for the same city waste network calls, risk IP-bans (HTTP 429), and make the app completely unusable offline.

**Technical spec:**
- Create `geocode_cache.db` (SQLite, stored in the OS user data directory or project root).
- Schema: `CREATE TABLE cache (query TEXT PRIMARY KEY, lat REAL, lon REAL, display_name TEXT, tz_name TEXT, fetched_at DATETIME)`.
- Before any HTTP call, check the local DB. Cache hit → return immediately. Cache miss → call Nominatim, store result, return.
- Bundle a compact offline fallback JSON of the top ~3,000 global cities and major Indian cities (lat/lon/timezone). Load this as a last resort when the network is unavailable and no cache entry exists.

---

### Task 2.2: Historical Timezone & DST Auto-Resolver

**Files:** `astro_engine.py`, `app.py:650`  
**Scorecard Rating (implied):** Devil's Advocate 2.3 — high-severity flaw  
**Status:** Core Backend Complete ✅; UI binding pending Phase 4.

**Current issue:** DST is left to manual user entry. A 1-hour DST error shifts the Ascendant by ~15°, invalidating all house placements and lordships.

**Implemented (Core):**
- Added `resolve_timezone(iana_tz_name, y, mo, d, h=12, mi=0)` in `astro_engine.py` using Python standard library `zoneinfo.ZoneInfo`.
- Accurately returns decimal UTC offset, daylight saving status (`is_dst`), and timezone abbreviation (`tz_abbr`).
- Integrated into `compute_chart(..., iana_tz=...)` to automatically derive UTC offset and record timezone/DST metadata in `_meta`.

**Technical spec (UI integration):**
- When a city is geocoded, pass its IANA timezone string to `resolve_timezone()`.
- Automatically update the timezone offset input field.
- Display a `"DST Active"` / `"DST Inactive"` indicator badge next to the timezone field.
- Store the IANA timezone string in `.jyotish` chart files for reproducibility.

---

### Task 2.3: Thread Mutex Locks & Button State Guards

**Files:** `app.py:750`, `ollama_engine.py`  
**Scorecard Rating:** 20/10 (7/10 → 9/10)

**Current issue (Devil's Advocate 2.2):** The LLM generation stream and chart calculation both run in `threading.Thread` without locks on shared state variables (`self._render_buf`, chat widget). Multiple rapid clicks launch concurrent threads writing into the same Tkinter widget, scrambling output.

**Technical spec:**
- Add `self._calc_lock = threading.Lock()` in `JyotishApp.__init__()`.
- On "Generate Chart" or "Ask AI": acquire lock → set buttons to `state=tk.DISABLED` → set cursor to `"watch"` → run thread → in `finally:` release lock → re-enable buttons → restore cursor.
- Prevent zombie threads: store thread references in `self._active_thread`; if a thread is still alive when a new action is requested, show a status bar warning instead of launching a second thread.

---

### Task 2.4: Input Boundary Validation & Visual Alerts

**Files:** `app.py`  
**Scorecard Rating:** 41/10 (5/10 → 9/10)

**Current issue:** Invalid coordinates (latitudes > 90°), out-of-range years, and blank fields produce unhandled backend exceptions rather than user-friendly validation messages.

**Technical spec:**
- Define validation ranges: latitude `[-90.0, 90.0]`, longitude `[-180.0, 180.0]`, year `[100, 3000]`, hour `[0, 23]`, minute `[0, 59]`.
- On field change or before calculation: validate → if invalid, set field background to `#FFE0E0` (soft pink), display status bar message `"Invalid latitude — must be between -90 and +90"`, and block calculation.
- Valid fields restore to `XP_FIELD = "#FFFFFF"`.

---

## 5. Phase 3 — Multi-Agent AI Pipeline & Sutra RAG

**Objective:** Upgrade from a single generic LLM prompt to a verifiable, sequential multi-agent pipeline grounded in classical Sanskrit texts with psychological, non-fatalistic framing.

---

### Task 3.1: 5-Stage Sequential Agent Pipeline

**Files:** `prediction_engine.py`, `ollama_engine.py`  
**Scorecard Ratings:** 28/10 (1/10 → 8/10)

**Current issue:** A single compressed JSON prompt feeds the full chart into Ollama. Standard LLMs fail when analyzing a full birth chart at once — context clutter leads to generic output and hallucinated combinations.

**Technical spec (from `MULTI_AGENT_ARCHITECTURE.md`):**

```
1. ChartVerifier   →  Sanity-checks grahas dict (Rahu/Ketu opposition, lon range, retro consistency)
2. ThemeAnalyzer   →  Isolates specific house lords, aspects, and active dasha lords for the query
3. RemedialSolver  →  Applies functional-benefic filter; strips gemstones for dusthana lords
4. VoiceSynthesizer→  Synthesizes final counseling narrative (outcome-first, Sanskrit in parens)
5. SafetyCritic    →  Streaming regex/LLM filter; intercepts fatalistic keywords and reframes
```

- Create `agents/` directory with `verifier.py`, `analyzer.py`, `solver.py`, `voice.py`, `critic.py`, and `coordinator.py`.
- Each agent is a small class with a `run(context: dict) -> dict` interface.
- `coordinator.py` sequences them, passing the context dict between stages.
- The existing `OllamaEngine.stream()` is reused by each agent that needs LLM access.

---

### Task 3.2: Classical Sutra Citation Database

**Files:** `constants.py`, `prediction_engine.py`  
**Scorecard Rating:** 28/10 (1/10 → 7/10) — Embedded lightweight RAG

**Current issue:** LLM predictions are ungrounded — no reference to classical textual authority.

**Technical spec:**
- Create `data/sutras.json`: a structured dictionary mapping detected Yoga/Dosha keys to:
  - `source`: e.g., `"Brihat Parashara Hora Shastra, Ch. 34, v. 12"`
  - `devanagari`: Sanskrit verse in Unicode
  - `translation`: English translation
- When `vedic_engine.py` detects a Yoga/Dosha, the `ThemeAnalyzer` agent retrieves the matching sutra entry and injects the citation directly into the LLM context prompt.
- Start with the 50 most frequently detected Yogas and Doshas (Raja Yogas, Gaja Kesari, Kemadruma, Kaal Sarp, Mangal Dosha, etc.).

---

### Task 3.3: Minified JSON Token Schema

**Files:** `prediction_engine.py:29`  
**Scorecard Rating:** (Devil's Advocate 3.1)

**Current issue:** Verbose JSON keys (`"lagna_rashi"`, `"nak_lord"`, `"dignity"`) inflate the prompt. Over a 7B model context window on 8GB VRAM, this increases TTFT and limits output space.

**Technical spec:**
- Define a compression map in `constants.py`:
  ```python
  MINIFY_MAP = {
      "lagna_rashi": "lr", "nak_lord": "nl", "dignity": "d",
      "bhava": "b", "shadbala": "sb", "retro": "r", "rashi": "rs"
  }
  ```
- Apply the map in `PredictionEngine.chart_json()` before JSON serialization.
- Estimated token reduction: ~28–32% on the chart payload section.

---

### Task 3.4: Live Inference Diagnostic Strip

**Files:** `ui_widgets.py:80`, `app.py`, `ollama_engine.py`  
**Scorecard Rating:** 40/10 (6/10 → 8/10)

**Technical spec:**
- Record timestamps: `t_start` (prompt dispatch), `t_first_token` (first chunk received).
- Count tokens as they stream. On each chunk, update the XP status bar:  
  `[Model: qwen2.5:7b | TTFT: 480ms | 34.2 tok/s | 612 tokens]`
- Reset metrics display on each new generation request.

---

## 6. Phase 4 — Interactive UX & Windows XP Polish

**Objective:** Resolve DPI issues, fix streaming scroll behavior, and transform static chart graphics into interactive inspection surfaces.

---

### Task 4.1: Dynamic DPI & Font Scale Multiplier

**Files:** `main.py:48`, `ui_widgets.py`, `constants.py`  
**Scorecard Rating:** 17/10 (4/10 → 8/10)

**Current issue:** All font sizes and canvas coordinates are hardcoded to fixed pixel values designed for 96 DPI screens. On 4K/HiDPI displays where DPI scaling is disabled (to preserve Luna pixel lines), everything is tiny and unreadable.

**Technical spec:**
- Define `UI_SCALE = 1.0` as a user setting in `constants.py`.
- Replace all hardcoded font constructor calls with a factory:
  ```python
  def xp_font(base_size, weight="normal"): 
      return ("Tahoma", round(base_size * UI_SCALE), weight)
  ```
- Add a **View → Scale** menu: `100% (Native XP)` | `125% (HD)` | `150% (4K)`.
- Reconstruct widgets on scale change.

---

### Task 4.2: Interactive RashiChart Hover & Click Inspector

**Files:** `ui_widgets.py:325`  
**Scorecard Rating (implied):** UI/UX Audit 2.2

**Current issue:** Rashi chart houses display static Devanagari abbreviations with no hover context. Users unfamiliar with Devanagari cannot read the chart without prior knowledge.

**Technical spec:**
- Map each drawn house cell on the South Indian canvas to its rashi index via a tag (e.g., `f"cell_{rashi_idx}"`).
- Bind `<Enter>` and `<Motion>` events: detect which cell the cursor is over using tag search on canvas.
- Display an `XPTooltip` balloon showing:
  - House number, sidereal sign, sign lord
  - Occupying planets with exact degree, nakshatra pada, and dignity
- Bind `<Button-1>` to send signals to the educational glossary tab (Task 5.3).

---

### Task 4.3: Fix Streaming Chat Scroll Hijacking

**Files:** `app.py:1050`  
**Scorecard Rating (implied):** UI/UX Audit 3.1

**Current issue:** Every streamed token fires `self.chat.see("end")`, yanking the scroll position to the bottom even when the user has manually scrolled up to read earlier text.

**Technical spec:**
```python
# In _flush_render_buf():
_, ymax = self.chat.yview()
# Only auto-scroll if already anchored at the bottom
if ymax >= 0.98:
    self.chat.see("end")
```

---

### Task 4.4: Restore Windows XP Luna Color Scheme Switcher

**Files:** `constants.py`, `ui_widgets.py`  
**Scorecard Rating:** 39/10 (8/10 → 9/10)

**Technical spec:**
- Define three XP palette dicts in `constants.py`:
  - `THEME_LUNA_BLUE`: current default (`#0A246A`, `#D4D0C8`)
  - `THEME_HOMESTEAD`: Olive/green (`#3B5A2A`, `#D7DCD0`)
  - `THEME_METALLIC`: Silver (`#3D3D3D`, `#ECE9D8`)
- Expose via **View → Theme** menu with immediate UI repaint using `xp_style()` re-call.

---

## 7. Phase 5 — Trust, Consultation & Deliverables

**Objective:** Provide professional astrologers and clients with calculation transparency, interactive birth time rectification, and permanent exportable reports.

---

### Task 5.1: Interactive Birth Time Rectification Slider

**Files:** `app.py`, `astro_engine.py`  
**Betterment Proposal Idea 5**

**Current issue:** Birth times are rarely recorded precisely. A shift of even 5 minutes can change the entire Navamsa (D-9) ascending sign, which underpins divisional chart readings.

**Technical spec:**
- Add a collapsible "Rectification Panel" below the birth detail entry fields.
- A horizontal `ttk.Scale` slider, range `±15 minutes` in `10-second` increments.
- On drag: compute `adjusted_time = original_time + slider_offset`. Re-run `SweEngine.compute()` and refresh the D-1 and D-9 charts in real time (target: < 50ms round-trip).
- Highlight cells where the Ascendant sign changes (a cusp transition during slider movement).

---

### Task 5.2: "Calculation Proof" Mathematical Traceability Drawer

**Files:** `app.py`, `astro_engine.py`  
**Betterment Proposal Idea 3**

**Current issue:** There is no mechanism for an astrologer to verify the ephemeris computation from within the application, undermining professional credibility.

**Technical spec:**
- Add a collapsible "Proof" drawer at the bottom of the Birth Chart tab.
- Display the raw ephemeris telemetry returned by `SweEngine.compute()`:
  - Julian Day Number (UT1 and TDT)
  - Greenwich Mean Sidereal Time (GMST) and Local Sidereal Time (LST)
  - True Obliquity of the Ecliptic (ε)
  - Exact Lahiri Ayanamsa offset (degrees, arcminutes, arcseconds)
  - Porphyry cusp trisection intermediate values
- Return this metadata from `SweEngine.compute()` in a `"_proof"` sub-dict and store in `_meta`.

---

### Task 5.3: "THAT MEANs" Interactive Educational Glossary Tab

**Files:** `app.py`, `constants.py`  
**Betterment Proposal Idea 1**

**Current issue:** Vedic astrology uses deeply technical Sanskrit terminology (Navamsa, Ashtakavarga, Kemadruma) that is opaque to lay clients, eroding trust in the reading.

**Technical spec:**
- Create a new notebook tab: "Glossary / THAT MEANs".
- Build a lookup dictionary in `constants.py` mapping every Yoga name, Dosha name, planet name, house number, and dignity key to a plain-English psychological and practical life description.
- Clicking any element in the Rashi chart (`<Button-1>` from Task 4.2) focuses its matching entry in this tab, showing the Sanskrit term, English plain meaning, classical scriptural source, and practical life signification.

---

### Task 5.4: Audit-Ready Client Report Export

**Files:** New `report_generator.py`, `app.py`  
**Betterment Proposal Idea 6**

**Technical spec:**
- New module: `report_generator.py` — a pure-data template renderer (no Tkinter dependency).
- Generates a self-contained HTML file (openable in any browser, printable to PDF via browser print) containing:
  - Personal birth details header
  - Rashi (D-1) chart diagram (Canvas-to-SVG or Canvas-to-PNG via `PIL.ImageGrab`)
  - Navamsa (D-9) chart diagram
  - Full planetary positions and dignity table
  - 6-fold Shadbala summary (after Phase 1 completion)
  - Active Vimshottari Dasha timeline
  - Classical sutra citations for detected Yogas/Doshas
  - AI counseling narrative (non-fatalistic, with all safety filters applied)
- Add an "Export Report" button to the options menu. Uses `webbrowser.open()` to display the result.

---

## 8. Quality & Test Strategy

A new `tests/` directory should be established alongside the source files:

```
tests/
├── test_astro_engine.py     # Benchmark longitude/speed against known charts
├── test_vedic_engine.py     # Shadbala, Yoga, Dasha boundary calculations
├── test_resilience.py       # Geocache, thread safety, input validation
└── test_report_generator.py # HTML output structure verification
```

**Key test cases:**
- Compare planetary longitudes and speeds for a known benchmark horoscope (e.g., historical figure with verified birth data) against Swiss Ephemeris reference values.
- Assert True Node vs. Mean Node Ketu opposition: `abs(ketu_lon - rahu_lon - 180) < 0.001`.
- Verify polar latitude equal-house fallback triggers at `abs(lat) > 60`.
- Validate 6-fold Shadbala values for a standard chart against a BPHS manual computation.
- Assert thread safety: simulate double-click on "Generate Chart" and confirm only one thread runs.
- Test offline geocode fallback: mock network failure and confirm bundled city list is used.

---

## 9. Ponytail-Audit: Over-Engineering Findings

> **Scope:** Complexity and over-engineering only. Ranked largest potential cut first.
> Correctness bugs (e.g., incomplete Shadbala, hardcoded Ketu) are addressed in Phases 1–5, not here.
> **Status:** One-shot audit report. Nothing has been applied.

---

### Findings (ranked by cut size)

| # | Tag | What to Cut | Replacement | Location |
|:---|:---|:---|:---|:---|
| 1 | `shrink` | `draw_xp_gradient()` draws one pixel-wide `create_line` per pixel in a loop (up to 1260 iterations per gradient render). | Use Tkinter's built-in `PhotoImage` stipple or a 10-step coarse gradient — imperceptible visual difference, 10× fewer canvas objects. | `ui_widgets.py:68` |
| 2 | `shrink` | `deser_dt()` tries three date format strings in a loop with bare `except`. | `datetime.fromisoformat()` (Python 3.7+) handles all three variants natively. | `ui_widgets.py:503` |
| 3 | `yagni` | `_estimate_tokens()` is a single-expression function (`max(1, int(len(text) / 3.8))`). | Inline the expression at its two call sites in `_dynamic_ctx()`. Delete the wrapper. | `ollama_engine.py:32` |
| 4 | `yagni` | `_strip_markdown()` is a standalone module-level function imported nowhere outside its own file. | Inline into the only method that calls it, or collapse it to a one-liner with `re.sub` chain. | `ollama_engine.py:50` |
| 5 | `shrink` | `sort_treeview_col()` uses a nested `_key()` function with try/except for numeric coercion, called on each item separately. | `key=lambda t: (0, float(…)) if t.replace(…).isnumeric() else (1, t.lower())` — no nested function needed. | `ui_widgets.py:482` |
| 6 | `yagni` | `OllamaEngine.BASE` is a class attribute set to `OLLAMA_BASE_URL` from `constants.py`. Both exist; one is redundant. | Use `OLLAMA_BASE_URL` directly in all methods; remove `OllamaEngine.BASE`. | `ollama_engine.py:73` |
| 7 | `shrink` | `_hex_to_rgb()` and `_rgb_to_hex()` are two private module-level functions used only inside `draw_xp_gradient()`. | Inline both as one-liners inside `draw_xp_gradient()` or use Python's `bytes.fromhex()` and f-string directly. | `ui_widgets.py:61–66` |
| 8 | `yagni` | `ser_dt()` is `dt.strftime(fmt) if isinstance(dt, datetime) else str(dt)` — a one-liner function exported from `ui_widgets.py` and used in exactly one place in `app.py`. | Inline at the call site. Delete the wrapper. | `ui_widgets.py:501` |
| 9 | `shrink` | `_dynamic_ctx()` has a docstring larger than its actual logic body. | Drop the docstring to a single `# clamp ctx to VRAM budget` comment. | `ollama_engine.py:37` |
| 10 | `stdlib` | `Geocoder._last_call` / `_MIN_INTERVAL` class-level debouncing uses `time.sleep()` on a background thread, blocking it. | Use `threading.Event` with a timeout, or Python 3.12+ `time.sleep()` is fine — but the sleep on the geocoder thread is acceptable. The real fix is an async queue (Task 2.1 addresses this properly). | `ui_widgets.py:442` |
| 11 | `yagni` | `OllamaEngine._active_request_id` class attribute is set in `__init__` but never actually read or used anywhere in the class logic. | Delete the attribute. | `ollama_engine.py:74` |
| 12 | `shrink` | `PredictionEngine.chart_json()` builds `bhava_lords` using a dict comprehension over a `range(1, 13)` then converts integer keys to strings. | Build with string keys directly: `{str(h): RASHI_SWAMI[(lr+h-1)%12] for h in range(1,13)}` — already done, but the intermediate `int` step can be dropped. Minor cleanup. | `prediction_engine.py:94` |

**net: approximately −120 lines, −0 deps possible** (all standard library; no dependencies to remove). The codebase is lean on dependencies already. The wins are from removing thin wrapper functions, inline-able helpers, and the pixel-loop gradient renderer.

---

*End of Implementation Plan — v1.0*  
*Prepared for review before implementation begins.*
