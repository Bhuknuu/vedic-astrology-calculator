# Changelog — Vedic Astrology Calculator

All notable changes, mathematical implementations, and architectural refactorings are documented here.
Format conforms to [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [v6.0.0] - Core Astrometry & Mathematical Integrity Upgrade

### Added

#### 1. Full Classical 6-Fold Shadbala Engine (`core/vedic_engine.py`)
- **Drik Bala (Aspect Strength):** Computes precise angular aspect virupas between all 7 planets. Incorporates Parashari special full aspects (Mars: 4th, 7th, 8th; Jupiter: 5th, 7th, 9th; Saturn: 3rd, 7th, 10th; all other planets: 7th only). Natural benefics (Jupiter, Venus, Mercury, waxing Moon) provide positive virupas; natural malefics (Saturn, Mars, Sun, waning Moon) provide negative virupas.
- **Ayana Bala (Solstitial Strength):** Computes planetary declination ($\delta$) using Swiss Ephemeris equatorial sidereal flag (`swe.FLG_EQUATORIAL | swe.FLG_SIDEREAL`). Evaluates score against the obliquity of the ecliptic ($\varepsilon \approx 23.44^\circ$).
- **Sthana Bala (Positional Strength):** Full 5-component breakdown:
  - *Uchcha Bala:* Exaltation/debilitation distance proportional scoring.
  - *Ojhayugmarashi Bala:* Odd/even sign placement scoring for masculine/feminine planets.
  - *Drekkana Bala:* Decanate placement dignity (1st/2nd/3rd decanate lordship).
  - *Kendradi Bala:* Quadrant (Kendra: 60 virupas), succedent (Panaphara: 30 virupas), and cadent (Apoklima: 15 virupas) scoring.
  - *Saptavargaja Bala:* Multi-divisional chart dignity aggregate.
- **6-Fold Total:** `shadbala()` returns authentic aggregate of Sthana, Dig, Kala, Chesta, Naisargika, and Drik bala, eliminating deceptive partial totals.

#### 2. Lunar True Nodes & Independent Ketu Vector (`core/astro_engine.py`)
- Added `node_type` toggle (`"true"` vs `"mean"`) defaulting to True Node calculation via `swe.TRUE_NODE`.
- Implemented independent velocity calculation for Ketu directly from orbital mechanics instead of cloning Rahu's speed vector.
- Supported True Node forward oscillation detection (temporary direct motion states).

#### 3. 4-State Stationary Planetary Motion Detection (`core/astro_engine.py`, `core/constants.py`)
- Added `STATIONARY_SPD_DEG = 0.001` threshold.
- Enhanced motion states beyond binary direct/retrograde:
  - `stationary_direct`: Planet transitioning from retrograde to direct motion ($\le 0.001^\circ$/day with positive acceleration).
  - `stationary_retrograde`: Planet transitioning from direct to retrograde motion ($\le 0.001^\circ$/day with negative acceleration).
  - `direct` / `retrograde`.

#### 4. High-Latitude Polar Quadrant Protection (`core/astro_engine.py`)
- Added `POLAR_LATITUDE_THRESHOLD = 60.0`.
- Implemented `equal_house_polar_fallback()`: Automatically intercepts calculations where $|\text{latitude}| \ge 60^\circ$ or where Porphyry cusp calculation fails due to arctic quadrant collapse. Fallback constructs equal $30^\circ$ houses anchored to the Ascendant longitude, logging defensive warnings.

#### 5. Deep Vimshottari Dasha Hierarchy (Levels 3 & 4) (`core/vedic_engine.py`)
- Added `depth` parameter (1 to 4) to `vimshottari()`.
- Implemented `compute_pratyantardasha_for_ad()` to support Pratyantardasha (sub-sub periods) and Sookshmadasha (sub-sub-sub periods) with proportional year subdivision based on the tropical year constant ($365.24219\text{ days}$).

#### 6. Divisional Chart Boundary Proximity Warnings (`core/vedic_engine.py`, `core/constants.py`)
- Added `BOUNDARY_THRESHOLD = 0.05` ($3'$ of arc).
- `varga()` now supports `return_boundary=True`, computing distance to varga sign boundary in degrees and flagging `near_boundary` status.
- Added `compute_varga_chart()` generating complete D-chart planetary placements with boundary proximity diagnostics for birth time rectification.

#### 7. Classical Panchanga Engine (`core/vedic_engine.py`, `core/constants.py`)
- Implemented `panchanga()` computing the 5 classical limbs of time:
  1. **Tithi (Lunar Day):** Angular elongation between Sun and Moon ($(\lambda_{\text{Moon}} - \lambda_{\text{Sun}}) \div 12^\circ$), Shukla/Krishna paksha, elapsed/remaining percentages.
  2. **Vara (Solar Weekday):** Standardized Vedic weekday index and Sanskrit name.
  3. **Nakshatra:** Lunar mansion (0–26), Pada (1–4), and ruling lord.
  4. **Nitya Yoga:** Solar-lunar angular sum ($(\lambda_{\text{Sun}} + \lambda_{\text{Moon}}) \div 13^\circ 20'$).
  5. **Karana:** Half-tithi calculation covering the 7 repeating movable karanas and 4 fixed classical karanas.

#### 8. Gemstone Prescription Specifications & BPHS Safety Filter (`core/vedic_engine.py`, `core/constants.py`)
- Added comprehensive classical gemstone reference table `GEMSTONE_SPECS` covering:
  - Primary gems (Ruby, Pearl, Red Coral, Emerald, Yellow Sapphire, Diamond, Blue Sapphire, Hessonite, Cat's Eye).
  - Authentic substitutes (Uparatnas).
  - Minimum weights in Ratti / carats.
  - Recommended setting metals, fingers, wearing days, and muhurta hours.
- Implemented `gemstone_prescription()` enforcing the *Brihat Parashara Hora Shastra* safety rule:
  - Automatically identifies functional benefics (`FUNC_BENEFIC_BY_LAGNA`) and functional malefics for the given Ascendant.
  - Explicitly flags and warns against prescribing gemstones for functional malefics, maraka lords, or dusthana (6th, 8th, 12th) rulers to prevent adverse planetary reinforcement.

#### 9. Historical Timezone & DST Auto-Resolver (`core/astro_engine.py`)
- Added `resolve_timezone()` leveraging standard Python `zoneinfo.ZoneInfo`.
- Accurately converts historical local civil dates to UTC across daylight saving transitions and historical timezone shifts without external network dependencies.
- Integrated `iana_tz` parameter into `compute_chart()`.

#### 10. Turnkey Environment Setup (`setup.sh`)
- Automated script to establish `.venv`, install `pyswisseph`, verify `python3-tk`, and scaffold local Ollama Modelfile.

---

### Changed & Fixed

- **UI/Tkinter PanedWindow Bug Fix (`ui/app.py`):** Resolved application crashes caused by invalid `stretch="always"` keyword argument on Tkinter `PanedWindow.add()`.
- **False Title & Minimalist Branding (`ui/app.py`):** Removed false marketing titles (`Qwen2.5-7B offline AI`) from the main window header and status labels, replacing them with clean minimalist metadata (`Vedic Astrology Calculator v6.0 · Offline`).
- **Ayanamsa Precision (`core/astro_engine.py`):** Added explicit support for standard ayanamsa keys (`lahiri`, `raman`, `krishnamurti`, `fagan_bradley`).
- **Test Suite Modernization (`tests/test_core.py`):** Added 14 unit test suites verifying all newly implemented astronomical and astrological calculations.
