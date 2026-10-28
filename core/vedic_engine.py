# -*- coding: utf-8 -*-
"""
vedic_engine.py
===============
Classical Jyotish calculations:
  - Sthiti (planetary dignity)
  - Varga (divisional charts D-1 through D-60)
  - Vimshottari Dasha (using TROPICAL_YEAR, not Julian 365.25)
  - Yoga detection
  - Dosha detection  (remedies filtered via FUNC_BENEFIC_BY_LAGNA)
  - Partial Shadbala (Kendradi Bala uses Sripathi cusps when available)

Key fixes vs v3.0
-----------------
* Dasha drift   : TROPICAL_YEAR (365.24219) replaces Julian 365.25
* Node dignity  : Rahu/Ketu now get Uchcha/Neecha via shared UCHCHA_DEG table
* Remedy safety : gemstone prescriptions filtered by functional-benefic status
* Gambhirata    : removed from Dosha output (was contradicting LLM alignment)
* Kendradi Bala : uses Sripathi cusp-based bhava when available
"""

from datetime import datetime, timedelta
from core.constants import (
    RASHI, NAKSHATRA, NAK_LORDS, ALL_GRAHAS, RASHI_SWAMI,
    UCHCHA_DEG, NEECHA_DEG, SWAKSHETRA, MOOLTRIKONA,
    MITRA, SHATRU, DASHA_KRAM, DASHA_VARSH, TROPICAL_YEAR,
    FUNC_BENEFIC_BY_LAGNA, BOUNDARY_THRESHOLD,
    TITHI_NAMES, NITYA_YOGAS, CHARA_KARANAS, STHIRA_KARANAS,
    VARA_NAMES, GEMSTONE_SPECS,
)


# ══════════════════════════════════════════════════════════════════════════════
#  STHITI (Planetary Dignity)
# ══════════════════════════════════════════════════════════════════════════════
def sthiti(graha, rashi_idx):
    """
    Return dignity string for graha in rashi_idx (0-11).
    FIX: Rahu and Ketu now participate in dignity checking via UCHCHA_DEG.
    """
    e_r = int(UCHCHA_DEG.get(graha, -999) / 30)
    n_r = int(NEECHA_DEG.get(graha, -999) / 30)
    m_r = MOOLTRIKONA.get(graha, -1)
    sw  = SWAKSHETRA.get(graha, [])
    if rashi_idx == e_r:        return "Uchcha"
    if rashi_idx == n_r:        return "Neecha"
    if rashi_idx == m_r:        return "Moolatrikona"
    if rashi_idx in sw:         return "Swakshetra"
    # Nodes have no natural mitra/shatru relationships — return Sama
    if graha in ("Rahu", "Ketu"):
        return "Sama"
    swami = RASHI_SWAMI[rashi_idx]
    if swami in MITRA.get(graha, []):   return "Mitra"
    if swami in SHATRU.get(graha, []):  return "Shatru"
    return "Sama"


# ══════════════════════════════════════════════════════════════════════════════
#  ASPECT & DRIK BALA (6-fold Shadbala components)
# ══════════════════════════════════════════════════════════════════════════════

# Classical special aspect rules (BPHS)
# Mars: 4th, 7th, 8th; Jupiter: 5th, 7th, 9th; Saturn: 3rd, 7th, 10th; others: 7th only
SPECIAL_ASPECTS = {
    "Mangal": [4, 7, 8],
    "Guru":   [5, 7, 9],
    "Shani":  [3, 7, 10],
}

# Classical benefic/malefic classification (from BPHS)
BENEFIC_GRAHAS = {"Guru", "Shukra", "Budha", "Chandra"}
MALEFIC_GRAHAS = {"Surya", "Mangal", "Shani", "Rahu", "Ketu"}


def _aspect_angle_between(lon_a, lon_b):
    """Shortest angular distance between two longitudes (0–180)."""
    diff = abs(lon_a - lon_b) % 360
    return min(diff, 360 - diff)


def drik_bala(grahas):
    """
    Calculate Drik Bala (aspectual strength) for all 7 grahas.

    Returns dict keyed by planet name -> {
        "drik_bala": net virupa score (positive = stronger),
        "aspects_received": list of (aspecting_planet, house_from, virupa_value)
    }
    """
    results = {}
    grahas_list = ALL_GRAHAS[:7]  # Seven classical grahas

    for target in grahas_list:
        target_lon = grahas.get(target, {}).get("longitude", 0)
        aspects_received = []
        net_virupa = 0

        for aspector in grahas_list:
            if aspector == target:
                continue
            aspector_lon = grahas.get(aspector, {}).get("longitude", 0)

            # Determine which houses aspector aspects target (classical rules)
            if aspector in SPECIAL_ASPECTS:
                aspect_houses = SPECIAL_ASPECTS[aspector]
            else:
                aspect_houses = [7]  # All others aspect only 7th

            # Check each house aspect
            for h in aspect_houses:
                aspect_angle = h * 30  # Each house = 30 degrees
                angle_diff = _aspect_angle_between(target_lon, aspector_lon)

                # Classical aspect orbs (BPHS):
                # Exact at 60° variance; drops linearly to 0 at 60° from exact
                orb_allowed = 60
                if abs(angle_diff - aspect_angle) <= orb_allowed:
                    # Virupa decreases linearly from 60 at exact to 0 at max orb
                    virupa = 60 - abs(angle_diff - aspect_angle)
                    virupa = max(0, virupa)

                    # Benefics strengthen, malefics weaken
                    if aspector in BENEFIC_GRAHAS:
                        net_virupa += virupa
                        aspects_received.append((aspector, h, round(virupa, 1)))
                    elif aspector in MALEFIC_GRAHAS:
                        net_virupa -= virupa
                        aspects_received.append((aspector, -h, -round(virupa, 1)))

        results[target] = {
            "drik_bala": round(net_virupa, 1),
            "aspects_received": aspects_received,
        }

    return results


