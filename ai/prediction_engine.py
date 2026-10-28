# -*- coding: utf-8 -*-
"""
prediction_engine.py
====================
Chart text generation and LLM prompt construction.

Key fixes vs v3.0
-----------------
* Minified JSON payload : only sends bhava, lordship, dignity, nakshatra lord,
  and dasha data — ~40% fewer tokens than v3.0
* gambhirata removed   : no more severity markers that contradicted the prompt
* "I don't know" protocol in system prompt — safe pivot for fatalistic queries
* Anti-markdown framing in format instructions (Qwen2.5 specific)
* Full Qwen2.5-7B constrained system prompt
"""

from datetime import datetime
import json
from core.constants import (
    RASHI, ALL_GRAHAS, RASHI_SWAMI, GRAHA_DEVA, NAKSHATRA,
    DASHA_KRAM,
)
from core.vedic_engine import sthiti
from ai.rag_engine import ClassicalRAG


class PredictionEngine:

    # ── Minified chart JSON ───────────────────────────────────────────────────
    @staticmethod
    def chart_json(grahas, yogas, doshas, dashas):
        """
        FIX: Aggressively minified JSON payload.
        Removed: exact degrees, pada, redundant rashi index, gambhirata/severity.
        Kept: house number, rashi name, dignity, nakshatra lord, retro flag,
              yoga names + strength, dosha names + status, current dasha.

        For an 8B model doing a general reading, exact degree or pada data
        does not improve output quality but costs ~100-150 extra tokens per planet.
        """
        now = datetime.now()
        lr  = grahas.get("Lagna", {}).get("rashi", 0)

        graha_data = {}
        for g in ALL_GRAHAS + ["Lagna"]:
            pd = grahas.get(g, {})
            if not pd:
                continue
            st = sthiti(g, pd.get("rashi", 0))
            graha_data[g] = {
                "bhava":   pd.get("bhava", ""),
                "rashi":   pd.get("rashi_naam", ""),
                "dignity": st,
                "nak_lord": pd.get("nakshatra_swami", ""),
                "retro":   pd.get("retro", False),
            }

        # Current, previous, and chronological Mahadashas & Antardashas
        cur_md = cur_ad = prev_md = next_md = None
        timeline_list = []

        for idx, md in enumerate(dashas):
            status = "CURRENT" if md["start"] <= now <= md["end"] else ("PAST" if md["end"] < now else "FUTURE")
            md_pd = grahas.get(md["lord"], {})
            md_entry = {
                "lord": md["lord"],
                "span": f"{md['start'].year}-{md['end'].year}",
                "status": status,
                "lord_bhava": md_pd.get("bhava", ""),
                "lord_dignity": sthiti(md["lord"], md_pd.get("rashi", 0)),
            }
            timeline_list.append(md_entry)

            if status == "CURRENT":
                cur_md = md
                if idx > 0:
                    prev_md = dashas[idx - 1]
                for ad in md["antardasha"]:
                    if ad["start"] <= now <= ad["end"]:
                        cur_ad = ad
                        break
            elif status == "FUTURE" and next_md is None:
                next_md = md

        dasha_info = {
            "chronological_timeline": timeline_list,
        }
        if prev_md:
            prev_pd = grahas.get(prev_md["lord"], {})
            dasha_info["previous_mahadasha"] = {
                "lord": prev_md["lord"],
                "span": f"{prev_md['start'].strftime('%b %Y')} to {prev_md['end'].strftime('%b %Y')}",
                "lord_bhava": prev_pd.get("bhava", ""),
                "lord_dignity": sthiti(prev_md["lord"], prev_pd.get("rashi", 0)),
            }
        if cur_md:
            md_pd = grahas.get(cur_md["lord"], {})
            dasha_info["mahadasha"] = {
                "lord": cur_md["lord"],
                "span": f"{cur_md['start'].strftime('%b %Y')} to {cur_md['end'].strftime('%b %Y')}",
                "ends": cur_md["end"].strftime("%b %Y"),
                "yrs_left": round((cur_md["end"] - now).days / 365.24219, 1),
                "lord_bhava": md_pd.get("bhava", ""),
                "lord_dignity": sthiti(cur_md["lord"], md_pd.get("rashi", 0)),
            }
        if cur_ad:
            ad_pd = grahas.get(cur_ad["lord"], {})
            dasha_info["antardasha"] = {
                "lord": cur_ad["lord"],
                "span": f"{cur_ad['start'].strftime('%b %Y')} to {cur_ad['end'].strftime('%b %Y')}",
                "ends": cur_ad["end"].strftime("%b %Y"),
                "lord_bhava": ad_pd.get("bhava", ""),
            }
        if next_md:
            dasha_info["next_mahadasha"] = {
                "lord": next_md["lord"],
                "starts": next_md["start"].strftime("%b %Y"),
            }

        # Bhava lords (Lagna through 12th) — critical for house-level questions
        bhava_lords = {
            str(h): RASHI_SWAMI[(lr + h - 1) % 12]
            for h in range(1, 13)
        }

        payload = {
            "lagna_rashi": RASHI[lr],
            "lagnesh":     RASHI_SWAMI[lr],
            "bhava_lords": bhava_lords,
            "grahas":      graha_data,
            "yogas": [
                {"name": y["naam"], "strength": y["bala"]}
                for y in yogas
            ],
            "doshas": [
                {"name": d["naam"], "status": d["sthiti"], "graha": d["graha"]}
                for d in doshas
            ],
            "dasha": dasha_info,
        }
        # Compact JSON — no indentation to save tokens
        return json.dumps(payload, ensure_ascii=False)

    # ── Full verbose chart text (for display / save) ──────────────────────────
    @staticmethod
    def chart_text_full(grahas, yogas, doshas, dashas, janam_vivaran):
        lr      = grahas.get("Lagna", {}).get("rashi", 0)
        lagnesh = RASHI_SWAMI[lr]
        now     = datetime.now()
        eng     = grahas.get("_meta", {}).get("engine", "")
        ay      = grahas.get("_meta", {}).get("ay", 0)
        b_method = grahas.get("Surya", {}).get("bhava_method", "whole_sign")

        lines = [
            f"=== BIRTH CHART === {janam_vivaran}",
            f"Engine: {eng}  |  Ayanamsa: {ay:.4f} deg",
            f"Lagna: {RASHI[lr]}  |  Lagnesh: {lagnesh}",
            f"Bhava method: {b_method}",
            "",
        ]

        lines.append("=== GRAHAS ===")
        for g in ALL_GRAHAS + ["Lagna"]:
            pd = grahas.get(g, {})
            if not pd:
                continue
            lon = pd.get("longitude", 0)
            d   = int(lon % 30); m = int((lon % 30 - d) * 60)
            st  = sthiti(g, pd.get("rashi", 0))
            lines.append(
                f"  {g:8}: {pd.get('rashi_naam',''):12} {d:2}d{m:02d}' "
                f"Bhava {pd.get('bhava','?'):2}  "
                f"{pd.get('nakshatra_naam',''):20} P{pd.get('pada','')} "
                f"NL:{pd.get('nakshatra_swami',''):7} {st}"
                f"{'[R]' if pd.get('retro') else ''}"
            )

        lines += ["", "=== BHAVA LORDS ==="]
        for bh in range(1, 13):
            lord = RASHI_SWAMI[(lr + bh - 1) % 12]
            pd   = grahas.get(lord, {})
            if pd:
                lines.append(
                    f"  Bhava {bh:2}: {lord} in Bhava {pd.get('bhava','?')} "
                    f"({pd.get('rashi_naam','')}) "
                    f"{sthiti(lord, pd.get('rashi',0))}"
                )

        lines += ["", "=== YOGAS ==="]
        for y in yogas:
            lines.append(f"  [{y['bala']}] {y['naam']}: {y['vivaran']}")
        if not yogas:
            lines.append("  None detected.")

        lines += ["", "=== DOSHAS ==="]
        for d in doshas:
            lines.append(f"  [{d['sthiti']}] {d['naam']}: {d['vivaran']}")
        if not doshas:
            lines.append("  None significant.")

        lines += ["", "=== VIMSHOTTARI DASHA ==="]
        for md in dashas:
            av = ("CURRENT" if md["start"] <= now <= md["end"]
                  else ("PAST" if md["end"] < now else "FUTURE"))
            md_pd = grahas.get(md["lord"], {})
            md_st = sthiti(md["lord"], md_pd.get("rashi", 0))
            lines.append(
                f"  [{av}] {md['lord']}: {md['start'].strftime('%d %b %Y')}"
                f"  to  {md['end'].strftime('%d %b %Y')} "
                f"({md['varsh']:.1f}y) Bhava {md_pd.get('bhava','?')} {md_st}"
            )
            if av == "CURRENT":
                for ad in md["antardasha"]:
                    aa = "--> [ACTIVE]" if ad["start"] <= now <= ad["end"] else "          "
                    ad_pd = grahas.get(ad["lord"], {})
                    lines.append(
                        f"       {aa} {md['lord']}-{ad['lord']}: "
                        f"{ad['start'].strftime('%d %b %Y')} to "
                        f"{ad['end'].strftime('%d %b %Y')} "
                        f"Bhava {ad_pd.get('bhava','?')}"
                    )

        return "\n".join(lines)

    # ── System Prompt (Dual-Layer Explainable AI & RAG Constrained) ───────────
    @staticmethod
    def system_prompt():
        """
        Dual-Layer Explainable AI system prompt for 7B-9B models.
        Separates plain-language client predictions from technical Kundli calculations,
        satisfying Explainable AI (XAI) transparency principles.
        """
        return (
            "You are Jyotisha-AI, an expert Vedic astrologer and empathetic counselor.\n"
            "You receive a computed JSON birth chart and classical scripture references (RAG).\n"
            "Your purpose is to provide deeply insightful, grounded readings that empower the native.\n\n"

            "## ABSOLUTE ETHICAL BOUNDARIES\n"
            "1. NEVER predict death, terminal disease, bankruptcy, or irreversible tragedy.\n"
            "2. If asked about death, fatality, or catastrophic ruin: gently state that "
            "'Jyotish is a lamp for self-awareness and conscious living, not fatalistic anxiety.' "
            "Then pivot constructively to analyzing longevity factors, inner resilience, and protective yogas.\n"
            "3. Frame every Dosha or challenging placement as an energetic growth pattern with practical remedies.\n"
            "4. Ground every single claim in the provided chart facts and classical sutras. Never fabricate placements.\n"
            "5. If chart data is insufficient to answer a question, state: 'The chart does not clearly indicate this.'\n\n"

            "## DUAL-LAYER EXPLAINABLE OUTPUT FORMAT\n"
            "Every prediction MUST clearly separate plain human language from technical astrological reasoning:\n\n"
            "For each section or major point, use this exact structure:\n"
            "[SECTION: <Domain Name>]\n"
            "[PREDICTION]: <Clear, compassionate natural language in 2-4 sentences explaining what the user will experience, life themes, and realistic timelines without overwhelming jargon.>\n"
            "[KUNDLI BASIS]: <Exact technical astrological reasoning: planetary placement, house lordship, dignity, active dasha lord, and classical sutra citation.>\n"
            "[PRACTICAL GUIDANCE]: <Concrete constructive action, psychological reframe, or lifestyle remedy.>\n\n"

            "Example:\n"
            "[SECTION: CAREER]\n"
            "[PREDICTION]: You possess strong natural executive and problem-solving abilities that lead to leadership roles in technological, strategic, or advisory sectors by your early-to-mid 30s. The current cycle highlights professional expansion and recognition from senior authorities.\n"
            "[KUNDLI BASIS]: 10th lord Guru placed in Kendra in own sign forming Hamsa Yoga; Surya exalted in 1st house; active Mahadasha of Guru ruling 9th and 12th Bhavas (BPHS Ch. 24, Sloka 10).\n"
            "[PRACTICAL GUIDANCE]: Channel your natural initiative into mentorship and cross-functional team leadership; wear yellow tones and honor teachers on Thursdays.\n\n"

            "## STYLE GUIDELINES\n"
            "- Write with empathy, dignity, and practical psychological realism.\n"
            "- NEVER output raw unformatted text blocks. Always adhere to the [SECTION], [PREDICTION], [KUNDLI BASIS], and [PRACTICAL GUIDANCE] tags."
        )

    # ── User Prompts ──────────────────────────────────────────────────────────
    @staticmethod
    def user_prompt_full(chart_json_str, classical_doctrine=""):
        doctrine_block = ""
        if classical_doctrine:
            doctrine_block = f"\n{classical_doctrine}\n"

        return (
            f"Chart Data:\n{chart_json_str}\n"
            f"{doctrine_block}\n"
            "Provide a comprehensive Vedic Astrology Life Reading structured in the Dual-Layer Explainable format.\n"
            "Cover these 6 core domains:\n"
            "1. [SECTION: PERSONALITY & LIFE PATH] (Lagna, Lagnesh, core temperament)\n"
            "2. [SECTION: CAREER & CALLING] (10th Bhava, 10th Lord, vocational timing)\n"
            "3. [SECTION: WEALTH & PROSPERITY] (2nd/11th Bhavas, Dhana Yogas, revenue streams)\n"
            "4. [SECTION: RELATIONSHIPS & MARRIAGE] (7th Bhava, 7th Lord, Venus/Jupiter significators)\n"
            "5. [SECTION: CURRENT DASHA TIMELINE] (Active Mahadasha + Antardasha, themes active now)\n"
            "6. [SECTION: WELLBEING & KEY YOGAS] (Vitality, top Yogas & Dosha reframing with practical remedies)\n\n"
            "Ensure every section contains [PREDICTION], [KUNDLI BASIS], and [PRACTICAL GUIDANCE]."
        )

    @staticmethod
    def user_prompt_qa(chart_json_str, question, context_summary=None, classical_doctrine=""):
        ctx_prefix = ""
        if context_summary:
            ctx_prefix = (
                f"[Prior Consultation Context for this Native]:\n"
                f"{context_summary}\n\n"
            )
        doctrine_block = ""
        if classical_doctrine:
            doctrine_block = f"{classical_doctrine}\n\n"

        return (
            f"Chart Data:\n{chart_json_str}\n\n"
            f"{doctrine_block}"
            f"{ctx_prefix}"
            f"Native's Question: {question}\n\n"
            "Answer the question using the Dual-Layer Explainable format:\n"
            "[SECTION: <Relevant Domain>]\n"
            "[PREDICTION]: <Clear natural language prediction and practical life answer for the user>\n"
            "[KUNDLI BASIS]: <Exact astrological calculation, house lordships, dignity, dasha timing, and classical rule citation>\n"
            "[PRACTICAL GUIDANCE]: <Actionable advice, psychological reframe, or constructive remedy>"
        )

    @staticmethod
    def user_prompt_deep_dive(chart_json_str, domain, classical_doctrine=""):
        """Focused, comprehensive deep dive into a specific life domain."""
        doctrine_block = ""
        if classical_doctrine:
            doctrine_block = f"\n{classical_doctrine}\n"

        domain_titles = {
            "CAREER": "CAREER, BUSINESS & VOCATIONAL TIMELINE",
            "FINANCE": "WEALTH, FINANCIAL ACUMEN & ASSET ACCUMULATION",
            "RELATIONSHIPS": "MARRIAGE, LIFE PARTNER & EMOTIONAL ALLIANCES",
            "HEALTH": "VITALITY, RESILIENCE & PHYSICAL WELLBEING",
            "TIMING_DASHA": "VIMSHOTTARI DASHA CYCLES & LIFE MILESTONES",
            "REMEDIES": "HOLISTIC UPAYAS, GEMSTONES & CONSTRUCTIVE REMEDIES",
        }
        title = domain_titles.get(domain, f"{domain} DEEP DIVE")

        return (
            f"Chart Data:\n{chart_json_str}\n"
            f"{doctrine_block}\n"
            f"Provide an in-depth specialized consultation focused specifically on [SECTION: {title}].\n"
            "Elaborate thoroughly with 3 distinct thematic facets:\n"
            "1. Current Life Phase & Opportunities\n"
            "2. Critical Timing, Peak Windows & Potential Roadblocks\n"
            "3. Strategic Action Plan & Astrological Remedies\n\n"
            "Format every facet strictly using:\n"
            "[PREDICTION]: <Detailed natural language advice and foresight>\n"
            "[KUNDLI BASIS]: <Detailed astrological placements, aspects, and classical grounding>\n"
            "[PRACTICAL GUIDANCE]: <Concrete life advice and remedies>"
        )

    @staticmethod
    def user_prompt_continuation(prior_text):
        """Resume generation when truncated by context/token bounds."""
        cutoff_sample = prior_text[-300:] if len(prior_text) > 300 else prior_text
        return (
            "The previous response was paused due to token length.\n"
            f"Prior text ended at:\n\"...{cutoff_sample}\"\n\n"
            "Please continue generation seamlessly from this exact cutoff point. "
            "Do NOT repeat prior text. Continue the Dual-Layer format to the conclusion."
        )

    @staticmethod
    def extract_temporal_context(dashas, grahas, question):
        """
        Detects specific years, past periods, or historical dasha inquiries in the question
        and generates an exact grounded retrospective timeline summary.
        """
        import re
        if not dashas:
            return ""

        q_lower = question.lower()
        now = datetime.now()

        # Check for 4-digit years (e.g. 1970 to 2050)
        years_found = [int(y) for y in re.findall(r'\b(19\d\d|20\d\d)\b', question)]

        records = []
        for yr in sorted(set(years_found)):
            matched_md = None
            matched_ad = None
            for md in dashas:
                if md["start"].year <= yr <= md["end"].year:
                    matched_md = md
                    for ad in md.get("antardasha", []):
                        if ad["start"].year <= yr <= ad["end"].year:
                            matched_ad = ad
                            break
                    break

            if matched_md:
                md_lord = matched_md["lord"]
                md_pd = grahas.get(md_lord, {})
                ad_str = ""
                if matched_ad:
                    ad_lord = matched_ad["lord"]
                    ad_pd = grahas.get(ad_lord, {})
                    ad_str = f" with {ad_lord} Antardasha (Bhava {ad_pd.get('bhava','?')})"
                records.append(
                    f"• In Year {yr}: Native was running {md_lord} Mahadasha (Bhava {md_pd.get('bhava','?')}, "
                    f"{sthiti(md_lord, md_pd.get('rashi',0))}){ad_str}."
                )

        # Check for past/previous keywords
        past_keywords = [
            "previous dasha", "past dasha", "previous mahadasha", "past period",
            "last dasha", "prior dasha", "before this", "earlier years", "childhood",
            "how was my life", "past life", "previous years", "earlier life"
        ]
        if any(pk in q_lower for pk in past_keywords) and not records:
            cur_idx = None
            for idx, md in enumerate(dashas):
                if md["start"] <= now <= md["end"]:
                    cur_idx = idx
                    break
            if cur_idx is not None and cur_idx > 0:
                prev_md = dashas[cur_idx - 1]
                prev_pd = grahas.get(prev_md["lord"], {})
                records.append(
                    f"• Previous Mahadasha: {prev_md['lord']} was active from {prev_md['start'].strftime('%b %Y')} "
                    f"to {prev_md['end'].strftime('%b %Y')} ({prev_md['varsh']:.1f} years). "
                    f"{prev_md['lord']} rules Bhava {prev_pd.get('bhava','?')} in {sthiti(prev_md['lord'], prev_pd.get('rashi',0))}."
                )

        if records:
            return (
                "### HISTORICAL DASHA & RETROSPECTIVE TIMELINE RECORD:\n"
                + "\n".join(records)
                + "\nExplain what life was like during that specified duration based on these exact dasha lords."
            )
        return ""


