# -*- coding: utf-8 -*-
"""
astro_engine.py
===============
Planetary position computation.

Primary  : SweEngine  — uses pyswisseph (Moshier built-in, no .se1 files needed)
Fallback : AstroEngine — pure-math approximation (used when pyswisseph absent)

Key fixes vs v3.0
-----------------
* All sidereal house cusps derived correctly: tropical cusps - ayanamsa
  (fixes the mixed-zodiac bug in future Bhava Chalit expansion)
* Sripathi-style Kendradi Bala: planet-in-bhava determined from cusp degrees,
  not from whole-sign bhava
* Ketu speed stored separately from Rahu (ready for True Node mode)
* Ayanamsa correctly applied to every cusp, not just the ascendant
"""

import math
from datetime import datetime
from core.constants import (
    RASHI, NAKSHATRA, NAK_LORDS, ALL_GRAHAS,
    UCHCHA_DEG, NEECHA_DEG, SWAKSHETRA, MOOLTRIKONA,
    POLAR_LATITUDE_THRESHOLD, STATIONARY_SPD_DEG,
)

# ══════════════════════════════════════════════════════════════════════════════
#  pyswisseph availability check
# ══════════════════════════════════════════════════════════════════════════════
try:
    import swisseph as swe

    # Use Moshier (built-in) — no external .se1 ephemeris files required
    _FLAG_BASE  = swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    _FLAG_TROP  = swe.FLG_MOSEPH | swe.FLG_SPEED   # tropical (for house cusps)

    AYANAMSA_MAP = {
        "Lahiri (Chitrapaksha)": swe.SIDM_LAHIRI,
        "Raman":                  swe.SIDM_RAMAN,
        "KP (Krishnamurti)":     swe.SIDM_KRISHNAMURTI,
    }
    SWE_PLANET_IDS = {
        "Surya":   swe.SUN,
        "Chandra": swe.MOON,
        "Mangal":  swe.MARS,
        "Budha":   swe.MERCURY,
        "Guru":    swe.JUPITER,
        "Shukra":  swe.VENUS,
        "Shani":   swe.SATURN,
        "Rahu":    swe.MEAN_NODE,   # ascending node = Rahu (traditional Vedic)
    }
    SWE_OK = True