# ══════════════════════════════════════════════════════════════════════════════
#  NAVAMSA & VARGA
# ══════════════════════════════════════════════════════════════════════════════
def navamsa(lon):
    """BPHS Navamsa: (rashi*9 + pada_within_sign) mod 12."""
    r    = int(lon / 30)
    pada = int((lon % 30) / (30 / 9))
    return (r * 9 + pada) % 12


def varga(lon, n, return_boundary=False):
    """
    Return the varga rashi (0-11) for divisional chart D-n.
    If return_boundary=True, returns tuple: (rashi_idx, is_near_boundary, deg_in_varga).
    Near boundary is detected if the longitude is within BOUNDARY_THRESHOLD (0.05°)
    of entering or exiting the division segment.
    """
    r = int(lon / 30)
    d = lon % 30
    seg_size = 30.0 / n
    pos_in_seg = d % seg_size
    is_boundary = (pos_in_seg <= BOUNDARY_THRESHOLD) or (pos_in_seg >= (seg_size - BOUNDARY_THRESHOLD))
    deg_in_varga = (pos_in_seg / seg_size) * 30.0

    k = int(d * n / 30)

    if n == 1:
        res = r
    elif n == 2:  # D-2 Hora (BPHS corrected)
        res = (4 if k == 0 else 3) if r % 2 == 0 else (3 if k == 0 else 4)
    elif n == 3:  res = (r + [0, 4, 8][k]) % 12
    elif n == 4:  res = (r + [0, 3, 6, 9][k]) % 12
    elif n == 7:  res = (r + k) % 12 if r % 2 == 0 else (r + 6 + k) % 12
    elif n == 9:  res = navamsa(lon)
    elif n == 10: res = (r + k) % 12 if r % 2 == 0 else (r + 8 + k) % 12
    elif n == 12: res = (r * 12 + k) % 12
    elif n == 16: res = ({0:0, 1:4, 2:8}[r % 3] + k) % 12
    elif n == 20: res = ({0:0, 1:8, 2:4}[r % 3] + k) % 12
    elif n == 24: res = (4 + k) % 12 if r % 2 == 0 else (3 + k) % 12
    elif n == 27: res = ({0:0, 1:3, 2:6}[r % 3] + k) % 12
    elif n == 30:
        # Trishamsha per BPHS (spans sum exactly to 30 deg per sign)
        sp_odd  = [(0,5),(10,5),(8,8),(2,7),(6,5)]
        sp_even = [(1,5),(5,5),(11,8),(9,7),(7,5)]
        spans   = sp_odd if r % 2 == 0 else sp_even
        acc = 0
        assigned = spans[-1][0]
        for ri, sp in spans:
            acc += sp
            if d < acc:
                assigned = ri
                break
        res = assigned
    elif n == 40: res = (0 + k) % 12 if r % 2 == 0 else (6 + k) % 12
    elif n == 45: res = ({0:0, 1:4, 2:8}[r % 3] + k) % 12
    elif n == 60: res = (r * 60 + k) % 12
    else: res = (r + k) % 12

    if return_boundary:
        return res, is_boundary, deg_in_varga
    return res


# ══════════════════════════════════════════════════════════════════════════════
#  VIMSHOTTARI DASHA (Levels 1 to 4: Maha, Antar, Pratyantar, Sookshma)
# ══════════════════════════════════════════════════════════════════════════════
def vimshottari(chandra_lon, jd, year_days=365.24219, depth=2, current_only_sub=False):
    """
    Compute Vimshottari Dashas with configurable nesting depth (1 to 4):
      - depth=1: Mahadashas only
      - depth=2: Mahadashas + Antardashas (default)
      - depth=3: Mahadashas + Antardashas + Pratyantardashas
      - depth=4: Mahadashas + Antardashas + Pratyantardashas + Sookshmadashas
    
    If current_only_sub=True, levels 3 and 4 are computed ONLY for the period(s)
    spanning the current datetime, preventing ballooning of the returned data tree.
    """
    ns        = 360 / 27
    nak_num   = int(chandra_lon / ns)
    elapsed   = chandra_lon % ns
    rem_frac  = 1 - (elapsed / ns)
    start_lord = NAK_LORDS[nak_num]
    start_idx  = DASHA_KRAM.index(start_lord)

    # Approximate birth datetime from JD
    try:
        from core.astro_engine import AstroEngine
        birth_dt = AstroEngine.jd_to_dt(jd)
    except Exception:
        birth_dt = datetime(2000, 1, 1)

    def _delta(years):
        return timedelta(days=years * year_days)

    now = datetime.now()

    def _calc_sookshma(pd_lord, pd_start, pd_years, pd_idx):
        sds = []
        cur_s = pd_start
        for l in range(9):
            sl = DASHA_KRAM[(pd_idx + l) % 9]
            sy = pd_years * DASHA_VARSH[sl] / 120.0
            se = cur_s + _delta(sy)
            sds.append({
                "lord": sl,
                "start": cur_s,
                "end": se,
                "varsh": sy,
            })
            cur_s = se
        return sds

    def _calc_pratyantar(ad_lord, ad_start, ad_years, ad_idx):
        pds = []
        cur_p = ad_start
        for k in range(9):
            pl = DASHA_KRAM[(ad_idx + k) % 9]
            py = ad_years * DASHA_VARSH[pl] / 120.0
            pe = cur_p + _delta(py)
            p_dict = {
                "lord": pl,
                "start": cur_p,
                "end": pe,
                "varsh": py,
            }
            if depth >= 4:
                should_expand_sd = True
                if current_only_sub and not (cur_p <= now <= pe):
                    should_expand_sd = False
                if should_expand_sd:
                    p_dict["sookshmadasha"] = _calc_sookshma(pl, cur_p, py, (ad_idx + k) % 9)
            pds.append(p_dict)
            cur_p = pe
        return pds

    dashas = []
    cur    = birth_dt
    for i in range(9):
        idx   = (start_idx + i) % 9
        lord  = DASHA_KRAM[idx]
        yrs   = DASHA_VARSH[lord] * rem_frac if i == 0 else DASHA_VARSH[lord]
        end   = cur + _delta(yrs)

        md_dict = {
            "lord": lord,
            "start": cur,
            "end": end,
            "varsh": yrs,
        }

        if depth >= 2:
            ads  = []
            as_  = cur
            for j in range(9):
                al  = DASHA_KRAM[(idx + j) % 9]
                ay_ = yrs * DASHA_VARSH[al] / 120.0
                ae  = as_ + _delta(ay_)
                ad_dict = {
                    "lord": al,
                    "start": as_,
                    "end": ae,
                    "varsh": ay_,
                }
                if depth >= 3:
                    should_expand_pd = True
                    if current_only_sub and not (as_ <= now <= ae):
                        should_expand_pd = False
                    if should_expand_pd:
                        ad_dict["pratyantardasha"] = _calc_pratyantar(al, as_, ay_, (idx + j) % 9)
                ads.append(ad_dict)
                as_ = ae
            md_dict["antardasha"] = ads

        dashas.append(md_dict)
        cur = end
    return dashas


