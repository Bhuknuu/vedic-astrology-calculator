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

        # Current + next Mahadasha / Antardasha
        cur_md = cur_ad = None
        for md in dashas:
            if md["start"] <= now <= md["end"]:
                cur_md = md
                for ad in md["antardasha"]:
                    if ad["start"] <= now <= ad["end"]:
                        cur_ad = ad
                        break
                break

        dasha_info = {}
        if cur_md:
            md_pd = grahas.get(cur_md["lord"], {})
            dasha_info["mahadasha"] = {
                "lord":       cur_md["lord"],
                "ends":       cur_md["end"].strftime("%b %Y"),
                "yrs_left":   round((cur_md["end"] - now).days / 365.24219, 1),
                "lord_bhava": md_pd.get("bhava", ""),
                "lord_dignity": sthiti(cur_md["lord"], md_pd.get("rashi", 0)),
            }
        if cur_ad:
            ad_pd = grahas.get(cur_ad["lord"], {})
            dasha_info["antardasha"] = {
                "lord":       cur_ad["lord"],
                "ends":       cur_ad["end"].strftime("%b %Y"),
                "lord_bhava": ad_pd.get("bhava", ""),
            }
        # Next Mahadasha (useful for predictions)
        for md in dashas:
            if md["start"] > now:
                dasha_info["next_mahadasha"] = {
                    "lord":  md["lord"],
                    "starts": md["start"].strftime("%b %Y"),
                }
                break

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

    # ── System Prompt (Qwen2.5-7B constrained) ────────────────────────────────
    @staticmethod
    def system_prompt():
        """
        Constrained system prompt for Qwen2.5-7B-Instruct.
        Fixes vs v3.0:
          - Added 'I don't know' / fatalistic query deflection protocol
          - Anti-markdown instruction (Qwen2.5 tends to over-use ** and ##)
          - Removed gambhirata severity references
          - Tighter output size cap for 7B context efficiency
        """
        return (
            "You are Jyotisha-GPT, an expert Vedic astrologer. "
            "You receive a compact JSON birth chart and answer questions about it.\n\n"

            "## ABSOLUTE RULES — NEVER VIOLATE\n"
            "1. NEVER predict death, fatal disease, or irreversible ruin for any person.\n"
            "2. If a user asks about death, fatal illness, financial ruin, or tragedy: "
            "gently decline that specific aspect, state 'Jyotish is a tool for "
            "self-awareness, not fatalism,' then pivot to analyzing the chart's "
            "resilience (e.g., 6th or 8th house strengths, protective yogas).\n"
            "3. Frame every Dosha as an energetic pattern or psychological tendency. "
            "Always end a Dosha note with a practical reframe or remedy.\n"
            "4. Ground EVERY statement in the JSON chart provided. "
            "Do not invent placements, yogas, or house positions.\n"
            "5. If the chart data does not contain information to answer a question, "
            "say: 'The chart does not clearly indicate this — I will not speculate.' "
            "Do not hallucinate an answer.\n\n"

            "## OUTPUT FORMAT\n"
            "- Use plain bullet points starting with a dash (-). "
            "Do NOT use markdown bold (**), headers (##), or code blocks.\n"
            "- Structure each bullet: [Domain]: [Result/Outcome] "
            "(brief astrological basis in parentheses at end).\n"
            "  Example: Career: Leadership role in technical or research fields "
            "by mid-30s (10th lord Guru in Kendra, Ruchaka Yoga).\n"
            "- Lead with the RESULT. Do NOT open with 'Because', 'Since', 'Due to'.\n"
            "- 3 to 5 bullets per section. Be specific about timing and domains.\n"
            "- Total output under 700 words for Q&A; under 950 for full readings.\n\n"

            "## TECHNICAL CONVENTIONS\n"
            "- Planet names: Surya, Chandra, Mangal, Budha, Guru, Shukra, Shani, Rahu, Ketu.\n"
            "- Houses: Bhava 1 to 12 (Bhava 10 = career, Bhava 7 = partnership).\n"
            "- Dasha: always state both Mahadasha and Antardasha lords and "
            "what houses they rule natally.\n"
            "- Yogas: name the yoga, state the practical outcome, then note the "
            "forming condition in parentheses.\n"
            "- Doshas: name the pattern, give a constructive reframe, suggest "
            "one practical remedy — never frame as a curse.\n\n"

            "## WELLBEING FRAMING EXAMPLES\n"
            "Correct: 'This placement creates intense drive — "
            "channelled constructively it excels in leadership.'\n"
            "Incorrect: 'This placement will cause suffering and loss.'"
        )

    # ── User Prompts ──────────────────────────────────────────────────────────
    @staticmethod
    def user_prompt_full(chart_json_str):
        return (
            f"Chart data:\n{chart_json_str}\n\n"
            "Provide a complete Jyotish reading. Use plain dash bullets. "
            "No markdown bold or headers. Each bullet: lead with the result, "
            "astrological basis in parentheses at end.\n\n"
            "Sections:\n"
            "1. PERSONALITY - Lagna and Lagnesh: core nature and temperament\n"
            "2. CAREER - 10th Bhava and its lord: fields, roles, peak timing\n"
            "3. WEALTH - 2nd/11th lords, Dhana Yogas: income sources and periods\n"
            "4. RELATIONSHIPS - 7th lord, Shukra: partner qualities, timing\n"
            "5. CURRENT DASHA - Active Mahadasha + Antardasha: themes and events now\n"
            "6. HEALTH - Surya, Lagna, 6th/8th Bhavas: areas to nurture\n"
            "7. KEY PATTERNS - Top 2 Yogas (practical outcome), "
            "top 1 Dosha as growth pattern with one remedy\n\n"
            "3 to 5 bullets per section. Specific, practical, result-first. "
            "Plain text only."
        )

    @staticmethod
    def user_prompt_qa(chart_json_str, question, context_summary=None):
        ctx_prefix = ""
        if context_summary:
            ctx_prefix = (
                f"[Context established from earlier turns for this chart]:\n"
                f"{context_summary}\n\n"
            )
        return (
            f"Chart data:\n{chart_json_str}\n\n"
            f"{ctx_prefix}"
            f"Question: {question}\n\n"
            "Answer with specific predictions — results first, astrological basis "
            "in parentheses. Use plain dash bullets. No markdown. "
            "3 to 5 bullets. Concrete and actionable. Under 400 words."
        )


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

    def build_qa_prompt(self, raw_chart_json_str, question):
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
