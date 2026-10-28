# -*- coding: utf-8 -*-
"""
tests/test_core.py
==================
Unit tests for core calculation engines: astro_engine and vedic_engine.
"""

import unittest
from core.constants import ALL_GRAHAS
from core.astro_engine import compute_chart, resolve_timezone
from core.vedic_engine import (
    sthiti, varga, check_varga_boundary, compute_varga_chart,
    vimshottari, compute_pratyantardasha_for_ad, format_dasha_balance,
    yoga, dosha, shadbala, ashtakavarga, sarvashtakavarga,
    panchanga, gemstone_prescription,
)


class TestCoreEngines(unittest.TestCase):

    def setUp(self):
        # Sample test birth details (May 15, 1990, 12:30 IST, New Delhi)
        self.y, self.mo, self.d = 1990, 5, 15
        self.h, self.mi, self.tz = 12, 30, 5.5
        self.lat, self.lon = 28.6139, 77.2090
        self.ayanamsa = "Lahiri (Chitrapaksha)"
        self.grahas = compute_chart(
            self.y, self.mo, self.d, self.h, self.mi, self.tz,
            self.lat, self.lon, self.ayanamsa
        )
        self.lagna_rashi = self.grahas["Lagna"]["rashi"]

    def test_compute_chart_keys(self):
        """Verify all standard grahas and Lagna are present with valid longitudes."""
        for g in ALL_GRAHAS + ["Lagna"]:
            self.assertIn(g, self.grahas)
            lon = self.grahas[g].get("longitude")
            self.assertIsNotNone(lon)
            self.assertTrue(0.0 <= lon < 360.0, f"{g} longitude {lon} out of range [0, 360)")
            rashi = self.grahas[g].get("rashi")
            self.assertTrue(0 <= rashi < 12, f"{g} rashi {rashi} out of range [0, 12)")

    def test_sthiti_dignity(self):
        """Verify dignity classification returns expected strings."""
        for g in ALL_GRAHAS:
            st = sthiti(g, self.grahas[g]["rashi"])
            self.assertIn(st, ["Uchcha", "Moolatrikona", "Swakshetra", "Mitra", "Sama", "Shatru", "Neecha"])

    def test_varga_generation(self):
        """Verify D-9 Navamsa generation produces valid rashis for all grahas."""
        for g in ALL_GRAHAS + ["Lagna"]:
            lon = self.grahas[g]["longitude"]
            d9_r = varga(lon, 9)
            self.assertTrue(0 <= d9_r < 12, f"Varga D-9 rashi {d9_r} out of range for {g}")

    def test_vimshottari_dashas(self):
        """Verify Vimshottari dasha periods calculate without error."""
        chandra_lon = self.grahas["Chandra"]["longitude"]
        jd = self.grahas.get("_meta", {}).get("jd", 2448027.0)
        dashas = vimshottari(chandra_lon, jd)
        self.assertGreater(len(dashas), 0)
        first_md = dashas[0]
        self.assertIn("lord", first_md)
        self.assertIn("start", first_md)
        self.assertIn("end", first_md)
        self.assertIn("antardasha", first_md)

    def test_ashtakavarga(self):
        """Verify Ashtakavarga produces 12 bindus per planet and valid Sarva list."""
        for p in ["Surya", "Chandra", "Mangal", "Budha", "Guru", "Shukra", "Shani"]:
            b = ashtakavarga(p, self.grahas)
            self.assertEqual(len(b), 12)
            for score in b:
                self.assertTrue(0 <= score <= 8)
        sarva = sarvashtakavarga(self.grahas)
        self.assertEqual(len(sarva), 12)
        total_bindus = sum(sarva)
        self.assertGreater(total_bindus, 300)

    def test_shadbala_partial(self):
        """Verify shadbala component computation."""
        sb = shadbala("Surya", self.grahas, self.lagna_rashi)
        self.assertIn("uchcha_bala", sb)
        self.assertIn("cheshta", sb)
        self.assertIn("naisargika", sb)

    def test_yoga_and_dosha(self):
        """Verify yoga and dosha detection executes cleanly."""
        y_list = yoga(self.grahas, self.lagna_rashi)
        d_list = dosha(self.grahas, self.lagna_rashi)
        self.assertIsInstance(y_list, list)
        self.assertIsInstance(d_list, list)

    def test_vimshottari_depth_and_pratyantar(self):
        """Verify Vimshottari level 3/4 calculations and on-demand expansion."""
        chandra_lon = self.grahas["Chandra"]["longitude"]
        jd = self.grahas.get("_meta", {}).get("jd", 2448027.0)
        # Depth 3 with current_only_sub=False
        dashas_l3 = vimshottari(chandra_lon, jd, depth=3)
        self.assertIn("antardasha", dashas_l3[0])
        first_ad = dashas_l3[0]["antardasha"][0]
        self.assertIn("pratyantardasha", first_ad)
        self.assertEqual(len(first_ad["pratyantardasha"]), 9)

        # On-demand pratyantardasha expansion
        pds = compute_pratyantardasha_for_ad(first_ad, include_sookshma=True)
        self.assertEqual(len(pds), 9)
        self.assertIn("sookshmadasha", pds[0])
        self.assertEqual(len(pds[0]["sookshmadasha"]), 9)

    def test_varga_boundary_check(self):
        """Verify divisional chart boundary warnings."""
        # A longitude right near sign edge (0.01 deg in D-60)
        # D-60 sign is 0.5 deg. At 0.01 deg, it is near boundary.
        self.assertTrue(check_varga_boundary(0.01, 60))
        # At 0.25 deg, middle of D-60 division, not near boundary
        self.assertFalse(check_varga_boundary(0.25, 60))

        # Test compute_varga_chart returns structured dict with boundary_flag
        d9_chart = compute_varga_chart(self.grahas, 9)
        for gn in ALL_GRAHAS + ["Lagna"]:
            self.assertIn(gn, d9_chart)
            self.assertIn("boundary_flag", d9_chart[gn])
            self.assertIn("boundary_dist", d9_chart[gn])
            self.assertIn("varga_rashi", d9_chart[gn])

    def test_timezone_resolver(self):
        """Verify historical timezone resolution and DST detection."""
        # New York in July (DST active -> EDT, -4.0)
        res_summer = resolve_timezone("America/New_York", 2023, 7, 1, 12, 0)
        self.assertEqual(res_summer["utc_offset"], -4.0)
        self.assertTrue(res_summer["is_dst"])

        # New York in January (DST inactive -> EST, -5.0)
        res_winter = resolve_timezone("America/New_York", 2023, 1, 1, 12, 0)
        self.assertEqual(res_winter["utc_offset"], -5.0)
        self.assertFalse(res_winter["is_dst"])

        # Test chart computation with iana_tz
        chart_ny = compute_chart(
            2023, 7, 1, 12, 0, tz=None, lat=40.7128, lon_geo=-74.0060,
            ayanamsa_key="Lahiri (Chitrapaksha)", iana_tz="America/New_York"
        )
        self.assertEqual(chart_ny["_meta"]["iana_tz"], "America/New_York")
        self.assertTrue(chart_ny["_meta"]["is_dst"])

    def test_panchanga(self):
        """Verify 5 limbs of Vedic time calculation."""
        surya_lon = self.grahas["Surya"]["longitude"]
        chandra_lon = self.grahas["Chandra"]["longitude"]
        jd = self.grahas["_meta"]["jd"]
        p = panchanga(surya_lon, chandra_lon, jd)

        self.assertIn("tithi", p)
        self.assertIn("vara", p)
        self.assertIn("nakshatra", p)
        self.assertIn("yoga", p)
        self.assertIn("karana", p)

        self.assertTrue(1 <= p["tithi"]["index"] <= 30)
        self.assertIn(p["tithi"]["paksha"], ["Shukla", "Krishna"])
        self.assertTrue(1 <= p["nakshatra"]["pada"] <= 4)
        self.assertIn(p["yoga"]["nature"], ["Shubha", "Ashubha"])

    def test_gemstone_prescription(self):
        """Verify gemstone safety filter and prescription parameters."""
        # For Mesha Lagna (index 0): Surya, Chandra, Mangal, Guru are functional benefics
        # Shani, Budha, Shukra are functional malefics
        g_surya = gemstone_prescription("Surya", 0, body_weight_kg=70.0)
        self.assertTrue(g_surya["prescribed"])
        self.assertEqual(g_surya["gemstone"], "Ruby")
        self.assertGreater(g_surya["recommended_carats"], 3.0)

        # Shani is malefic for Mesha Lagna -> should be contraindicated
        g_shani = gemstone_prescription("Shani", 0)
        self.assertFalse(g_shani["prescribed"])
        self.assertIn("CONTRAINDICATED", g_shani["warning"])
        self.assertIn("safe_remedy", g_shani)


if __name__ == "__main__":
    unittest.main()