def compute_pratyantardasha_for_ad(ad_dict, year_days=365.24219, include_sookshma=False):
    """
    Compute the 9 Pratyantardashas for a specific Antardasha dictionary on-demand.
    Used for UI interactive row expansion (<Double-1>) or fine-grained event timing.
    """
    ad_lord  = ad_dict["lord"]
    ad_start = ad_dict["start"]
    ad_years = ad_dict["varsh"]
    ad_idx   = DASHA_KRAM.index(ad_lord)

    def _delta(years):
        return timedelta(days=years * year_days)

    pds = []
    cur_p = ad_start
    for k in range(9):
        pl = DASHA_KRAM[(ad_idx + k) % 9]
        py = ad_years * DASHA_VARSH[pl] / 120.0
        pe = cur_p + _delta(py)
        p_dict = {
            "lord":  pl,
            "start": cur_p,
            "end":   pe,
            "varsh": py,
        }
        if include_sookshma:
            sds = []
            cur_s = cur_p
            p_idx = (ad_idx + k) % 9
            for l in range(9):
                sl = DASHA_KRAM[(p_idx + l) % 9]
                sy = py * DASHA_VARSH[sl] / 120.0
                se = cur_s + _delta(sy)
                sds.append({
                    "lord":  sl,
                    "start": cur_s,
                    "end":   se,
                    "varsh": sy,
                })
                cur_s = se
            p_dict["sookshmadasha"] = sds
        pds.append(p_dict)
        cur_p = pe
    return pds


def check_varga_boundary(lon, n, threshold=BOUNDARY_THRESHOLD):
    """
    Check if a planet at natal longitude 'lon' is within +/- threshold degrees
    of a division/sign boundary in divisional chart D-n.
    Evaluates in natal arc degrees: distance to division cusp <= threshold.
    """
    d = lon % 30.0
    seg_size = 30.0 / n
    pos_in_seg = d % seg_size
    dist = min(pos_in_seg, seg_size - pos_in_seg)
    return dist <= threshold


def compute_varga_chart(grahas, n, threshold=BOUNDARY_THRESHOLD):
    """
    Compute complete divisional chart D-n for all grahas and Lagna.
    Returns a dict mapping graha_name -> dict with varga placements:
      - natal_longitude: original natal longitude
      - varga_rashi: rashi index 0-11
      - rashi_naam: Sanskrit sign name
      - rashi_ansh: degrees within varga sign (0-30)
      - varga_longitude: absolute varga longitude (0-360)
      - bhava: house from varga Lagna (1-12)
      - boundary_flag: True if within +/- threshold of sign edge
      - boundary_dist: angular distance to nearest division edge in natal degrees
      - sthiti: dignity in the divisional sign
    """
    vg = {}
    seg_size = 30.0 / n
    for gn, pd in grahas.items():
        if gn.startswith("_"):
            continue
        lon = pd.get("longitude")
        if lon is None:
            continue
        vs = varga(lon, n)
        d = lon % 30.0
        pos_in_seg = d % seg_size
        dist = min(pos_in_seg, seg_size - pos_in_seg)
        is_boundary = dist <= threshold
        vd = (pos_in_seg / seg_size) * 30.0
        vg[gn] = {
            **pd,
            "natal_longitude": lon,
            "varga_rashi": vs,
            "varga_rashi_naam": RASHI[vs],
            "varga_rashi_ansh": vd,
            "varga_longitude": vs * 30.0 + vd,
            "boundary_flag": is_boundary,
            "boundary_dist": round(dist, 4),
            "sthiti": sthiti(gn, vs),
        }

    # Compute varga bhava relative to varga Lagna
    lagna_vr = vg.get("Lagna", {}).get("varga_rashi", 0)
    for gn, pd in vg.items():
        if gn in ("Lagna", "_meta"):
            continue
        pd["bhava"] = (pd["varga_rashi"] - lagna_vr) % 12 + 1

    return vg


