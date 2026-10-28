# -*- coding: utf-8 -*-
"""
tests/test_ai.py
================
Unit tests for AI payload construction and prompt helpers.
"""

import unittest
from core.astro_engine import compute_chart
from core.vedic_engine import yoga, dosha, vimshottari
from ai.prediction_engine import PredictionEngine, ContextCompressor, ConversationManager
from ai.ollama_engine import _dynamic_ctx


class TestAIEngine(unittest.TestCase):

    def setUp(self):
        self.y, self.mo, self.d = 1990, 5, 15
        self.h, self.mi, self.tz = 12, 30, 5.5
        self.lat, self.lon = 28.6139, 77.2090
        self.ayanamsa = "Lahiri (Chitrapaksha)"
        self.grahas = compute_chart(
            self.y, self.mo, self.d, self.h, self.mi, self.tz,
            self.lat, self.lon, self.ayanamsa
        )
        lr = self.grahas["Lagna"]["rashi"]
        self.yogas = yoga(self.grahas, lr)
        self.doshas = dosha(self.grahas, lr)
        chandra_lon = self.grahas["Chandra"]["longitude"]
        jd = self.grahas["_meta"]["jd"]
        self.dashas = vimshottari(chandra_lon, jd)

    def test_chart_json_structure(self):
        """Verify minified chart JSON builds expected sections."""
        payload_str = PredictionEngine.chart_json(self.grahas, self.yogas, self.doshas, self.dashas)
        self.assertIsInstance(payload_str, str)
        self.assertIn("grahas", payload_str)
        self.assertIn("dasha", payload_str)
        self.assertIn("yogas", payload_str)
        self.assertIn("doshas", payload_str)

    def test_dynamic_ctx(self):
        """Verify dynamic context calculation clamps within limits."""
        ctx = _dynamic_ctx("system prompt here", "user question here")
        self.assertGreaterEqual(ctx, 1024)
        self.assertLessEqual(ctx, 3072)

    def test_domain_detection(self):
        """Verify intelligent semantic domain classification for astrological questions."""
        self.assertEqual(ContextCompressor.detect_domain("When will I get a promotion in my career?"), "CAREER")
        self.assertEqual(ContextCompressor.detect_domain("Tell me about my marriage and relationship with spouse"), "RELATIONSHIPS")
        self.assertEqual(ContextCompressor.detect_domain("How will my wealth and financial investments perform?"), "FINANCE")
        self.assertEqual(ContextCompressor.detect_domain("Any illness or health recovery timeline?"), "HEALTH")
        self.assertEqual(ContextCompressor.detect_domain("Which gemstone or puja remedy should I perform?"), "REMEDIES")
        self.assertEqual(ContextCompressor.detect_domain("When does my next mahadasha and antardasha period start?"), "TIMING_DASHA")
        self.assertEqual(ContextCompressor.detect_domain("General life outlook"), "GENERAL")

    def test_context_compressor_pruning(self):
        """Verify chart payload pruning focuses on domain-pertinent bhavas and significators."""
        payload_str = PredictionEngine.chart_json(self.grahas, self.yogas, self.doshas, self.dashas)
        compressed = ContextCompressor.compress_chart_for_domain(payload_str, "CAREER")
        self.assertIsInstance(compressed, str)
        self.assertIn('"domain": "CAREER"', compressed)
        self.assertIn("pertinent_grahas", compressed)
        self.assertIn("other_grahas_summary", compressed)

    def test_conversation_manager_isolation_and_compression(self):
        """Verify ConversationManager resets context between charts and records rolling takeaways."""
        mgr = ConversationManager()
        mgr.reset_for_new_chart("CHART_001", "Native One")
        self.assertTrue(mgr.is_current_chart("CHART_001"))
        self.assertFalse(mgr.is_current_chart("CHART_002"))

        # Q&A Turn 1
        raw_payload = PredictionEngine.chart_json(self.grahas, self.yogas, self.doshas, self.dashas)
        prompt, domain = mgr.build_qa_prompt(raw_payload, "What career path suits me best?")
        self.assertEqual(domain, "CAREER")
        self.assertIn("CAREER", prompt)

        ans1 = "• 10th house has strong Jupiter aspect favoring teaching.\n• Saturn in 6th house indicates success in competitive exams."
        mgr.record_turn("What career path suits me best?", ans1, domain)
        self.assertEqual(len(mgr.turns), 1)
        self.assertGreaterEqual(len(mgr.compressed_findings), 1)

        # Context isolation reset on new Kundali
        mgr.reset_for_new_chart("CHART_002", "Native Two")
        self.assertTrue(mgr.is_current_chart("CHART_002"))
        self.assertEqual(len(mgr.turns), 0)
        self.assertEqual(len(mgr.compressed_findings), 0)


if __name__ == "__main__":
    unittest.main()