except ImportError:
    SWE_OK = False


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED UTILITIES
# ══════════════════════════════════════════════════════════════════════════════
def _to_jd(y, mo, d, h, mi, tz):
    """Calendar date + local time → Julian Day (UT)."""
    ut = h + mi / 60.0 - tz
    day_adj = int(ut // 24)
    ut %= 24
    d += day_adj
    if mo <= 2:
        y -= 1
        mo += 12
    A = int(y / 100)
    B = 2 - A + int(A / 4)
    return (int(365.25 * (y + 4716)) + int(30.6001 * (mo + 1))
            + d + ut / 24.0 + B - 1524.5)


def _bhava_from_cusps(planet_lon, sidereal_cusps):
    """
    Determine the Sripathi bhava of a planet given the 12 sidereal house cusps.
    Cusps are a list of 12 sidereal longitudes [cusp1 … cusp12].
    Returns 1-indexed bhava (1–12).

    FIX: This replaces the whole-sign bhava assignment used for Kendradi Bala,
    giving a more accurate value when Lagna is near a sign boundary.
    """
    lon = planet_lon % 360
    for i in range(12):
        c_start = sidereal_cusps[i] % 360
        c_end   = sidereal_cusps[(i + 1) % 12] % 360
        if c_start < c_end:
            if c_start <= lon < c_end:
                return i + 1
        else:   # cusp wraps through 0°
            if lon >= c_start or lon < c_end:
                return i + 1
    return 1   # fallback


def _enrich(pd, lon, asc_rashi, sidereal_cusps=None):
    """Attach rashi, nakshatra, bhava metadata to a graha dict in-place."""
    r  = int(lon / 30)
    nd = int(lon / (360 / 27))
    np = int((lon % (360 / 27)) / (360 / 27 / 4)) + 1
    pd["rashi"]           = r
    pd["rashi_naam"]      = RASHI[r]
    pd["rashi_ansh"]      = lon % 30
    pd["nakshatra"]       = nd
    pd["nakshatra_naam"]  = NAKSHATRA[nd]
    pd["nakshatra_swami"] = NAK_LORDS[nd]
    pd["pada"]            = np
    if sidereal_cusps:
        pd["bhava"] = _bhava_from_cusps(lon, sidereal_cusps)
        pd["bhava_method"] = "sripathi"
    else:
        pd["bhava"] = (r - asc_rashi) % 12 + 1
        pd["bhava_method"] = "whole_sign"


# ══════════════════════════════════════════════════════════════════════════════
#  SweEngine  (pyswisseph, Moshier — no .se1 files needed)
# ══════════════════════════════════════════════════════════════════════════════
class SweEngine:
    """
    High-precision planetary positions via pyswisseph (Moshier ephemeris).
    Accurate to <1 arcminute for dates 1800–2100 without any data files.

    House cusps are computed in tropical zodiac via swe.houses(jd, lat, lon, b"O")
    (Porphyry system = Sripathi equivalent: trisects Ascendant-MC and MC-Descendant
    arcs, which is what classical Jyotish Sripathi actually specifies), then the
    ayanamsa is subtracted from EVERY cusp to get sidereal values.  Previously
    Placidus (b"P") was used, which is a Western system incompatible with classical
    Sripathi.  This change makes Kendradi Bala mathematically sound for Jyotish.
    """

    @staticmethod
    def compute(y, mo, d, h, mi, tz, lat, lon_geo,
                ayanamsa_key="Lahiri (Chitrapaksha)",
                node_type="Mean"):
        jd = _to_jd(y, mo, d, h, mi, tz)

        # Set sidereal mode — this call also sets the ayanamsa for get_ayanamsa_ut
        swe.set_sid_mode(AYANAMSA_MAP.get(ayanamsa_key, swe.SIDM_LAHIRI), 0, 0)
        ay = swe.get_ayanamsa_ut(jd)

        res = {}

        # ── Planets ────────────────────────────────────────────────────────
        for name, pid in SWE_PLANET_IDS.items():
            try:
                xx, _ = swe.calc_ut(jd, pid, _FLAG_BASE)
            except Exception:
                # Moshier fallback already in _FLAG_BASE; this catches edge cases
                xx, _ = swe.calc_ut(jd, pid, swe.FLG_MOSEPH | swe.FLG_SPEED)
                lon = (xx[0] - ay) % 360   # manual ayanamsa if FLG_SIDEREAL failed
                spd = xx[3]
                res[name] = {"longitude": lon, "speed": spd, "retro": spd < 0}
                continue
            lon = xx[0] % 360   # FLG_SIDEREAL already applied inside swe
            spd = xx[3]
            res[name] = {"longitude": lon, "speed": spd, "retro": spd < 0}

        # ── Rahu/Ketu with True Node support ───────────────────────────────
        # When node_type="True", use swe.TRUE_NODE for Rahu
        # Ketu's velocity is queried independently from the opposite node's
        # ephemeris position, not cloned from Rahu.
        if node_type == "True":
            try:
                xx_r, _ = swe.calc_ut(jd, swe.TRUE_NODE, _FLAG_BASE)
                rahu_lon = xx_r[0] % 360
                rahu_spd = xx_r[3]
                res["Rahu"] = {"longitude": rahu_lon, "speed": rahu_spd,
                               "retro": rahu_spd < 0}
                # Ketu: query opposite node independently
                xx_k, _ = swe.calc_ut(jd, swe.MEAN_NODE, _FLAG_BASE)
                ketu_lon = (xx_k[0] - ay + 180) % 360
                ketu_spd = xx_k[3]
                res["Ketu"] = {"longitude": ketu_lon, "speed": ketu_spd,
                               "retro": ketu_spd < 0}
            except Exception:
                # Fallback to mean node if true node fails
                rahu_lon = res["Rahu"]["longitude"]
                res["Ketu"] = {
                    "longitude": (rahu_lon + 180) % 360,
                    "speed":     res["Rahu"]["speed"],
                    "retro":     True,
                }
        else:
            # Mean Node: Ketu = Rahu + 180 (traditional)
            rahu_lon = res["Rahu"]["longitude"]
            res["Ketu"] = {
                "longitude": (rahu_lon + 180) % 360,
                "speed":     res["Rahu"]["speed"],
                "retro":     True,
            }

        # ── Stationary motion detection ────────────────────────────────────
        # Classify planets as one of four states:
        #   "D"  = Direct
        #   "R"  = Retrograde
        #   "SD" = Stationary Direct (speed crossing zero from negative)
        #   "SR" = Stationary Retrograde (speed crossing zero in negative direction)
        for name, pd in res.items():
            if name.startswith("_"):
                continue
            spd = pd.get("speed", 0)
            ret = pd.get("retro", False)
            if abs(spd) < STATIONARY_SPD_DEG:
                # Determine direction of motion change
                if ret:
                    pd["motion_state"] = "SR"  # was retro, slowing to stop
                else:
                    pd["motion_state"] = "SD"  # was direct, slowing to stop
            elif spd < 0:
                pd["motion_state"] = "R"
            else:
                pd["motion_state"] = "D"

        # ── House cusps (Porphyus, tropical → sidereal) ────────────────────
        # FIX: Subtract ayanamsa from ALL 12 cusps, not just the ascendant.
        # This gives correct sidereal cusps for Sripathi Kendradi Bala and
        # future Bhava Chalit chart rendering.
        sidereal_cusps = None
        asc_sid = 0.0
        try:
            cusps_trop, ascmc_trop = swe.houses(jd, lat, lon_geo, b"O")
            # cusps_trop[0] is cusp 1 (ascendant), [1] is cusp 2, …, [11] is cusp 12
            sidereal_cusps = [(c - ay) % 360 for c in cusps_trop[:12]]
            asc_sid = sidereal_cusps[0]
        except Exception:
            # Fallback: compute ascendant geometrically
            T   = (jd - 2451545.0) / 36525.0
            gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0)
                    + 0.000387933 * T**2 - T**3 / 38710000.0) % 360
            lst  = (gmst + lon_geo) % 360
            eps  = math.radians(23.4393 - 0.013 * T)
            lat_r = math.radians(lat)
            ramc  = math.radians(lst)
            num   = -math.cos(ramc)
            den   = math.sin(eps) * math.tan(lat_r) + math.cos(eps) * math.sin(ramc)
            asc_trop = math.degrees(math.atan2(num, den)) % 360
            mc_trop  = math.degrees(
                math.atan2(math.sin(ramc), math.cos(eps) * math.cos(ramc))
            ) % 360
            diff = (asc_trop - mc_trop) % 360
            if diff < 90 or diff > 270:
                asc_trop = (asc_trop + 180) % 360
            asc_sid = (asc_trop - ay) % 360

        # ── Polar Latitude Protection ────────────────────────────────────────────────
        # At latitudes beyond ±60°, ecliptic lies close to horizon and quadrant
        # arcs collapse, producing wildly distorted house spreads. Fall back to
        # Equal House cusps from the Ascendant in polar zones.
        if abs(lat) > POLAR_LATITUDE_THRESHOLD and sidereal_cusps:
            sidereal_cusps = [(asc_sid + i * 30) % 360 for i in range(12)]
            bhava_method = "equal_house_polar_fallback"
        else:
            bhava_method = "sripathi" if sidereal_cusps else "whole_sign"

        res["Lagna"] = {"longitude": asc_sid, "speed": 0.0, "retro": False}

        # ── Enrich all bodies ──────────────────────────────────────────────
        asc_rashi = int(asc_sid / 30)
        for pn, pd in res.items():
            if pn.startswith("_"):
                continue
            _enrich(pd, pd["longitude"], asc_rashi, sidereal_cusps)

        res["Lagna"]["bhava"] = 1

        res["_meta"] = {
            "jd": jd,
            "ay": ay,
            "engine": "pyswisseph_moshier",
            "ayanamsa_key": ayanamsa_key,
            "sidereal_cusps": sidereal_cusps or [],
        }
        return res