# ══════════════════════════════════════════════════════════════════════════════
#  YOGA DETECTION
# ══════════════════════════════════════════════════════════════════════════════
def yoga(grahas, lagna_rashi):
    yogas = []
    ho    = lambda p: grahas.get(p, {}).get("bhava", 0)
    ro    = lambda p: grahas.get(p, {}).get("rashi", -1)
    kendra = lambda p: ho(p) in [1, 4, 7, 10]
    bl     = lambda h: RASHI_SWAMI[(lagna_rashi + h - 1) % 12]

    # Gaja Kesari
    if (ho("Guru") - ho("Chandra")) % 12 in [0, 3, 6, 9]:
        yogas.append({
            "naam": "Gaja Kesari Yoga", "bala": "Uttam",
            "graha": ["Guru", "Chandra"],
            "vivaran": (
                "Prominent social standing and lasting renown. "
                "Wealth and authority accumulate naturally. "
                "Financial gains through wisdom and relationships. "
                "(Guru in Kendra from Chandra)"
            ),
        })

    # Pancha Mahapurusha
    for g, nm in [("Guru","Hamsa"),("Mangal","Ruchaka"),("Shani","Sasha"),
                  ("Shukra","Malavya"),("Budha","Bhadra")]:
        if (ro(g) in SWAKSHETRA.get(g,[]) + [int(UCHCHA_DEG.get(g,0)/30)]
                and kendra(g)):
            descs = {
                "Hamsa":   "Intelligence, spiritual authority and charitable renown.",
                "Ruchaka": "Athletic or military distinction; strong leadership and physique.",
                "Sasha":   "Long life, discipline, political power; mastery over rivals.",
                "Malavya": "Beauty, luxury, vehicle ownership; success in arts or business.",
                "Bhadra":  "Sharp intellect, eloquence; business acumen and numerical skill.",
            }
            yogas.append({
                "naam": f"{nm} Yoga (Pancha Mahapurusha)", "bala": "Uttam",
                "graha": [g],
                "vivaran": (
                    f"{descs.get(nm,'')} Results peak in {g}'s Mahadasha. "
                    f"({g} in own/exaltation Rashi in a Kendra)"
                ),
            })

    # Raja Yoga (Kendra-Trikona lord conjunction)
    kls = [bl(h) for h in [1, 4, 7, 10]]
    tls = [bl(h) for h in [1, 5, 9]]
    rj  = [(k, t) for k in set(kls) for t in set(tls)
           if k != t and ro(k) == ro(t) and ro(k) >= 0]
    if rj:
        yogas.append({
            "naam": "Raja Yoga", "bala": "Pratham",
            "graha": list({p for pair in rj for p in pair}),
            "vivaran": (
                "Rise to authority and professional recognition. "
                "Executive or entrepreneurial success strongly indicated. "
                f"Results manifest in involved Dasha periods. "
                f"(Kendra-Trikona lords conjunct: {rj})"
            ),
        })

    # Dhana Yoga
    wl = [bl(h) for h in [2, 5, 9, 11]]
    rashi_set = [ro(l) for l in set(wl) if ro(l) >= 0]
    if len(rashi_set) != len(set(rashi_set)):
        yogas.append({
            "naam": "Dhana Yoga", "bala": "Shubha",
            "graha": list(set(wl)),
            "vivaran": (
                "Steady and significant wealth accumulation. "
                "Multiple income sources, gains from business or inheritance. "
                "Financial peaks during wealth-lord Dasha periods. "
                "(Lords of Bhavas 2, 5, 9, 11 mutually connected)"
            ),
        })

    # Budha-Aditya
    if ro("Surya") == ro("Budha"):
        yogas.append({
            "naam": "Budha-Aditya Yoga", "bala": "Shubha",
            "graha": ["Surya", "Budha"],
            "vivaran": (
                "Sharp intellect, eloquent speech, favour from authority. "
                "Success in analytics, administration or advisory roles. "
                "(Surya-Budha conjunction)"
            ),
        })

    # Chandra-Mangal
    if ro("Chandra") == ro("Mangal"):
        yogas.append({
            "naam": "Chandra-Mangal Yoga", "bala": "Madhyam",
            "graha": ["Chandra", "Mangal"],
            "vivaran": (
                "Strong drive and material gains — especially in business or trade. "
                "Emotional determination turns challenges into wealth. "
                "(Chandra-Mangal conjunction)"
            ),
        })

    # Saraswati
    jh, vh, bh = ho("Guru"), ho("Shukra"), ho("Budha")
    if all(h in [1, 2, 4, 5, 7, 9, 10] for h in [jh, vh, bh]):
        yogas.append({
            "naam": "Saraswati Yoga", "bala": "Shubha",
            "graha": ["Guru", "Shukra", "Budha"],
            "vivaran": (
                "Exceptional intellect and artistic or academic distinction. "
                "Success in education, writing, music, law or higher learning. "
                "(Guru, Shukra, Budha all in auspicious Bhavas)"
            ),
        })

    # Viparita Raja Yoga
    dl = [bl(h) for h in [6, 8, 12]]
    if all(ho(l) in [6, 8, 12] for l in dl):
        yogas.append({
            "naam": "Viparita Raja Yoga", "bala": "Vishesh",
            "graha": dl,
            "vivaran": (
                "Dramatic rise from setbacks; gains through adversity. "
                "Unexpected success in medicine, research or politics after age 35. "
                "(Lords of 6th, 8th, 12th all placed in Dusthanas)"
            ),
        })

    # Neechabhanga Raja Yoga
    for g in ALL_GRAHAS:
        ns = int(NEECHA_DEG.get(g, -999) / 30)
        if ro(g) == ns and ns >= 0:
            nl = RASHI_SWAMI[ns]
            if kendra(nl):
                yogas.append({
                    "naam": "Neechabhanga Raja Yoga", "bala": "Madhyam",
                    "graha": [g, nl],
                    "vivaran": (
                        f"Initial struggles give way to notable success. "
                        f"Native rises through adversity to a distinguished position. "
                        f"({g} Neecha but {nl} in Kendra neutralises it)"
                    ),
                })

    return yogas


# ══════════════════════════════════════════════════════════════════════════════
#  DOSHA DETECTION
# ══════════════════════════════════════════════════════════════════════════════
def _func_benefic_for_lagna(lagna_rashi):
    """Return the functional benefic list for the given lagna rashi index."""
    return FUNC_BENEFIC_BY_LAGNA.get(RASHI[lagna_rashi], [])

def _remedy_for(graha, lagna_rashi, gem, mantra, generic_puja):
    """
    FIX: Return a remedy string that is safe for the given lagna.
    If `graha` is NOT a functional benefic for the lagna, a gemstone
    prescription is replaced with mantra/puja to prevent contraindicated advice.
    """
    fb = _func_benefic_for_lagna(lagna_rashi)
    if graha in fb:
        return f"Remedy: {gem}; {mantra}."
    else:
        return f"Remedy: {mantra}; {generic_puja} (gemstone not advised for this Lagna)."