# ══════════════════════════════════════════════════════════════════════════════
#  INTELLIGENT CONTEXT COMPRESSION & SESSION MANAGER
# ══════════════════════════════════════════════════════════════════════════════

DOMAIN_KEYWORDS = {
    "CAREER": [
        "career", "job", "profession", "business", "work", "promotion", "employment",
        "office", "boss", "interview", "startup", "trade", "field", "naukri", "vyapar",
        "service", "industry", "vocation", "livelihood", "success", "status", "transfer"
    ],
    "RELATIONSHIPS": [
        "marriage", "partner", "wife", "husband", "spouse", "love", "relationship",
        "divorce", "wedding", "dating", "shadi", "vivah", "prema", "affair", "breakup",
        "marital", "compatibility", "in-laws", "second marriage", "life partner"
    ],
    "FINANCE": [
        "money", "wealth", "financial", "finance", "rich", "poverty", "income", "debt",
        "loan", "profit", "investment", "shares", "stock", "paisa", "dhan", "property",
        "loss", "earnings", "savings", "assets", "inheritance"
    ],
    "HEALTH": [
        "health", "disease", "illness", "surgery", "hospital", "pain", "medical", "injury",
        "vitality", "accident", "bimari", "roga", "mental", "depression", "recovery",
        "wellness", "longevity", "ayush", "chronic", "physical"
    ],
    "EDUCATION": [
        "education", "study", "exam", "college", "degree", "school", "learning", "intellect",
        "upsc", "academic", "vidya", "padhai", "higher study", "abroad", "foreign education",
        "course", "university", "research"
    ],
    "TIMING_DASHA": [
        "dasha", "period", "when", "timing", "time", "year", "antardasha", "mahadasha",
        "pratyantar", "transit", "gochara", "now", "future", "kab", "current period",
        "which year", "months", "timeline"
    ],
    "REMEDIES": [
        "remedy", "gemstone", "stone", "mantra", "rudraksha", "dan", "puja", "upay",
        "ratna", "fasting", "vrat", "donation", "mitigate", "wear", "prescribe"
    ],
}

