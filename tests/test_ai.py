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
        self.assertLessEqual(ctx, 8192)

    def test_thinking_stream_parser_isolation(self):
        """Verify ThinkingStreamParser isolates <think> blocks and routes tokens correctly."""
        from ai.ollama_engine import ThinkingStreamParser

        tokens_received = []
        thinking_received = []

        parser = ThinkingStreamParser(
            token_cb=lambda t: tokens_received.append(t),
            thinking_cb=lambda th: thinking_received.append(th),
        )

        # Feed chunks with thinking tags split across chunk boundaries
        parser.feed("<thi")
        parser.feed("nk>Let us analyze the 10th lord and Jupiter aspect.")
        parser.feed("</thi")
        parser.feed("nk>\n[SECTION: CAREER]\n[PREDICTION]: Professional success in strategic leadership.")
        parser.finish()

        full_thinking = "".join(thinking_received)
        full_tokens = "".join(tokens_received)

        self.assertIn("Let us analyze the 10th lord", full_thinking)
        self.assertNotIn("<think>", full_tokens)
        self.assertNotIn("</think>", full_tokens)
        self.assertNotIn("Let us analyze", full_tokens)
        self.assertIn("[PREDICTION]: Professional success", full_tokens)

    def test_thinking_stream_parser_plain_passthrough(self):
        """Verify ThinkingStreamParser delivers regular tokens with zero lag when no thinking tags exist."""
        from ai.ollama_engine import ThinkingStreamParser

        tokens = []
        parser = ThinkingStreamParser(token_cb=lambda t: tokens.append(t))

        parser.feed("Hello ")
        parser.feed("Vedic ")
        parser.feed("Astrology!")
        parser.finish()

        self.assertEqual("".join(tokens), "Hello Vedic Astrology!")

    def test_classical_rag_retrieval(self):
        """Verify ClassicalRAG retrieves grounded scriptural sutras matching chart placements."""
        from ai.rag_engine import ClassicalRAG

        sutras = ClassicalRAG.retrieve_context(
            grahas=self.grahas,
            yogas=self.yogas,
            doshas=self.doshas,
            dashas=self.dashas,
            domain="CAREER",
            max_rules=6,
        )
        self.assertIsInstance(sutras, str)
        self.assertIn("AUTHENTIC CLASSICAL DOCTRINE", sutras)
        # Should cite standard classical texts (BPHS / Phaladeepika)
        self.assertTrue("BPHS" in sutras or "Phaladeepika" in sutras or "Saravali" in sutras)

    def test_dual_layer_prompt_structure(self):
        """Verify PredictionEngine generates prompts demanding the Dual-Layer Explainable format."""
        full_p = PredictionEngine.user_prompt_full("{}", classical_doctrine="• [BPHS Ch. 24]: Karma Lord in Kendra")
        self.assertIn("[PREDICTION]", full_p)
        self.assertIn("[KUNDLI BASIS]", full_p)
        self.assertIn("[PRACTICAL GUIDANCE]", full_p)
        self.assertIn("BPHS Ch. 24", full_p)

        dd_p = PredictionEngine.user_prompt_deep_dive("{}", "CAREER")
        self.assertIn("[SECTION: CAREER", dd_p)
        self.assertIn("[PREDICTION]", dd_p)
        self.assertIn("[KUNDLI BASIS]", dd_p)

        cont_p = PredictionEngine.user_prompt_continuation("Prior cutoff text ending here")
        self.assertIn("continue generation seamlessly", cont_p.lower())

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

    def test_extract_temporal_context_specific_year(self):
        """Verify PredictionEngine accurately resolves past years to specific Dasha periods."""
        # Check year 2015
        record = PredictionEngine.extract_temporal_context(self.dashas, self.grahas, "How was my life back in 2015?")
        self.assertIn("HISTORICAL DASHA", record)
        self.assertIn("In Year 2015", record)
        self.assertIn("Mahadasha", record)

    def test_extract_temporal_context_previous_dasha(self):
        """Verify PredictionEngine resolves inquiries regarding previous dasha periods."""
        record = PredictionEngine.extract_temporal_context(self.dashas, self.grahas, "Tell me about my previous dasha period.")
        self.assertIn("HISTORICAL DASHA", record)
        self.assertIn("Previous Mahadasha", record)

    def test_dynamic_manuscript_bm25_retrieval(self):
        """Verify DynamicManuscriptRAG indexes and matches classical manuscripts with BM25."""
        from ai.manuscript_rag import DynamicManuscriptRAG
        DynamicManuscriptRAG.load_corpus()

        results = DynamicManuscriptRAG.search("career leadership authority", top_k=2)
        self.assertGreaterEqual(len(results), 1)
        self.assertIn("text", results[0])
        self.assertTrue("Brihat Parashara" in results[0]["work"] or "Phaladeepika" in results[0]["work"])


if __name__ == "__main__":
    unittest.main()