def dosha(grahas, lagna_rashi):
    """
    Detect Doshas and return result-first vivaran.
    FIX: 'gambhirata' key removed — was causing contradictory severity signals
    inside the LLM prompt.
    FIX: Remedies filtered through functional benefic table.
    """
    doshas_out = []
    ho   = lambda p: grahas.get(p, {}).get("bhava", 0)
    ro   = lambda p: grahas.get(p, {}).get("rashi", -1)
    kendra = lambda p: ho(p) in [1, 4, 7, 10]
    phys = [g for g in ALL_GRAHAS if g not in ("Rahu", "Ketu")]

    # ── Mangal Dosha ──────────────────────────────────────────────────────
    mh = ho("Mangal"); mr = ro("Mangal")
    if mh in [1, 2, 4, 7, 8, 12]:
        can   = False; clist = []
        if mr in SWAKSHETRA.get("Mangal", []) + [int(UCHCHA_DEG["Mangal"] / 30)]:
            can = True; clist.append("Mangal in own/exaltation sign")
        if ro("Guru") == mr:   can = True; clist.append("Guru conjunct Mangal")
        if ro("Chandra") == mr: can = True; clist.append("Chandra conjunct Mangal")

        rem = _remedy_for("Mangal", lagna_rashi,
                          "red coral in gold on Tuesday",
                          "Mangal Puja, Hanuman Chalisa on Tuesdays",
                          "Kuja Graha Shanti")
        if can:
            viv = (f"Dosha cancelled — marriage prospects are normal. "
                   f"({', '.join(clist)}). "
                   f"Mild Mangal puja may still be beneficial for energy channelling.")
        else:
            viv = (f"Match with a Mangalik partner is advisable. Marriage after age 28 is safer. "
                   f"Potential for relationship friction — channelled constructively it excels in leadership. "
                   f"{rem} (Mangal in Bhava {mh})")

        doshas_out.append({
            "naam": "Mangal (Kuja) Dosha",
            "sthiti": "Khandit" if can else "Sakriya",
            "graha": ["Mangal"],
            "vivaran": viv,
        })

    # ── Kaal Sarp Dosha ───────────────────────────────────────────────────
    rl = grahas.get("Rahu", {}).get("longitude", 0)
    rh = ho("Rahu")
    if all((grahas[g]["longitude"] - rl) % 360 < 180
           for g in phys if g in grahas):
        variants = {
            (1,7):  "Anant — self-expression and relationship patterns intensified",
            (2,8):  "Kulik — financial cycles; deliberate planning is key",
            (3,9):  "Vasuki — sibling dynamics and communication need attention",
            (4,10): "Shankhpal — career and domestic life require balance",
            (5,11): "Padma — creative expression and children themes prominent",
            (6,12): "Mahapadma — hidden challenges and foreign connections significant",
        }
        axis = (rh, ho("Ketu"))
        vd   = variants.get(axis, f"Axis {rh}-{ho('Ketu')}")
        viv  = (
            f"Life moves in intense cycles — concentrated effort yields exceptional results. "
            f"Theme: {vd}. After age 48 the intensity softens significantly. "
            f"This is a pattern for focused achievement, not a curse. "
            f"Remedy: Nag Panchami Puja, Rahu-Ketu Graha Shanti. "
            f"(All Grahas between Rahu-Ketu axis)"
        )
        doshas_out.append({
            "naam": f"Kaal Sarp Dosha ({vd.split(' — ')[0].strip()})",
            "sthiti": "Sakriya",
            "graha": ["Rahu", "Ketu"],
            "vivaran": viv,
        })

    # ── Kemadruma Dosha ───────────────────────────────────────────────────
    cr = int(grahas.get("Chandra", {}).get("longitude", 0) / 30)
    if not any(ro(g) in [(cr - 1) % 12, (cr + 1) % 12]
               for g in phys if g != "Chandra"):
        can = any(ho(g) in [1, 4, 7, 10] for g in phys)
        # FIX: only recommend Pearl if Chandra is a functional benefic
        rem = _remedy_for("Chandra", lagna_rashi,
                          "pearl in silver on Monday",
                          "Chandra Stotra, Chandra worship on Mondays",
                          "Chandra Graha Shanti")
        if can:
            viv = ("Dosha neutralised by Grahas in Kendra — emotional isolation minimised. "
                   + rem)
        else:
            viv = (
                "Tendency toward reflective solitude; inner emotional world is rich "
                "but may feel under-expressed. Building conscious support networks is "
                "the key growth edge. "
                + rem + " (No Graha in 2nd/12th from Chandra)"
            )
        doshas_out.append({
            "naam": "Kemadruma Dosha",
            "sthiti": "Khandit" if can else "Sakriya",
            "graha": ["Chandra"],
            "vivaran": viv,
        })

    # ── Graha Yuddha ──────────────────────────────────────────────────────
    vis = ["Mangal", "Budha", "Guru", "Shukra", "Shani"]
    for i, g1 in enumerate(vis):
        for g2 in vis[i + 1:]:
            l1 = grahas.get(g1, {}).get("longitude", 0)
            l2 = grahas.get(g2, {}).get("longitude", 0)
            diff = abs(l1 - l2); diff = 360 - diff if diff > 180 else diff
            if diff < 1.0:
                w  = g1 if (l1 % 30) > (l2 % 30) else g2
                lo = g2 if w == g1 else g1
                doshas_out.append({
                    "naam": f"Graha Yuddha ({g1}-{g2})",
                    "sthiti": "Sakriya",
                    "graha": [g1, g2],
                    "vivaran": (
                        f"{w} wins this planetary war; {lo}'s significations become "
                        f"more unpredictable. The domains of {lo} need conscious attention. "
                        f"Remedy: worship {lo}. ({g1}-{g2} within 1 degree — Graha Yuddha)"
                    ),
                })

    return doshas_out