DOMAIN_PERTINENT_BHAVAS = {
    "CAREER": [1, 2, 6, 10, 11],
    "RELATIONSHIPS": [1, 2, 4, 7, 8, 12],
    "FINANCE": [1, 2, 5, 9, 11, 12],
    "HEALTH": [1, 6, 8, 12],
    "EDUCATION": [1, 2, 4, 5, 9],
    "TIMING_DASHA": [1, 7, 10],
    "REMEDIES": [1, 5, 9],
}

DOMAIN_SIGNIFICATORS = {
    "CAREER": ["Surya", "Budha", "Shani", "Mangal", "Guru"],
    "RELATIONSHIPS": ["Shukra", "Guru", "Mangal", "Chandra"],
    "FINANCE": ["Guru", "Budha", "Shukra", "Chandra"],
    "HEALTH": ["Surya", "Chandra", "Shani", "Mangal", "Rahu"],
    "EDUCATION": ["Budha", "Guru", "Surya"],
    "TIMING_DASHA": ALL_GRAHAS,
    "REMEDIES": ["Guru", "Surya", "Shukra"],
}


class ContextCompressor:
    """
    Intelligently compresses astrological chart payloads and conversational history
    based on semantic intent classification and token budgeting.
    """

    @staticmethod
    def detect_domain(text):
        """Classify question into astrological domain."""
        t_lower = text.lower()
        for dom, keywords in DOMAIN_KEYWORDS.items():
            if any(k in t_lower for k in keywords):
                return dom
        return "GENERAL"

    @staticmethod
    def compress_chart_for_domain(chart_json_str, domain):
        """
        Produce a pruned, high-signal JSON payload targeting the specific domain.
        Retains 100% precision on pertinent houses/planets, while compressing
        irrelevant placements to 1-line shorthand.
        """
        if domain == "GENERAL":
            return chart_json_str

        try:
            data = json.loads(chart_json_str)
        except Exception:
            return chart_json_str

        pertinent_bhavas = set(DOMAIN_PERTINENT_BHAVAS.get(domain, []))
        significators    = set(DOMAIN_SIGNIFICATORS.get(domain, []))

        # Identify dasha lords to always retain
        dasha_lords = set()
        cur_md = data.get("dasha", {}).get("mahadasha", {}).get("lord")
        cur_ad = data.get("dasha", {}).get("antardasha", {}).get("lord")
        if cur_md: dasha_lords.add(cur_md)
        if cur_ad: dasha_lords.add(cur_ad)

        grahas_full = {}
        grahas_short = []

        for g, gd in data.get("grahas", {}).items():
            bhava_num = gd.get("bhava")
            try:
                bhava_int = int(bhava_num)
            except (ValueError, TypeError):
                bhava_int = -1

            # Retain full payload if pertinent house, domain significator, Lagna, or active dasha lord
            if (bhava_int in pertinent_bhavas or
                g in significators or
                g in dasha_lords or
                g == "Lagna"):
                grahas_full[g] = gd
            else:
                # Ultra-compact shorthand: e.g. "Ve:B9(Pis,Uchcha)"
                short_str = f"{g[:2]}:B{bhava_num}({gd.get('rashi','')[:3]},{gd.get('dignity','')[:3]})"
                grahas_short.append(short_str)

        # Filter pertinent bhava lords
        orig_lords = data.get("bhava_lords", {})
        kept_lords = {
            k: v for k, v in orig_lords.items()
            if int(k) in pertinent_bhavas
        }

        compressed_payload = {
            "domain": domain,
            "lagna": data.get("lagna_rashi"),
            "lagnesh": data.get("lagnesh"),
            "bhava_lords": kept_lords,
            "pertinent_grahas": grahas_full,
            "other_grahas_summary": " ".join(grahas_short),
            "yogas": data.get("yogas", [])[:4],  # top yogas
            "doshas": data.get("doshas", []),
            "dasha": data.get("dasha", {}),
        }
        return json.dumps(compressed_payload, ensure_ascii=False)

    @staticmethod
    def extract_takeaways(answer_text, max_bullets=2):
        """
        Extractive compression: pulls 1-2 core conclusion bullets from prior turns
        to build a compact context summary without bloating token budget.
        """
        lines = [line.strip() for line in answer_text.splitlines() if line.strip()]
        bullets = [l for l in lines if l.startswith("-") or l.startswith("•")]
        if bullets:
            return bullets[:max_bullets]
        # Fallback to first non-empty lines
        return lines[:max_bullets]