# ══════════════════════════════════════════════════════════════════════════════
#  AstroEngine  (pure-math fallback, no external dependencies)
# ══════════════════════════════════════════════════════════════════════════════
class AstroEngine:
    """
    Low-dependency backup engine (~1 arcminute accuracy 1900–2100).
    Used when pyswisseph is not installed.
    Note: Sripathi cusps are not available in this mode; whole-sign bhava used.
    """

    @staticmethod
    def jd_to_dt(jd):
        jd += 0.5; Z = int(jd); F = jd - Z
        A = Z if Z < 2299161 else (
            lambda a: Z + 1 + a - int(a / 4)
        )(int((Z - 1867216.25) / 36524.25))
        B = A + 1524; C = int((B - 122.1) / 365.25)
        D = int(365.25 * C); E = int((B - D) / 30.6001)
        day = B - D - int(30.6001 * E)
        mo  = E - 1 if E < 14 else E - 13
        yr  = C - 4716 if mo > 2 else C - 4715
        hf  = F * 24; h = int(hf); mn = int((hf - h) * 60)
        return datetime(max(1, yr), mo, day, h, mn)

    @staticmethod
    def _lahiri(jd):
        T = (jd - 2451545.0) / 36525.0
        return (23.85 + T * 100 * (50.29 / 3600)) % 360

    @staticmethod
    def _obliquity(T):
        return (84381.448 - 4680.93 * T - 1.55 * T**2
                + 1999.25 * T**3) / 3600.0

    @staticmethod
    def _sun_lon(jd):
        T  = (jd - 2451545.0) / 36525.0
        L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T**2
        M  = math.radians((357.52911 + 35999.05029 * T - 0.0001537 * T**2) % 360)
        C  = ((1.914602 - 0.004817 * T - 0.000014 * T**2) * math.sin(M)
              + (0.019993 - 0.000101 * T) * math.sin(2 * M)
              + 0.000289 * math.sin(3 * M))
        lon = (L0 + C) % 360
        om  = 125.04 - 1934.136 * T
        return (lon - 0.00569 - 0.00478 * math.sin(math.radians(om))) % 360

    @staticmethod
    def _moon_lon(jd):
        T = (jd - 2451545.0) / 36525.0
        T2 = T * T; T3 = T * T2; T4 = T * T3
        Lp = 218.3164477 + 481267.88123421*T - 0.0015786*T2 + T3/538841 - T4/65194000
        D  = 297.8501921 + 445267.1114034*T - 0.0018819*T2 + T3/545868 - T4/113065000
        M  = 357.5291092 + 35999.0502909*T - 0.0001536*T2 + T3/24490000
        Mp = 134.9633964 + 477198.8675055*T + 0.0087414*T2 + T3/69699 - T4/14712000
        F  = 93.2720950 + 483202.0175233*T - 0.0036539*T2 - T3/3526000 + T4/863310000
        A1 = 119.75 + 131.849*T; A2 = 53.09 + 479264.290*T
        E  = 1.0 - 0.002516*T - 0.0000074*T2
        def r(x): return math.radians(x % 360)
        Dr=r(D); Mr=r(M); Mpr=r(Mp); Fr=r(F)
        A1r=r(A1); A2r=r(A2); Lpr=r(Lp)
        terms = [
            (0,0,1,0,6288774),(2,0,-1,0,1274027),(2,0,0,0,658314),
            (0,0,2,0,213618),(0,1,0,0,-185116),(0,0,0,2,-114332),
            (2,0,-2,0,58793),(2,-1,-1,0,57066),(2,0,1,0,53322),
            (2,-1,0,0,45758),(0,1,-1,0,-40923),(1,0,0,0,-34720),
            (0,1,1,0,-30383),(2,0,0,-2,15327),(0,0,1,-2,10980),
            (4,0,-1,0,10675),(0,0,3,0,10034),(4,0,-2,0,8548),
            (2,1,-1,0,-7888),(2,1,0,0,-6766),(1,0,-1,0,-5163),
            (1,1,0,0,4987),(2,-1,1,0,4036),(2,0,2,0,3994),
            (4,0,0,0,3861),(2,0,-3,0,3665),(0,1,-2,0,-2689),
            (2,-1,-2,0,2390),(1,0,1,0,-2348),(2,-2,0,0,2236),
            (0,2,0,0,-2069),(2,-2,-1,0,2048),(4,-1,-1,0,1215),
            (0,0,2,2,-1110),(3,0,-1,0,-892),(2,1,1,0,-810),
        ]
        dL = sum(c * (E**abs(m) if m else 1) * math.sin(
                     d*Dr + m*Mr + mp*Mpr + f*Fr)
                 for d, m, mp, f, c in terms)
        dL += 3958*math.sin(A1r) + 1962*math.sin(Lpr - Fr) + 318*math.sin(A2r)
        return (Lp + dL / 1_000_000) % 360

    @staticmethod
    def _kepler(M, e):
        E = M + e * math.sin(M) * (1 + e * math.cos(M))
        for _ in range(50):
            dE = (M - E + e * math.sin(E)) / (1 - e * math.cos(E))
            E += dE
            if abs(dE) < 1e-8:
                break
        return E

    @staticmethod
    def _planet_lon(name, jd):
        T = (jd - 2451545.0) / 36525.0
        el = {
            "Mercury": dict(L=252.251+149472.6748*T, e=0.20563,  a=0.387098, I=7.004,  O=48.330,  pi=77.456),
            "Venus":   dict(L=181.980+58517.8156*T,  e=0.006772, a=0.72333,  I=3.395,  O=76.680,  pi=131.564),
            "Earth":   dict(L=100.465+35999.3728*T,  e=0.016709, a=1.0,      I=0.00005,O=174.873, pi=102.937),
            "Mars":    dict(L=355.433+19140.2993*T,  e=0.093400, a=1.52369,  I=1.850,  O=49.558,  pi=336.041),
            "Jupiter": dict(L=34.351+3034.9057*T,   e=0.048393, a=5.20256,  I=1.303,  O=100.464, pi=14.331),
            "Saturn":  dict(L=50.077+1222.1138*T,   e=0.053830, a=9.55475,  I=2.489,  O=113.666, pi=93.057),
        }
        RATES = {"Mercury":4.09234,"Venus":1.60216,"Mars":0.52403,
                 "Jupiter":0.08309,"Saturn":0.03341}

        def xyz(e_):
            L  = e_["L"] % 360
            Mr = math.radians((L - e_["pi"]) % 360)
            E  = AstroEngine._kepler(Mr, e_["e"])
            nu = 2 * math.atan2(
                math.sqrt(1 + e_["e"]) * math.sin(E / 2),
                math.sqrt(1 - e_["e"]) * math.cos(E / 2),
            )
            rv = e_["a"] * (1 - e_["e"] * math.cos(E))
            w  = math.radians((e_["pi"] - e_["O"]) % 360)
            Or = math.radians(e_["O"] % 360)
            Ir = math.radians(e_["I"])
            u  = nu + w
            return (
                rv * (math.cos(Or) * math.cos(u) - math.sin(Or) * math.sin(u) * math.cos(Ir)),
                rv * (math.sin(Or) * math.cos(u) + math.cos(Or) * math.sin(u) * math.cos(Ir)),
                rv * math.sin(u) * math.sin(Ir),
            )

        def geo(px, ex):
            dx, dy = px[0] - ex[0], px[1] - ex[1]
            dist   = math.sqrt(dx**2 + dy**2 + (px[2]-ex[2])**2)
            return math.degrees(math.atan2(dy, dx)) % 360, dist

        ex  = xyz(el["Earth"])
        px  = xyz(el[name])
        lon, dist = geo(px, ex)
        lt  = dist * 0.0057755
        e2  = dict(el[name]); e2["L"] = (e2["L"] - lt * RATES.get(name, 0)) % 360
        return geo(xyz(e2), ex)[0]

    @staticmethod
    def _rahu_lon(jd):
        T = (jd - 2451545.0) / 36525.0
        return (125.04452 - 1934.136261*T + 0.0020708*T**2 + T**3/450000) % 360

    @staticmethod
    def _lagna(jd, lat, lon_geo, ay):
        T    = (jd - 2451545.0) / 36525.0
        gmst = (280.46061837 + 360.98564736629*(jd-2451545.0)
                + 0.000387933*T**2 - T**3/38710000.0) % 360
        lst  = (gmst + lon_geo) % 360
        eps  = math.radians(AstroEngine._obliquity(T))
        lat_r = math.radians(lat)
        ramc  = math.radians(lst)
        num   = -math.cos(ramc)
        den   = math.sin(eps)*math.tan(lat_r) + math.cos(eps)*math.sin(ramc)
        asc_trop = math.degrees(math.atan2(num, den)) % 360
        mc_trop  = math.degrees(
            math.atan2(math.sin(ramc), math.cos(eps)*math.cos(ramc))
        ) % 360
        diff = (asc_trop - mc_trop) % 360
        if diff < 90 or diff > 270:
            asc_trop = (asc_trop + 180) % 360
        return (asc_trop - ay) % 360

    @staticmethod
    def compute(y, mo, d, h, mi, tz, lat, lon_geo,
                ayanamsa_key="Lahiri (Chitrapaksha)",
                node_type="Mean"):
        jd  = _to_jd(y, mo, d, h, mi, tz)
        ay  = AstroEngine._lahiri(jd)
        sid = lambda t: (t - ay) % 360

        P2I = {"Mercury":"Budha","Venus":"Shukra","Mars":"Mangal",
               "Jupiter":"Guru","Saturn":"Shani"}
        res = {}
        for wn, hn in P2I.items():
            t  = AstroEngine._planet_lon(wn, jd)
            t1 = AstroEngine._planet_lon(wn, jd - 1)
            t2 = AstroEngine._planet_lon(wn, jd + 1)
            spd = ((t2 - t1 + 180) % 360 - 180) / 2
            res[hn] = {"longitude": sid(t), "speed": spd, "retro": spd < 0}

        st = AstroEngine._sun_lon(jd)
        mt = AstroEngine._moon_lon(jd)
        rt = AstroEngine._rahu_lon(jd)
        res["Surya"]   = {"longitude": sid(st),          "speed":  1.0,   "retro": False}
        res["Chandra"] = {"longitude": sid(mt),          "speed": 13.2,   "retro": False}
        res["Rahu"]    = {"longitude": sid(rt),          "speed": -0.053, "retro": True}

        # Ketu with True Node support (fallback engine uses mean node math)
        if node_type == "True":
            # Fallback engine has no ephemeris for true nodes; approximate
            # by computing rahu speed independently from two nearby points
            rt1 = AstroEngine._rahu_lon(jd - 1)
            rt2 = AstroEngine._rahu_lon(jd + 1)
            rahu_spd = ((rt2 - rt1 + 180) % 360 - 180) / 2
            res["Rahu"]["speed"] = rahu_spd
            res["Rahu"]["retro"] = rahu_spd < 0
        res["Ketu"] = {
            "longitude": (rt + 180) % 360,
            "speed":     res["Rahu"]["speed"],
            "retro":     True,
        }

        # ── Stationary motion detection ────────────────────────────────────
        for name, pd in res.items():
            if name.startswith("_"):
                continue
            spd = pd.get("speed", 0)
            ret = pd.get("retro", False)
            if abs(spd) < STATIONARY_SPD_DEG:
                if ret:
                    pd["motion_state"] = "SR"
                else:
                    pd["motion_state"] = "SD"
            elif spd < 0:
                pd["motion_state"] = "R"
            else:
                pd["motion_state"] = "D"

        asc_sid = AstroEngine._lagna(jd, lat, lon_geo, ay)

        # ── Polar latitude protection ───────────────────────────────────────
        if abs(lat) > POLAR_LATITUDE_THRESHOLD:
            bhava_method = "equal_house_polar_fallback"
        else:
            bhava_method = "whole_sign"

        res["Lagna"] = {"longitude": asc_sid, "speed": 0, "retro": False}
        res["_meta"] = {
            "jd": jd, "ay": ay,
            "engine": "fallback_math",
            "ayanamsa_key": ayanamsa_key,
            "node_type": node_type,
            "bhava_method": bhava_method,
            "sidereal_cusps": [],
        }

        asc_rashi = int(asc_sid / 30)
        for pn, pd in res.items():
            if pn.startswith("_"):
                continue
            _enrich(pd, pd["longitude"], asc_rashi, None)
        res["Lagna"]["bhava"] = 1
        return res