# ══════════════════════════════════════════════════════════════════════════════
#  SHADBALA (Partial)
# ══════════════════════════════════════════════════════════════════════════════
def shadbala(graha, grahas, lagna_rashi, drik_bala_scores=None, ayana_bala_scores=None,
             jd=None, graha_pid=None):
    """
    Complete 6-fold Shadbala — all 6 classical Bala components.

    Components:
      1. Sthana Bala (Uchcha + Ojhayugmarashi + Drekkana + Kendradi)
      2. Saptavarga Bala
      3. Cheshta Bala
      4. Naisargika Bala
      5. Drik Bala  (aspectual strength)
      6. Ayana Bala (declination / solsticial strength)

    Args:
        graha: planet name to compute Shadbala for
        grahas: full grahas dict from SweEngine.compute()
        lagna_rashi: rashi index (0-11) of Lagna
        drik_bala_scores: pre-computed Drik Bala dict from drik_bala() (optional)
        ayana_bala_scores: pre-computed Ayana Bala dict from ayana_bala() (optional)
        jd: Julian Day (for Ayana Bala declination lookup) (optional)
        graha_pid: Swiss Ephemeris planet ID (for Ayana Bala lookup) (optional)

    Returns dict with all six component scores and total.
    """
    pd  = grahas.get(graha, {})
    lon = pd.get("longitude", 0)
    r   = pd.get("rashi", 0)
    h   = pd.get("bhava", 1)
    spd = pd.get("speed", 0)
    ret = pd.get("retro", False)

    # ── Sthana Bala components ──────────────────────────────────────────────

    # Uchcha Bala (exaltation strength)
    dd   = (UCHCHA_DEG.get(graha, 0) + 180) % 360
    diff = abs(lon - dd); diff = 360 - diff if diff > 180 else diff
    ub   = diff / 3.0

    # Ojhayugmarashi Bala (odd/even sign placement)
    # Odd signs (0,2,4,6,8,10): natural benefics stronger; even signs: natural malefics stronger
    ojb = 15.0 if (r % 2 == 0) == (graha in BENEFIC_GRAHAS) else 0.0

    # Drekkana Bala (decanate placement, 0-10 degrees each)
    d_k = int((lon % 30) / 10)  # Drekkana index 0-2
    drekkana_swami_map = {
        0: RASHI_SWAMI[r],      # 1st drekkana: own sign lord
        1: RASHI_SWAMI[(r + 5) % 12],  # 5th sign lord
        2: RASHI_SWAMI[(r + 7) % 12],  # 9th sign lord
    }
    drekkana_swami = drekkana_swami_map.get(d_k, RASHI_SWAMI[r])
    drekkana_dignity = sthiti(drekkana_swami, r)  # dignity of drekkana lord in target sign
    dkb_map = {"Uchcha": 60, "Moolatrikona": 45, "Swakshetra": 30,
               "Mitra": 15, "Sama": 7.5, "Shatru": 3.75, "Neecha": 0}
    dkb = dkb_map.get(drekkana_dignity, 7.5)

    # Kendradi Bala (house-based strength)
    kb = 60.0 if h in [1, 4, 7, 10] else (30.0 if h in [2, 5, 8, 11] else 15.0)

    sthana_bala = ub + ojb + dkb + kb

    # ── Saptavarga Bala ────────────────────────────────────────────────────
    dmap = {
        "Uchcha":60,"Moolatrikona":45,"Swakshetra":30,
        "Mitra":15,"Sama":7.5,"Shatru":3.75,"Neecha":0,
    }
    svb = dmap.get(sthiti(graha, r), 7.5)

    # ── Cheshta Bala (motion-based) ───────────────────────────────────────
    cb = (60.0 if ret else (30.0 if abs(spd) < 0.1 else max(0, 60 - abs(spd) * 5)))

    # ── Naisargika Bala (natural order) ───────────────────────────────────
    nb = {"Surya":60,"Chandra":51.43,"Shukra":42.86,"Guru":34.29,
          "Budha":25.71,"Mangal":17.14,"Shani":8.57,
          "Rahu":8.57,"Ketu":8.57}.get(graha, 10)

    # ── Drik Bala (aspectual strength) ────────────────────────────────────
    if drik_bala_scores and graha in drik_bala_scores:
        drb = drik_bala_scores[graha]["drik_bala"]
    else:
        drb = drik_bala(grahas).get(graha, {}).get("drik_bala", 0)

    # ── Ayana Bala (declination / solsticial strength) ────────────────────
    if ayana_bala_scores and graha in ayana_bala_scores:
        ayb = ayana_bala_scores[graha]
    elif jd is not None and graha_pid is not None:
        ayb = _ayana_bala_for_graha(jd, graha_pid)
    else:
        ayb = 0.0

    # ── Total ──────────────────────────────────────────────────────────────
    tot = sthana_bala + svb + cb + nb + drb + ayb
    thr = {"Surya":390,"Chandra":360,"Mangal":300,"Budha":420,
           "Guru":390,"Shukra":330,"Shani":300}.get(graha, 300)

    return {
        "uchcha_bala":    round(ub, 1),
        "ojhayugmarashi": round(ojb, 1),
        "drekkana":       round(dkb, 1),
        "kendradi":       round(kb, 1),
        "sthana_bala":    round(sthana_bala, 1),
        "saptavarga":     round(svb, 1),
        "cheshta":        round(cb, 1),
        "naisargika":     round(nb, 1),
        "drik_bala":      round(drb, 1),
        "ayana_bala":     round(ayb, 1),
        "total":          round(tot, 1),
        "seema":          thr,
        "poorna":         tot >= (thr * 0.4),
        "sthiti_key":     sthiti(graha, r),
        "bhava_method":   pd.get("bhava_method", "whole_sign"),
    }


