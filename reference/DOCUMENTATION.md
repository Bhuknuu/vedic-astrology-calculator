# Vedic Astrology Calculator Developer Documentation

This document contains a comprehensive, function-by-function description of the modularized codebase in the [Astro_Best](file:///d:/Programs/Python/Astro/Astro_Best) directory. It explains what each function and class does, and the technical rationale for why it does it.

---

## 1. [main.py](file:///d:/Programs/Python/Astro/Astro_Best/main.py)

This file serves as the main entry point for the application. It handles initial window configuration, OS-level display adjustments, and boots the primary user interface.

### Functions

#### [main](file:///d:/Programs/Python/Astro/Astro_Best/main.py#L37)
* **What**: Initializes the Tkinter root window instance, sets the window title, and configures the geometry to 1260x860 centered on the screen. It also invokes the Windows DPI awareness API via `ctypes` as a fallback, instantiates the main application class [JyotishApp](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L85), and starts the main event loop.
* **Why**: Centering the window ensures a polished user experience upon launch. Disabling Windows DPI auto-scaling is necessary to keep the Windows XP Luna pixel grids and Tahoma fonts looking sharp and pixel-perfect, preventing fuzzy text or stretched borders on modern high-resolution displays.

---

## 2. [constants.py](file:///d:/Programs/Python/Astro/Astro_Best/constants.py)

This file contains all static data structures, translation tables, Sanskrit transliterations, astronomical constants, and UI configuration variables. It does not import other modules, making it safe to import anywhere.

### Configuration Constants

* **`TROPICAL_YEAR`**: Set to 365.24219 days. Used for planetary cycles (Vimshottari Dasha) to prevent coordinate drifts. A standard calendar year (365 or 365.25 days) causes Dasha transitions to drift by 15 to 20 days over a 60-year lifespan. Using the exact tropical year maintains alignment with classic texts.
* **Astrological Tables**: Contains definitions for signs (Rashi), Nakshatras, nakshatra lords, exaltation degrees (`UCHCHA_DEG`), debilitation degrees (`NEECHA_DEG`), swakshetra (own sign) indices, and moolatrikona limits. These parameters drive the core calculations of dignity and strength.
* **`FUNC_BENEFIC_BY_LAGNA`**: Maps functional benefic planets for each of the 12 ascendants. Used to safeguard gemstone recommendations (prescribing a gem for a functional malefic or dusthana lord can cause negative effects).
* **`ASHTAK_BINDUS`**: Implements the Brihat Parashara Hora Shastra rules for computing Ashtakavarga points. Defines which relative houses from the 8 contributors (7 planets and Lagna) award a bindu to a planet.
* **UI Palette Constants**: Hardcodes the hex color values for the Windows XP Luna theme (e.g. silver-gray background `#D4D0C8`, white field background `#FFFFFF`, deep navy `#0A246A`, and gradient colors).

---

## 3. [astro_engine.py](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py)

This module handles astronomical calculations for planetary positions and house boundaries. It uses `pyswisseph` as its primary engine, and automatically falls back to a custom, pure-math approximation if the library is not installed.

### Classes

#### [SweEngine](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L121)
* **What**: Encapsulates methods to query the Swiss Ephemeris package in Moshier mode, which runs locally without requiring external data files.
* **Why**: High-precision astronomical coordinates are essential for accurate chart generation. Moshier mode provides arcminute accuracy without adding file-loading dependencies.

#### [AstroEngine](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L224)
* **What**: A pure-Python fallback calculations engine. Approximates positions of the Sun, Moon, node, and 5 classical planets using Keplerian elements and basic orbit perturbations.
* **Why**: Guarantees that the software launches and operates basic calculations on systems lacking compiled C dependencies or unable to run `pyswisseph`.

### Functions

#### [_to_jd](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L61)
* **What**: Converts a Gregorian calendar date, local time, and timezone offset to a Julian Day in Universal Time.
* **Why**: Astronomical algorithms calculate orbits relative to Julian epochs (like J2000). Standardizing all input datetimes into a float index simplifies subsequent position queries.

#### [_bhava_from_cusps](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L76)
* **What**: Determines which house (1 to 12) a planetary longitude falls into based on a list of 12 unequal house cusps.
* **Why**: Under systems like Porphyry (Sripathi), house boundaries are unequal. Simply dividing the zodiac into 30-degree signs is insufficient; this checks the degree limits of each house, wrapping around 0 degrees when necessary.

#### [_enrich](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L98)
* **What**: Computes and adds Rashi indices, degrees, Nakshatras, nakshatra lords, padas, and bhava (house) numbers to a planet longitude dictionary.
* **Why**: Translates raw degrees (0-360) into standard Sanskrit astrological terms. It supports both Sripathi unequal house placements (when cusps are present) and whole-sign placements (when using fallback math).

#### [SweEngine.compute](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L134)
* **What**: Runs Swiss Ephemeris calculations. Sets the sidereal mode, retrieves the ayanamsa offset, calculates the coordinates of the 8 bodies (Sun through Rahu), determines Ketu (Rahu + 180 degrees), and calculates the 12 tropical house cusps using the Porphyry method (option `b"O"`), then subtracts the ayanamsa from all 12 cusps to yield sidereal boundaries.
* **Why**: Swiss Ephemeris operates natively in tropical coordinates. Sidereal calculations require setting the ayanamsa and subtracting it from all positions and cusps to yield accurate Vedic house boundaries. Porphyry matches the classical Sripathi house system.

#### [AstroEngine.jd_to_dt](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L231)
* **What**: Converts a Julian Day value back to a standard Python `datetime` object.
* **Why**: Used to convert the start and end moments of Vimshottari Dasha intervals back to human-readable dates.

#### [AstroEngine._lahiri](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L245)
* **What**: Approximates the Lahiri ayanamsa offset for a given Julian Day based on time elapsed since the J2000 epoch.
* **Why**: Essential for applying the sidereal correction in pure-math fallback mode.

#### [AstroEngine._obliquity](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L250)
* **What**: Computes the obliquity of the ecliptic (tilt of Earth's axis) for a given Julian epoch.
* **Why**: Obliquity is required to geometrically convert equatorial coordinate components (sidereal time) into ecliptic coordinates (used for calculating the ascendant).

#### [AstroEngine._sun_lon](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L256)
* **What**: Computes the Sun's tropical longitude using mean anomaly and basic ellipse equations.
* **Why**: Fallback solar position source.

#### [AstroEngine._moon_lon](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L268)
* **What**: Calculates the Moon's longitude using a simplified lunar theory with 36 periodic perturbation terms.
* **Why**: The Moon's position must be calculated carefully because it dictates Nakshatra placement, which in turn determines the Vimshottari Dasha lifecycle.

#### [AstroEngine._kepler](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L301)
* **What**: Solves Kepler's Equation for eccentric anomaly given mean anomaly and eccentricity using Newton-Raphson iterations.
* **Why**: Orbits are elliptical, not circular; solving this transcendental equation is necessary to obtain coordinates along the ellipse.

#### [AstroEngine._planet_lon](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L312)
* **What**: Computes heliocentric coordinates for a planet (Mercury, Venus, Earth, Mars, Jupiter, or Saturn), projects them to geocentric coordinates, and corrects for light-travel delay.
* **Why**: Fallback calculations.

#### [AstroEngine._rahu_lon](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L357)
* **What**: Approximates the longitude of the mean ascending node (Rahu).
* **Why**: Fallback node calculation.

#### [AstroEngine._lagna](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L362)
* **What**: Calculates the ascendant (Lagna) degree geometrically based on Greenwich Mean Sidereal Time (GMST), longitude, latitude, and obliquity.
* **Why**: The ascendant marks the eastern horizon at the time of birth, establishing the base coordinate for the entire house system.

#### [AstroEngine.compute](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L381)
* **What**: Computes positions for all bodies. Calculates planet speed numerically by comparing coordinates at `jd - 1` and `jd + 1`.
* **Why**: Direct calculations do not yield analytical speed vectors in fallback mode; numerical differentiation provides a simple, accurate alternative.

#### [compute_chart](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L427)
* **What**: Dispatches calculations to `SweEngine` if `pyswisseph` was loaded successfully, or defaults to `AstroEngine` if not. Supports `node_type="Mean"|"True"` and `iana_tz` for automatic DST resolution.
* **Why**: Decouples the frontend from backend package status, ensuring the application remains functional.

#### [resolve_timezone](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py)
* **What**: Resolves historical decimal UTC offset, daylight saving status (`is_dst`), and timezone abbreviation using standard library `zoneinfo`.
* **Why**: Eliminates manual DST entry errors which can shift the Ascendant by ~15°.

#### [compute_transits](file:///d:/Programs/Python/Astro/Astro_Best/astro_engine.py#L437)
* **What**: Computes the coordinates of all bodies for the current UTC moment.
* **Why**: Feeds live transit coordinates to the Gochara tab overlay.

---

## 4. [vedic_engine.py](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py)

This module implements the core interpretive math of Vedic astrology: dignity levels, divisional charts, Vimshottari periods, Yogas, Doshas, Shadbala component scores, and Ashtakavarga bindus.

### Functions

#### [sthiti](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py#L34)
* **What**: Determines planetary dignity (Uchcha, Neecha, Moolatrikona, Swakshetra, Mitra, Shatru, Sama).
* **Why**: Exaltation, debilitation, and planetary friendships influence how planets express their characteristics in a reading. Rahu and Ketu are included using classical exaltation degrees.

#### [navamsa](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py#L59)
* **What**: Computes the Rashi index (0-11) of the Navamsa (D-9) divisional chart.
* **Why**: The Navamsa is the most critical sub-divisional chart, representing the inner potential, dharma, and marriage of the native.

#### [varga](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py#L66)
* **What**: Calculates the sign index for divisional charts D-1 through D-60. Supports `return_boundary=True` for boundary alerts.
* **Why**: Divisional charts analyze specific life areas (e.g. D-10 for career, D-24 for education, D-30 for health/obstacles).

#### [check_varga_boundary / compute_varga_chart](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py)
* **What**: Flags planets sitting within ±0.05° of a divisional chart sign cusp and generates complete divisional charts with relative bhavas.
* **Why**: High-harmonic charts like D-60 change signs with a few seconds of birth time; flagging boundaries warns practitioners of calculation sensitivity.

#### [vimshottari](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py#L105)
* **What**: Calculates the chronological sequence of Mahadashas and Antardashas, supporting nesting depths up to Level 4 (Pratyantardasha and Sookshmadasha).
* **Why**: Vimshottari Dasha is the primary system for timing events in Vedic astrology, showing when planetary periods are active. The time delta is calculated using the customizable year length (tropical solar year by default) to prevent calendar drift.

#### [compute_pratyantardasha_for_ad](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py)
* **What**: Expands any selected Antardasha into its 9 Pratyantardashas (and optional Sookshmadashas) on-demand.
* **Why**: Enables instantaneous UI drill-down without calculating a memory-heavy full multi-thousand row tree up-front.

#### [yoga](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py#L156)
* **What**: Checks for configurations like Gaja Kesari, Pancha Mahapurusha, Raja Yoga, Dhana Yoga, Budha-Aditya, Chandra-Mangal, Saraswati, Viparita Raja, and Neechabhanga.
* **Why**: Yogas indicate significant life accomplishments, talents, and turnarounds.

#### [_func_benefic_for_lagna](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py#L301)
* **What**: Returns functional benefics list.
* **Why**: Mapped to ascendants to avoid harmful gemstone suggestions.

#### [_remedy_for](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py#L305)
* **What**: Validates remedies, substituting gemstones with mantras if the planet is a functional malefic.
* **Why**: Recommending gems for harmful planets is counter-productive.

#### [dosha](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py#L318)
* **What**: Detects Mangal Dosha, Kaal Sarp Dosha, Kemadruma Dosha, and Graha Yuddha.
* **Why**: Doshas indicate critical challenges and karma.

#### [shadbala](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py#L443)
* **What**: Calculates complete 6-fold Shadbala: Sthana Bala (Uchcha, Ojhayugmarashi, Drekkana, Kendradi), Cheshta Bala, Naisargika Bala, Drik Bala (mutual benefic/malefic aspects), and Ayana Bala (declination-based strength via Swiss Ephemeris).
* **Why**: Provides authentic classical planetary strength per BPHS without misleading partial totals.

#### [panchanga](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py)
* **What**: Calculates the 5 classical limbs of Vedic time: Tithi (with paksha and elapsed percentage), Vara (weekday and ruler), Nakshatra (mansion, pada, ruler), Nitya Yoga (solilunar combination and nature), and Karana (half-tithi, highlighting Vishti/Bhadra).
* **Why**: Core requirement for muhurta timing and daily energetic quality assessment.

#### [gemstone_prescription](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py)
* **What**: Prescribes gemstones with weight calculation based on body weight, metal, finger, day, and consecration mantra; automatically contraindicates gems for functional malefics of the native's Lagna.
* **Why**: Prevents contraindicated gemstone recommendations and provides safe remedial alternatives (japa, charity).

#### [ashtakavarga](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py#L506)
* **What**: Calculates 12-sign Ashtakavarga bindu distribution.
* **Why**: Shows how planets influence signs natally and in transit.

#### [sarvashtakavarga](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py#L538)
* **What**: Sums the 7 planet AVs.
* **Why**: Shows the total energy index of each sign.

#### [format_dasha_balance](file:///d:/Programs/Python/Astro/Astro_Best/vedic_engine.py#L554)
* **What**: Renders the remaining dasha balance at birth.
* **Why**: Essential detail for birth time rectification.

---

## 5. [ollama_engine.py](file:///d:/Programs/Python/Astro/Astro_Best/ollama_engine.py)

This file integrates the local Ollama service for running offline AI interpretations.

### Classes

#### [OllamaEngine](file:///d:/Programs/Python/Astro/Astro_Best/ollama_engine.py#L66)
* **What**: Discovers models, manages server-side cancellations, and streams token-by-token generation.

### Functions

#### [_estimate_tokens](file:///d:/Programs/Python/Astro/Astro_Best/ollama_engine.py#L32)
* **What**: Estimates token count from text length.
* **Why**: Used to size context windows.

#### [_dynamic_ctx](file:///d:/Programs/Python/Astro/Astro_Best/ollama_engine.py#L37)
* **What**: Computes optimal context size (`num_ctx`).
* **Why**: Prevents overallocating GPU VRAM.

#### [_strip_markdown](file:///d:/Programs/Python/Astro/Astro_Best/ollama_engine.py#L50)
* **What**: Strips markdown syntax from incoming tokens.
* **Why**: Keeps text clean for Tkinter display.

#### [OllamaEngine.ping](file:///d:/Programs/Python/Astro/Astro_Best/ollama_engine.py#L77)
* **What**: Checks if Ollama service is reachable.
* **Why**: Discovers backend status.

#### [OllamaEngine.list_models](file:///d:/Programs/Python/Astro/Astro_Best/ollama_engine.py#L87)
* **What**: Lists installed Ollama models.
* **Why**: Allows user to select available models.

#### [OllamaEngine.request_stop](file:///d:/Programs/Python/Astro/Astro_Best/ollama_engine.py#L98)
* **What**: Sends `DELETE` request to abort generation.
* **Why**: Immediately halts server processing and frees the GPU.

#### [OllamaEngine.generate_stream](file:///d:/Programs/Python/Astro/Astro_Best/ollama_engine.py#L121)
* **What**: Streams generation via `POST` request.
* **Why**: Powers real-time AI responses.

---

## 6. [prediction_engine.py](file:///d:/Programs/Python/Astro/Astro_Best/prediction_engine.py)

This file serializes chart data into minified JSON and builds LLM prompts.

### Classes

#### [PredictionEngine](file:///d:/Programs/Python/Astro/Astro_Best/prediction_engine.py#L26)
* **What**: Builds prompts and serializes details.

### Functions

#### [chart_json](file:///d:/Programs/Python/Astro/Astro_Best/prediction_engine.py#L29)
* **What**: Creates a minified JSON representation of birth details, planet attributes, yogas, doshas, and active dashas.
* **Why**: Saves ~40% tokens compared to full texts, maximizing inference speed.

#### [chart_text_full](file:///d:/Programs/Python/Astro/Astro_Best/prediction_engine.py#L118)
* **What**: Formats verbose chart details.
* **Why**: Displays details in UI and saves into files.

#### [system_prompt](file:///d:/Programs/Python/Astro/Astro_Best/prediction_engine.py#L201)
* **What**: Returns system instructions for the LLM.
* **Why**: Enforces safe predictions (no fatalistic death claims) and defines bulleted output rules.

#### [user_prompt_full](file:///d:/Programs/Python/Astro/Astro_Best/prediction_engine.py#L257)
* **What**: Prompts full reading.
* **Why**: Defines reading sections.

#### [user_prompt_qa](file:///d:/Programs/Python/Astro/Astro_Best/prediction_engine.py#L276)
* **What**: Prompts answering a user question.
* **Why**: Answers queries specifically.

---

## 7. [ui_widgets.py](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py)

This file implements custom Windows XP Luna styling and widgets (status bar, tooltips, chart canvas, geocoder).

### Classes

#### [XPGradientHeader](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L87)
* **What**: Renders Luna deep blue gradient header.
* **Why**: Hallmark of XP style.

#### [XPStatusBar](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L132)
* **What**: Explorer-style status bar with panels.
* **Why**: Shows distinct status information.

#### [XPTooltip](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L168)
* **What**: Yellow hover tooltip.
* **Why**: Describes controls on hover.

#### [RashiChart](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L325)
* **What**: South-Indian style rashi chart canvas. Overlays transits and flags retrogrades.
* **Why**: Visual chart representation.

#### [Geocoder](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L442)
* **What**: Geocodes city names with debouncing and rate-limit handling.
* **Why**: Prevents IP bans on OpenStreetMap.

### Functions

#### [_resolve_devanagari_font](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L40)
* **What**: Selects installed Devanagari font.
* **Why**: Displays Sanskrit terms correctly.

#### [ensure_utf8_stdout](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L50)
* **What**: Reconfigures console stdout to UTF-8.
* **Why**: Prevents Windows crash when printing unicode.

#### [_hex_to_rgb](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L61), [_rgb_to_hex](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L65)
* **What**: Color format conversions.

#### [draw_xp_gradient](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L68)
* **What**: Renders step-by-step horizontal gradient.
* **Why**: Used in gradient headers.

#### [xp_style](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L211)
* **What**: Configures clam theme styles for Tkinter.
* **Why**: Implements Windows XP look.

#### [titled_frame](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L295)
* **What**: Groove frame with blue header.
* **Why**: Used to group large UI sections.

#### [xp_labelframe](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L312)
* **What**: LabelFrame with blue Tahoma font.
* **Why**: Classic grouping style.

#### [sort_treeview_col](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L482)
* **What**: Sorts Treeview columns.
* **Why**: Makes data tables sortable.

#### [ser_dt](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L501), [deser_dt](file:///d:/Programs/Python/Astro/Astro_Best/ui_widgets.py#L503)
* **What**: Date string helpers.

---

## 8. [app.py](file:///d:/Programs/Python/Astro/Astro_Best/app.py)

This file contains the core Tkinter application orchestrator. Configures layouts, inputs, triggers background calculations, streams LLM predictions, and handles files.

### Classes

#### [JyotishApp](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L85)
* **What**: Main application window orchestrator.

### Functions

#### [__init__](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L87)
* **What**: Initializes variables, builds widgets, sets window size, starts checking Ollama.
* **Why**: Entry initialization.

#### [_bind_shortcuts](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L129)
* **What**: Binds keyboard commands (Ctrl+G, Ctrl+S, Ctrl+L, F5).
* **Why**: Keyboard navigation.

#### [_build](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L141)
* **What**: Lays out panels, gradient header, status bar, and tabs.
* **Why**: Main layout setup.

#### Tabs setup methods: [_tab_rashi](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L297), [_tab_graha](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L311), [_tab_varga](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L329), [_tab_dasha](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L352), [_tab_yoga](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L385), [_tab_shadbala](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L417), [_tab_chalit](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L438), [_tab_ashtak](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L477), [_tab_gochara](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L511), [_tab_phaladesh](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L547).
* **What**: Build corresponding tabs.
* **Why**: Tabs setup.

#### [_configure_chat_tags](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L609)
* **What**: Sets up formatting colors and fonts for chat.
* **Why**: Chat readability.

#### [_check_ollama_bg](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L620)
* **What**: Background thread that pings Ollama and queries models.
* **Why**: Non-blocking service discovery.

#### [_apply_ollama_status](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L625)
* **What**: Updates connection dot, status text, and setups frame.
* **Why**: Visual status feedback.

#### [_chat_add](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L648)
* **What**: Inserts text in chat log.
* **Why**: Safely appends from thread.

#### [_clear_chat](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L656)
* **What**: Clears chat history.

#### [_set_streaming](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L660)
* **What**: Toggles streaming indicators and buttons.
* **Why**: Visual state update.

#### [_stop_generation](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L665)
* **What**: Cancels LLM generation.
* **Why**: Frees local GPU resource.

#### [_on_chat_enter](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L670)
* **What**: Triggers sending text when Return is pressed.
* **Why**: Convenience.

#### [_lookup_geo](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L677)
* **What**: Runs geocoder in background.
* **Why**: Non-blocking geocoding.

#### [_flash_geo_ok](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L692)
* **What**: Temporarily flashes "✓ Found".
* **Why**: Clear verification feedback.

#### [_calculate](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L699)
* **What**: Extracts inputs, runs position math, calculates yogas/doshas/dashas, refreshes UI.
* **Why**: Main generation logic.

#### [_refresh_all](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L757)
* **What**: Triggers sequential tab refreshes with small delays.
* **Why**: Avoids freezing UI thread.

#### Tab refresh implementations: [_upd_info](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L764), [_upd_grahas](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L813), [_upd_dasha](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L832), [_on_md_sel](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L844), [_upd_yoga](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L860), [_upd_shadbala](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L883), [_upd_chalit](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L899), [_upd_ashtak](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L938).
* **What**: Populate tables and canvas coordinates with calculated values.
* **Why**: Displays birth chart details.

#### [_show_ashtak](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L943)
* **What**: Recalculates and populates Ashtakavarga table.
* **Why**: Swaps between planets.

#### [_show_varga](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L974)
* **What**: Recalculates and displays divisional chart.
* **Why**: Swaps between vargas.

#### [_refresh_transits](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L1003)
* **What**: Computes live planetary transits.
* **Why**: Live Gochara analysis.

#### [_upd_transit_display](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L1013)
* **What**: Renders transit overlay and transit notes.
* **Why**: Visual transit feedback.

#### [_flush_render_buf](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L1058)
* **What**: Renders text formatting on bold `**text**` matches.
* **Why**: Renders bold text in chat log.

#### [_flush_remaining_buf](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L1078)
* **What**: Flushes leftover buffer.

#### [_run_generation](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L1086)
* **What**: Performs streaming inference.
* **Why**: Background inference process.

#### [_remove_thinking_marker](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L1114)
* **What**: Removes loading indicator.

#### [_auto_analyse](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L1224)
* **What**: Triggers complete reading.

#### [_send](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L1129)
* **What**: Sends question.

#### [_save_kundali](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L1140)
* **What**: Serializes and writes `.jyotish` chart file.
* **Why**: Export charts.

#### [_load_kundali](file:///d:/Programs/Python/Astro/Astro_Best/app.py#L1169)
* **What**: Reads, parses, and populates `.jyotish` files.
* **Why**: Import charts.