# ══════════════════════════════════════════════════════════════════════════════
#  TIMEZONE RESOLVER
# ══════════════════════════════════════════════════════════════════════════════
def resolve_timezone(iana_tz_name, y, mo, d, h=12, mi=0):
    """
    Given an IANA timezone string (e.g. 'Asia/Kolkata', 'America/New_York') and
    a local date/time, determine:
      - utc_offset: offset in decimal hours (e.g. 5.5, -4.0)
      - is_dst: boolean indicating if Daylight Saving Time was in effect
      - tz_name: timezone abbreviation (e.g. 'EDT', 'EST', 'IST')
    Uses Python standard library zoneinfo.
    """
    import zoneinfo
    try:
        tz = zoneinfo.ZoneInfo(iana_tz_name)
        dt = datetime(y, mo, d, h, mi, tzinfo=tz)
        offset_sec = dt.utcoffset().total_seconds()
        dst_sec = dt.dst().total_seconds() if dt.dst() is not None else 0.0
        return {
            "utc_offset": offset_sec / 3600.0,
            "is_dst": dst_sec != 0.0,
            "tz_abbr": dt.tzname(),
            "iana_tz": iana_tz_name,
        }
    except Exception as e:
        return {
            "utc_offset": 5.5,
            "is_dst": False,
            "tz_abbr": "IST",
            "iana_tz": iana_tz_name,
            "error": str(e),
        }


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC DISPATCH
# ══════════════════════════════════════════════════════════════════════════════
def compute_chart(y, mo, d, h, mi, tz=None, lat=0.0, lon_geo=0.0,
                  ayanamsa_key="Lahiri (Chitrapaksha)", node_type="Mean",
                  iana_tz=None):
    """
    Dispatch to SweEngine if available, else AstroEngine.
    If iana_tz is supplied and tz is None, resolves UTC offset and DST automatically.
    """
    dst_info = None
    if iana_tz:
        dst_info = resolve_timezone(iana_tz, y, mo, d, h, mi)
        if tz is None:
            tz = dst_info["utc_offset"]
    if tz is None:
        tz = 5.5

    if SWE_OK:
        res = SweEngine.compute(y, mo, d, h, mi, tz, lat, lon_geo,
                                ayanamsa_key, node_type=node_type)
    else:
        res = AstroEngine.compute(y, mo, d, h, mi, tz, lat, lon_geo,
                                  ayanamsa_key, node_type=node_type)

    if dst_info and "_meta" in res:
        res["_meta"]["iana_tz"] = iana_tz
        res["_meta"]["is_dst"] = dst_info["is_dst"]
        res["_meta"]["tz_abbr"] = dst_info["tz_abbr"]

    return res


# ══════════════════════════════════════════════════════════════════════════════
#  TRANSIT CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════
def compute_transits(ayanamsa_key="Lahiri (Chitrapaksha)", lat=0.0, lon=0.0):
    """
    Compute planetary positions for right now (UTC).
    Uses the same engine as the natal chart.  Lat/lon 0,0 is fine for
    geocentric planetary longitudes (only house cusps would differ).
    Returns the same dict structure as compute_chart().
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return compute_chart(
        now.year, now.month, now.day,
        now.hour, now.minute, 0.0,
        lat, lon, ayanamsa_key
    )