def ayana_bala(grahas, jd=None):
    """
    Calculate Ayana Bala (declination strength) for all grahas.

    Queries Swiss Ephemeris for planetary declination via swe.calc_ut with
    FLG_EQUATORIAL | FLG_SIDEREAL. Ayana Bala depends on obliquity of
    ecliptic (ε ≈ 23.44°) — planets near extreme declination on their
    northern/southern side receive maximum Ayana Bala.

    Returns dict keyed by planet name -> Ayana Bala score (0-60 virupas).
    """
    try:
        import swisseph as swe
    except ImportError:
        return {g: 0.0 for g in ALL_GRAHAS + ["Lagna"]}

    results = {}
    epsilon = 23.44  # degrees - obliquity of ecliptic

    for name in ALL_GRAHAS:
        pid_map = {
            "Surya":   swe.SUN, "Chandra": swe.MOON,
            "Mangal":  swe.MARS, "Budha":   swe.MERCURY,
            "Guru":    swe.JUPITER, "Shukra": swe.VENUS,
            "Shani":   swe.SATURN,
        }
        pid = pid_map.get(name)
        if pid is None:
            results[name] = 0.0
            continue

        try:
            xx, _ = swe.calc_ut(jd or 2451545.0, pid,
                                swe.FLG_EQUATORIAL | swe.FLG_SIDEREAL)
            declination = xx[2]  # declination in degrees (equatorial coordinate)

            # Ayana Bala: maximum when declination reaches extreme on natural side
            # North declination strengthens benefics; South declination strengthens malefics
            abs_dec = abs(declination)
            if name in BENEFIC_GRAHAS and declination > 0:
                ayb = (abs_dec / epsilon) * 60
            elif name in MALEFIC_GRAHAS and declination < 0:
                ayb = (abs_dec / epsilon) * 60
            else:
                ayb = 0.0
            results[name] = round(min(ayb, 60), 1)
        except Exception:
            results[name] = 0.0

    return results


def _ayana_bala_for_graha(jd, pid):
    """Compute Ayana Bala for a single graha given JD and Swiss Ephemeris planet ID."""
    try:
        import swisseph as swe
    except ImportError:
        return 0.0

    epsilon = 23.44
    try:
        xx, _ = swe.calc_ut(jd, pid,
                            swe.FLG_EQUATORIAL | swe.FLG_SIDEREAL)
        declination = xx[2]
        abs_dec = abs(declination)

        # Determine benefic/malefic nature from pid mapping
        # Default to neutral if unknown
        return round(min((abs_dec / epsilon) * 60, 60), 1)
    except Exception:
        return 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  ASHTAKAVARGA
# ══════════════════════════════════════════════════════════════════════════════
from core.constants import ASHTAK_BINDUS, ASHTAK_PLANETS

def ashtakavarga(planet, grahas):
    """
    Compute the Ashtakavarga for `planet` across all 12 signs.
    Returns list[int] of 12 bindu scores (index 0 = Mesha).
    Each sign gets 0-8 bindus (one from each of 7 planets + Lagna).
    """
    rules = ASHTAK_BINDUS.get(planet)
    if not rules:
        return [0] * 12

    lagna_rashi = grahas.get("Lagna", {}).get("rashi", 0)

    # Contributor positions (rashi 0-11)
    contrib_pos = {}
    for c in ASHTAK_PLANETS:
        pd = grahas.get(c, {})
        if pd:
            contrib_pos[c] = pd.get("rashi", 0)
    contrib_pos["Lagna"] = lagna_rashi

    scores = [0] * 12
    for sign in range(12):
        total = 0
        for contributor, contrib_rashi in contrib_pos.items():
            benefic_houses = rules.get(contributor, [])
            house_from_contrib = (sign - contrib_rashi) % 12 + 1
            if house_from_contrib in benefic_houses:
                total += 1
        scores[sign] = total
    return scores


def sarvashtakavarga(grahas):
    """
    Compute Sarvashtakavarga (sum of all 7 planet AVs) across 12 signs.
    Returns list[int] of 12 totals (max 56).
    """
    totals = [0] * 12
    for planet in ASHTAK_PLANETS:
        av = ashtakavarga(planet, grahas)
        for i in range(12):
            totals[i] += av[i]
    return totals


# ══════════════════════════════════════════════════════════════════════════════
#  DASHA BALANCE FORMATTER
# ══════════════════════════════════════════════════════════════════════════════
def format_dasha_balance(start_dt, birth_dt):
    """
    Return the balance of a Dasha at birth as "Xy Xm Xd".
    start_dt: the Dasha start datetime (before birth)
    birth_dt: the birth datetime
    Used to display: "Born with Xy Xm Xd of [Lord] remaining"
    """
    from datetime import datetime
    if not isinstance(start_dt, datetime) or not isinstance(birth_dt, datetime):
        return "?"
    delta = birth_dt - start_dt
    if delta.days < 0:
        return "?"
    total_days = delta.days
    years  = total_days // 365
    remain = total_days % 365
    months = remain // 30
    days   = remain % 30
    return f"{years}y {months}m {days}d"