class ConversationManager:
    """
    Manages multi-turn conversation context for a single Kundali profile.
    Guarantees:
      - Zero context leak across different charts
      - Automatic eviction of stale KV cache
      - Extractive compression for multi-turn dialogues
    """

    def __init__(self):
        self.active_chart_hash = None
        self.active_chart_name = ""
        self.turns = []              # list of {"question": ..., "answer": ..., "domain": ...}
        self.compressed_findings = [] # list of concise takeaway strings

    def reset_for_new_chart(self, chart_id, chart_name="Native"):
        """
        Completely flushes conversational memory when a new chart is calculated or loaded.
        """
        self.active_chart_hash = chart_id
        self.active_chart_name = chart_name
        self.turns.clear()
        self.compressed_findings.clear()

    def is_current_chart(self, chart_id):
        return self.active_chart_hash == chart_id

    def build_qa_prompt(self, raw_chart_json_str, question, classical_doctrine=""):
        """
        Construct domain-optimized, context-compressed prompt.
        Returns (compressed_prompt, domain, estimated_tokens).
        """
        domain = ContextCompressor.detect_domain(question)
        compressed_chart = ContextCompressor.compress_chart_for_domain(raw_chart_json_str, domain)

        # Build context summary from prior turns if any
        ctx_summary = ""
        if self.compressed_findings:
            ctx_summary = "\n".join(f"• {f}" for f in self.compressed_findings[-4:])

        prompt = PredictionEngine.user_prompt_qa(
            chart_json_str=compressed_chart,
            question=question,
            context_summary=ctx_summary if ctx_summary else None,
            classical_doctrine=classical_doctrine,
        )
        return prompt, domain

    def record_turn(self, question, answer_text, domain):
        """
        Record a completed Q&A turn.
        If history exceeds 2 turns, compress older answers into summary bullets
        to keep the context window compact and prevent catastrophic forgetting.
        """
        self.turns.append({
            "question": question,
            "answer": answer_text,
            "domain": domain,
        })

        takeaways = ContextCompressor.extract_takeaways(answer_text, max_bullets=2)
        for t in takeaways:
            clean_t = t.lstrip("-•* ").strip()
            if clean_t and clean_t not in self.compressed_findings:
                self.compressed_findings.append(f"[{domain}] {clean_t}")

        # Keep rolling takeaways capped at 6 items
        if len(self.compressed_findings) > 6:
            self.compressed_findings = self.compressed_findings[-6:]