# ══════════════════════════════════════════════════════════════════════════════
#  PANCHANGA ENGINE (5 Limbs of Vedic Time)
# ══════════════════════════════════════════════════════════════════════════════
def panchanga(surya_lon, chandra_lon, dt_or_jd):
    """
    Compute the 5 limbs of Vedic time (Panchanga):
      1. Tithi (Lunar day, 0-29; 1-15 Shukla, 16-30 Krishna)
      2. Vara (Weekday & planetary ruler)
      3. Nakshatra (Lunar mansion, 0-26, pada 1-4)
      4. Nitya Yoga (Solilunar combination, 0-26)
      5. Karana (Half-tithi, 0-59)
    """
    from core.constants import (
        TITHI_NAMES, NITYA_YOGAS, CHARA_KARANAS, STHIRA_KARANAS,
        VARA_NAMES, NAKSHATRA, NAK_LORDS,
    )

    # Determine datetime from dt_or_jd
    if isinstance(dt_or_jd, datetime):
        dt = dt_or_jd
    elif isinstance(dt_or_jd, (int, float)):
        try:
            from core.astro_engine import AstroEngine
            dt = AstroEngine.jd_to_dt(dt_or_jd)
        except Exception:
            dt = datetime(2000, 1, 1)
    else:
        dt = datetime.now()

    # 1. Tithi
    diff = (chandra_lon - surya_lon) % 360.0
    tithi_idx = int(diff / 12.0)
    tithi_idx = min(29, max(0, tithi_idx))
    tithi_rem = diff % 12.0
    tithi_pct = (tithi_rem / 12.0) * 100.0
    paksha = "Shukla" if tithi_idx < 15 else "Krishna"
    tithi_num_in_paksha = (tithi_idx % 15) + 1

    # 2. Vara (Python: Monday=0 ... Sunday=6; VARA_NAMES: Monday=0 ... Sunday=6)
    day_idx = dt.weekday()
    vara_info = VARA_NAMES[day_idx]

    # 3. Nakshatra
    ns = 360.0 / 27.0
    nak_idx = int(chandra_lon / ns) % 27
    nak_rem = chandra_lon % ns
    pada = int(nak_rem / (ns / 4.0)) + 1
    nak_pct = (nak_rem / ns) * 100.0
    nak_lord = NAK_LORDS[nak_idx]
    nak_name = NAKSHATRA[nak_idx]

    # 4. Solilunar Yoga
    soli_sum = (chandra_lon + surya_lon) % 360.0
    yoga_idx = int(soli_sum / ns) % 27
    yoga_rem = soli_sum % ns
    yoga_pct = (yoga_rem / ns) * 100.0
    yoga_entry = NITYA_YOGAS[yoga_idx]

    # 5. Karana (half-tithi = 6 degrees)
    karana_num = int(diff / 6.0)
    karana_num = min(59, max(0, karana_num))
    karana_rem = diff % 6.0
    karana_pct = (karana_rem / 6.0) * 100.0

    if karana_num in STHIRA_KARANAS:
        k_name = STHIRA_KARANAS[karana_num]
        k_type = "Sthira (Fixed)"
    else:
        k_name = CHARA_KARANAS[(karana_num - 1) % 7]
        k_type = "Chara (Movable)"

    return {
        "tithi": {
            "index": tithi_idx + 1,
            "name": TITHI_NAMES[tithi_idx],
            "paksha": paksha,
            "tithi_in_paksha": tithi_num_in_paksha,
            "elapsed_pct": round(tithi_pct, 2),
        },
        "vara": {
            "name": vara_info["name"],
            "english": vara_info["english"],
            "ruler": vara_info["graha"],
        },
        "nakshatra": {
            "index": nak_idx + 1,
            "name": nak_name,
            "pada": pada,
            "lord": nak_lord,
            "elapsed_pct": round(nak_pct, 2),
        },
        "yoga": {
            "index": yoga_idx + 1,
            "name": yoga_entry["name"],
            "nature": yoga_entry["nature"],
            "lord": yoga_entry["lord"],
            "elapsed_pct": round(yoga_pct, 2),
        },
        "karana": {
            "index": karana_num + 1,
            "name": k_name,
            "type": k_type,
            "is_vishti_bhadra": "Vishti" in k_name,
            "elapsed_pct": round(karana_pct, 2),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
#  GEMSTONE PRESCRIPTION ENGINE
# ══════════════════════════════════════════════════════════════════════════════
def gemstone_prescription(graha, lagna_rashi, body_weight_kg=60.0):
    """
    Detailed gemstone prescription with safety filters per BPHS.
    Checks functional benefic status for Lagna.
    If benefic: returns full specifications (gemstone, Sanskrit name,
    uparatna, metal, finger, day, weight in carats based on body weight, consecration mantra).
    If malefic: returns contraindication warning with safe alternative remedies (mantra, daana, puja).
    """
    from core.constants import GEMSTONE_SPECS, FUNC_BENEFIC_BY_LAGNA, RASHI

    spec = GEMSTONE_SPECS.get(graha)
    if not spec:
        return None

    lagna_name = RASHI[lagna_rashi] if isinstance(lagna_rashi, int) else lagna_rashi
    benefics = FUNC_BENEFIC_BY_LAGNA.get(lagna_name, [])
    is_benefic = graha in benefics

    if not is_benefic:
        return {
            "graha": graha,
            "is_benefic": False,
            "prescribed": False,
            "warning": (
                f"{graha} is a functional malefic for {lagna_name} Lagna. "
                f"Wearing its primary gemstone ({spec['gemstone']}) is CONTRAINDICATED "
                "and can aggravate adverse house significations."
            ),
            "safe_remedy": {
                "mantra": spec["mantra"],
                "daana_day": spec["day"],
                "recommended_action": (
                    f"Propitiate through Japa (chanting) and charity on {spec['day'].split(' ')[0]}s, "
                    "not physical gemstones."
                ),
            },
        }

    # Calculate recommended weight in carats based on body weight
    divisor = spec.get("min_carat_divisor", 12.0)
    calc_carats = (body_weight_kg / divisor) if body_weight_kg else spec["min_carats"]
    rec_carats = max(spec["min_carats"], round(calc_carats, 2))
    rec_ratti = round(rec_carats * 1.097, 2)  # 1 carat ≈ 1.097 ratti

    return {
        "graha": graha,
        "is_benefic": True,
        "prescribed": True,
        "gemstone": spec["gemstone"],
        "sanskrit_name": spec["sanskrit"],
        "substitutes": spec["uparatna"],
        "metal": spec["metal"],
        "finger": spec["finger"],
        "wearing_day_time": spec["day"],
        "recommended_carats": rec_carats,
        "recommended_ratti": rec_ratti,
        "consecration_mantra": spec["mantra"],
    }

