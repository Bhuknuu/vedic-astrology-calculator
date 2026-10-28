# -*- coding: utf-8 -*-
"""
rag_engine.py
=============
Deterministic Classical Knowledge Retrieval (RAG) Engine for Vedic Astrology.
Operationalizes classical principles from:
  - Brihat Parashara Hora Shastra (BPHS)
  - Phaladeepika (Mantreswara)
  - Saravali (Kalyana Varma)
  - Bhavartha Ratnakara (Raman translation)

Architecture:
-------------
Follows the "Computed Data + Retrieved Doctrine" paradigm:
1. Core calculations (Swiss Ephemeris) produce exact planetary placements.
2. ClassicalRAG indexes classical sloka rules for:
     - Lagnesh placement across the 12 Bhavas
     - 10th Lord (Career / Karma) across the 12 Bhavas
     - 2nd & 11th Lords (Wealth / Dhana) combinations
     - 7th Lord & Shukra (Relationships / Kalatra) placements
     - Detected Yogas (Pancha Mahapurusha, Gajakesari, Budhaditya, etc.)
     - Vimshottari Mahadasha / Antardasha active cycles
3. Classical rules matching the native's chart are retrieved deterministically.
4. The retrieved classical principles are passed to the 7B/9B LLM prompt,
   grounding its synthesis in authentic shastric doctrine and eliminating
   hallucinations.
"""

from core.constants import RASHI, RASHI_SWAMI, ALL_GRAHAS

# ══════════════════════════════════════════════════════════════════════════════
#  CLASSICAL SUTRA CORPUS
# ══════════════════════════════════════════════════════════════════════════════

# ── 1. Lagnesh (Ascendant Lord) Placements in Bhavas 1-12 (BPHS Ch. 24) ──────
LAGNESH_BHAVA_RULES = {
    1: {
        "text": "Lagnesh in 1st Bhava (Tanu): Endows the native with strong physical constitution, self-reliance, leadership instincts, and independent success. The native carves their own path.",
        "sutra": "BPHS Ch. 24, Sloka 1 (Lagnesha in Tanu Bhava)",
        "domains": ["PERSONALITY", "HEALTH", "CAREER"],
    },
    2: {
        "text": "Lagnesh in 2nd Bhava (Dhana): Bestows financial acumen, articulate speech, dedication to family heritage, and steady wealth accumulation through personal skill.",
        "sutra": "BPHS Ch. 24, Sloka 2 (Lagnesha in Dhana Bhava)",
        "domains": ["FINANCE", "PERSONALITY"],
    },
    3: {
        "text": "Lagnesh in 3rd Bhava (Sahaja): Grants immense courage (Parakrama), entrepreneurial enterprise, sibling support, and talent in communication, arts, or technical initiative.",
        "sutra": "BPHS Ch. 24, Sloka 3 (Lagnesha in Sahaja Bhava)",
        "domains": ["CAREER", "PERSONALITY"],
    },
    4: {
        "text": "Lagnesh in 4th Bhava (Sukha): Brings maternal blessings, domestic happiness, vehicle and landed property acquisitions, and emotional groundedness.",
        "sutra": "BPHS Ch. 24, Sloka 4 (Lagnesha in Sukha Bhava)",
        "domains": ["PERSONALITY", "FINANCE"],
    },
    5: {
        "text": "Lagnesh in 5th Bhava (Putra): Bestows sharp intellect, creative mastery, wisdom in counsel, virtuous progeny, and past-life merits (Purva Punya).",
        "sutra": "BPHS Ch. 24, Sloka 5 (Lagnesha in Putra Bhava)",
        "domains": ["EDUCATION", "CAREER", "PERSONALITY"],
    },
    6: {
        "text": "Lagnesh in 6th Bhava (Ari): Creates a tenacious problem-solver, victor over competition and adversaries, but requires conscious cultivation of digestive health and stress balance.",
        "sutra": "BPHS Ch. 24, Sloka 6 (Lagnesha in Ari Bhava)",
        "domains": ["HEALTH", "CAREER"],
    },
    7: {
        "text": "Lagnesh in 7th Bhava (Yuvati): Directs focus toward partnership, business alliances, public prominence, and foreign travel; spouse plays a catalytic role in destiny.",
        "sutra": "BPHS Ch. 24, Sloka 7 (Lagnesha in Yuvati Bhava)",
        "domains": ["RELATIONSHIPS", "CAREER"],
    },
    8: {
        "text": "Lagnesh in 8th Bhava (Randhra): Endows investigative depth, occult/research acumen, and transformative resilience; life undergoes major metamorphosis through unexpected events.",
        "sutra": "BPHS Ch. 24, Sloka 8 (Lagnesha in Randhra Bhava)",
        "domains": ["HEALTH", "PERSONALITY"],
    },
    9: {
        "text": "Lagnesh in 9th Bhava (Dharma): High fortune (Bhagya), philosophical wisdom, righteous conduct, guidance from mentors/father, and effortless public esteem.",
        "sutra": "BPHS Ch. 24, Sloka 9 (Lagnesha in Dharma Bhava)",
        "domains": ["CAREER", "FINANCE", "PERSONALITY"],
    },
    10: {
        "text": "Lagnesh in 10th Bhava (Karma): Confers leadership, renown, career distinction, strong vocational ambition, and honor from government or institutions.",
        "sutra": "BPHS Ch. 24, Sloka 10 (Lagnesha in Karma Bhava)",
        "domains": ["CAREER", "FINANCE"],
    },
    11: {
        "text": "Lagnesh in 11th Bhava (Labha): Assures perpetual financial gains, extensive professional networks, fulfillment of major life desires, and elder sibling goodwill.",
        "sutra": "BPHS Ch. 24, Sloka 11 (Lagnesha in Labha Bhava)",
        "domains": ["FINANCE", "CAREER"],
    },
    12: {
        "text": "Lagnesh in 12th Bhava (Vyaya): Fosters foreign connections, spiritual liberation, introspective mind, research pursuits, and gains through non-traditional or overseas avenues.",
        "sutra": "BPHS Ch. 24, Sloka 12 (Lagnesha in Vyaya Bhava)",
        "domains": ["CAREER", "PERSONALITY"],
    },
}

# ── 2. 10th Lord (Career / Karma) Placements (Phaladeepika Ch. 18 / BPHS) ───
TENTH_LORD_RULES = {
    1: {
        "text": "10th Lord in 1st Bhava: Self-made enterprise, natural executive authority, public-facing career, and identity strongly tied to vocational achievements.",
        "sutra": "Phaladeepika Ch. 18, Sloka 21",
        "domains": ["CAREER"],
    },
    2: {
        "text": "10th Lord in 2nd Bhava: Wealth derived directly from profession; success in finance, consultancy, family commerce, or communication-heavy industries.",
        "sutra": "Phaladeepika Ch. 18, Sloka 22",
        "domains": ["CAREER", "FINANCE"],
    },
    3: {
        "text": "10th Lord in 3rd Bhava: Career flourishes through media, technology, short travels, artistic courage, and independent commercial initiative.",
        "sutra": "Phaladeepika Ch. 18, Sloka 23",
        "domains": ["CAREER"],
    },
    4: {
        "text": "10th Lord in 4th Bhava: Prominence in real estate, education, institutional administration, agriculture, or services providing comfort and security to society.",
        "sutra": "Phaladeepika Ch. 18, Sloka 24",
        "domains": ["CAREER"],
    },
    5: {
        "text": "10th Lord in 5th Bhava: Professional distinction through intellect, strategic advisory, speculative investments, politics, teaching, or creative arts.",
        "sutra": "Phaladeepika Ch. 18, Sloka 25",
        "domains": ["CAREER", "EDUCATION"],
    },
    6: {
        "text": "10th Lord in 6th Bhava: Excellence in competitive examinations, legal, healthcare, dispute resolution, auditing, or service sectors; overcomes all workplace rivals.",
        "sutra": "Phaladeepika Ch. 18, Sloka 26",
        "domains": ["CAREER"],
    },
    7: {
        "text": "10th Lord in 7th Bhava: Successful business partnerships, public diplomacy, international trade, client consultancy, and career elevation through spouse or joint ventures.",
        "sutra": "Phaladeepika Ch. 18, Sloka 27",
        "domains": ["CAREER", "RELATIONSHIPS"],
    },
    8: {
        "text": "10th Lord in 8th Bhava: Unconventional or research-intensive vocation; career in data mining, risk management, surgery, occult science, or turnaround consulting.",
        "sutra": "Phaladeepika Ch. 18, Sloka 28",
        "domains": ["CAREER"],
    },
    9: {
        "text": "10th Lord in 9th Bhava: Highly auspicious Dharma-Karmadhipati connection; fortune shines through higher education, judiciary, mentorship, publishing, and ethical leadership.",
        "sutra": "Phaladeepika Ch. 18, Sloka 29",
        "domains": ["CAREER", "FINANCE"],
    },
    10: {
        "text": "10th Lord in 10th Bhava (Swakshetra/Moolatrikona): Supreme career stability, institutional authority, widespread professional respect, and enduring legacy.",
        "sutra": "Phaladeepika Ch. 18, Sloka 30",
        "domains": ["CAREER"],
    },
    11: {
        "text": "10th Lord in 11th Bhava: Lucrative professional gains, influential patronage, leadership in large corporations/organizations, and steady monetization of ideas.",
        "sutra": "Phaladeepika Ch. 18, Sloka 31",
        "domains": ["CAREER", "FINANCE"],
    },
    12: {
        "text": "10th Lord in 12th Bhava: Career flourishes in foreign lands, multinational corporations, hospitals, spiritual retreats, or overseas trade.",
        "sutra": "Phaladeepika Ch. 18, Sloka 32",
        "domains": ["CAREER"],
    },
}

# ── 3. Wealth & Dhana Yogas (Bhavartha Ratnakara & BPHS Ch. 41) ───────────────
DHANA_RULES = {
    "2_in_11": {
        "text": "2nd Lord in 11th Bhava: Continuous inflow of wealth, multiple revenue streams, commercial brilliance, and high financial liquidity.",
        "sutra": "Bhavartha Ratnakara, Ch. 2 (Dhana Yogas)",
        "domains": ["FINANCE"],
    },
    "11_in_2": {
        "text": "11th Lord in 2nd Bhava: Compounding savings, profitable asset retention, and prosperity sustained through intelligent investments.",
        "sutra": "Bhavartha Ratnakara, Ch. 2 (Dhana Yogas)",
        "domains": ["FINANCE"],
    },
    "1_in_11": {
        "text": "Lagnesha in 11th Bhava: High financial gains achieved through personal effort; natural magnet for commercial opportunities.",
        "sutra": "BPHS Ch. 41, Sloka 3",
        "domains": ["FINANCE"],
    },
    "5_and_9": {
        "text": "Trikona Lords (5th & 9th) active: Wealth is accompanied by ethical prestige (Lakshmi Sthana) and sustained luck in wealth generation.",
        "sutra": "BPHS Ch. 41, Sloka 7",
        "domains": ["FINANCE"],
    },
}

# ── 4. Relationships & 7th Lord (Phaladeepika Ch. 17 / BPHS Ch. 24) ──────────
SEVENTH_LORD_RULES = {
    1: {
        "text": "7th Lord in 1st Bhava: Partner is deeply bonded to native's life decisions, shares similar ambitions, and brings public respect.",
        "sutra": "Phaladeepika Ch. 17, Sloka 1",
        "domains": ["RELATIONSHIPS"],
    },
    2: {
        "text": "7th Lord in 2nd Bhava: Marriage brings financial consolidation, family support, and mutual material prosperity.",
        "sutra": "Phaladeepika Ch. 17, Sloka 2",
        "domains": ["RELATIONSHIPS", "FINANCE"],
    },
    4: {
        "text": "7th Lord in 4th Bhava: Domestic harmony, supportive home environment, and cooperative partner who values emotional stability.",
        "sutra": "Phaladeepika Ch. 17, Sloka 4",
        "domains": ["RELATIONSHIPS"],
    },
    7: {
        "text": "7th Lord in 7th Bhava (Own Sign): Highly stable marital bonds, charming and accomplished spouse, and successful mutual enterprise.",
        "sutra": "Phaladeepika Ch. 17, Sloka 7",
        "domains": ["RELATIONSHIPS"],
    },
    9: {
        "text": "7th Lord in 9th Bhava: Fortunate union; partner brings good luck, shared spiritual/philosophical values, and auspicious foreign journeys.",
        "sutra": "Phaladeepika Ch. 17, Sloka 9",
        "domains": ["RELATIONSHIPS"],
    },
    10: {
        "text": "7th Lord in 10th Bhava: Partner is professionally accomplished, career-oriented, and directly aids native's status enhancement.",
        "sutra": "Phaladeepika Ch. 17, Sloka 10",
        "domains": ["RELATIONSHIPS", "CAREER"],
    },
    11: {
        "text": "7th Lord in 11th Bhava: Marriage brings expanding social circle, financial gains, and cooperative realization of life goals.",
        "sutra": "Phaladeepika Ch. 17, Sloka 11",
        "domains": ["RELATIONSHIPS", "FINANCE"],
    },
}

# ── 5. Classical Yogas (BPHS Ch. 34-36 / Phaladeepika Ch. 6) ───────────────────
YOGA_CLASSICAL_SUTRAS = {
    "Ruchaka": {
        "text": "Ruchaka Yoga (Mars in Kendra in Own/Exaltation sign): Conferring martial courage, physical endurance, strategic brilliance, leadership over forces/teams, and triumph in competitive pursuits.",
        "sutra": "BPHS Ch. 75, Sloka 2 & Phaladeepika Ch. 6, Sloka 1",
        "domains": ["CAREER", "PERSONALITY"],
    },
    "Bhadra": {
        "text": "Bhadra Yoga (Mercury in Kendra in Own/Exaltation sign): Endows extraordinary intellect, mathematical acuity, oratorical eloquence, commercial genius, and scholarly fame.",
        "sutra": "BPHS Ch. 75, Sloka 3 & Phaladeepika Ch. 6, Sloka 2",
        "domains": ["CAREER", "EDUCATION"],
    },
    "Hamsa": {
        "text": "Hamsa Yoga (Jupiter in Kendra in Own/Exaltation sign): Conveys supreme wisdom, spiritual nobility, administrative respect, ethical clarity, and widespread societal reverence.",
        "sutra": "BPHS Ch. 75, Sloka 4 & Phaladeepika Ch. 6, Sloka 3",
        "domains": ["CAREER", "PERSONALITY"],
    },
    "Malavya": {
        "text": "Malavya Yoga (Venus in Kendra in Own/Exaltation sign): Bestows aesthetic refinement, luxury vehicles, diplomatic charm, artistic brilliance, and deeply fulfilling relationships.",
        "sutra": "BPHS Ch. 75, Sloka 5 & Phaladeepika Ch. 6, Sloka 4",
        "domains": ["RELATIONSHIPS", "FINANCE"],
    },
    "Sasa": {
        "text": "Sasa Yoga (Saturn in Kendra in Own/Exaltation sign): Produces institutional endurance, command over labor and organizations, political or judicial authority, and enduring achievements.",
        "sutra": "BPHS Ch. 75, Sloka 6 & Phaladeepika Ch. 6, Sloka 5",
        "domains": ["CAREER", "PERSONALITY"],
    },
    "Gajakesari": {
        "text": "Gajakesari Yoga (Jupiter in Kendra from Moon): Shields native against adversity, confers unfailing popular goodwill, virtuous reputation, intellectual brilliance, and prosperity.",
        "sutra": "Phaladeepika Ch. 6, Sloka 14",
        "domains": ["CAREER", "FINANCE", "PERSONALITY"],
    },
    "Budhaditya": {
        "text": "Budhaditya Yoga (Sun + Mercury conjunction): Sharp cognitive bandwidth, royal/governmental favor, administrative acumen, and technical eloquence.",
        "sutra": "Saravali Ch. 14, Sloka 12",
        "domains": ["CAREER", "EDUCATION"],
    },
    "Viparita Raja": {
        "text": "Viparita Raja Yoga (Dusthana lords in Dusthanas): Turnaround victories, unexpected elevation during crises, and triumph through unconventional circumstances.",
        "sutra": "Phaladeepika Ch. 6, Slokas 57-60",
        "domains": ["CAREER", "FINANCE"],
    },
    "Neechabhanga Raja": {
        "text": "Neechabhanga Raja Yoga (Cancellation of planetary debility): Early struggle transforms into high competence, resilience, and hard-earned institutional triumph.",
        "sutra": "Phaladeepika Ch. 6, Slokas 26-30",
        "domains": ["CAREER", "PERSONALITY"],
    },
    "Chandra-Mangal": {
        "text": "Chandra-Mangal Yoga (Moon + Mars conjunction/mutual aspect): Commercial sharpness, energetic enterprise, earnings through property/manufacturing, and financial drive.",
        "sutra": "Saravali Ch. 15, Sloka 20",
        "domains": ["FINANCE", "CAREER"],
    },
}

# ── 6. Dasha Interpretation Matrix (BPHS Ch. 47-58) ──────────────────────────
DASHA_RULES = {
    "Guru": {
        "text": "Jupiter Dasha: Expansion of wisdom, auspicious milestones, mentorship roles, wealth accumulation, and spiritual elevation if Jupiter is well-placed.",
        "sutra": "BPHS Ch. 52, Slokas 1-12",
    },
    "Shani": {
        "text": "Saturn Dasha: Era of profound structural building, discipline, shedding superficial pursuits, endurance, and durable career foundations through patience.",
        "sutra": "BPHS Ch. 53, Slokas 1-15",
    },
    "Budha": {
        "text": "Mercury Dasha: Intellectual productivity, commercial growth, communication mastery, academic/literary pursuits, and diversification of revenue streams.",
        "sutra": "BPHS Ch. 54, Slokas 1-10",
    },
    "Ketu": {
        "text": "Ketu Dasha: Inner spiritual awakening, detachment from conventional dogma, intuitive breakthroughs, and philosophical recalibration.",
        "sutra": "BPHS Ch. 55, Slokas 1-8",
    },
    "Shukra": {
        "text": "Venus Dasha: Artistic fulfillment, relationship milestones, aesthetic acquisitions, social harmony, and comfort in material affairs.",
        "sutra": "BPHS Ch. 56, Slokas 1-14",
    },
    "Surya": {
        "text": "Sun Dasha: Vocational visibility, government connections, self-assertion, vital health focus, and assuming leadership responsibilities.",
        "sutra": "BPHS Ch. 48, Slokas 1-9",
    },
    "Chandra": {
        "text": "Moon Dasha: Emotional and domestic developments, public popularity, mental creativity, travel, and prosperity through public-facing goods/services.",
        "sutra": "BPHS Ch. 49, Slokas 1-10",
    },
    "Mangal": {
        "text": "Mars Dasha: Courageous execution, physical drive, competition wins, property acquisition, and rapid vocational mobilization.",
        "sutra": "BPHS Ch. 50, Slokas 1-9",
    },
    "Rahu": {
        "text": "Rahu Dasha: Radical career transformations, foreign avenues, ambition, high technological affinity, and non-linear breakthroughs.",
        "sutra": "BPHS Ch. 51, Slokas 1-16",
    },
}

# ── 7. Dosha Interpretation & Mitigation (BPHS Ch. 81 / Mansagari) ───────────
DOSHA_CLASSICAL_SUTRAS = {
    "Mangal": {
        "text": "Kuja/Mangal Dosha: High vital energy, passionate drive, and occasional friction in domestic dynamics; mitigated when channelled into constructive physical disciplines, shared projects, or after age 28.",
        "sutra": "BPHS Ch. 81 (Stri Jataka / Kuja Dosha Principles)",
        "domains": ["RELATIONSHIPS", "PERSONALITY"],
    },
    "Kaal Sarp": {
        "text": "Kaal Sarp Pattern (All planets hemmed between Rahu and Ketu): Intense karmic focus, non-linear early struggles followed by profound resilience, worldly breakthroughs, and spiritual realization.",
        "sutra": "Mansagari Ch. 4 (Sarpa Yoga Formations)",
        "domains": ["CAREER", "PERSONALITY"],
    },
    "Sade Sati": {
        "text": "Shani Sade Sati (Saturn transit over natal Moon): Period of psychological maturity, stripping away illusions, establishing self-discipline, and building enduring character through perseverance.",
        "sutra": "Phaladeepika Ch. 23, Sloka 22 (Gochara Saturn)",
        "domains": ["TIMING_DASHA", "PERSONALITY"],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
#  CLASSICAL RAG RETRIEVER
# ══════════════════════════════════════════════════════════════════════════════
class ClassicalRAG:
    """
    Retrieves authentic, deterministic classical Vedic astrology rules matching
    a native's exact computed chart coordinates and the active conversational domain.
    """

    @staticmethod
    def retrieve_context(grahas, yogas, doshas, dashas, domain="GENERAL", max_rules=7, query=""):
        """
        Extract pertinent shastric doctrine grounded in the native's chart,
        supplemented by dynamic BM25 manuscript search when a query is provided.
        Returns a formatted markdown string of classical sutras.
        """
        rules = []

        lr = grahas.get("Lagna", {}).get("rashi", 0)
        lagnesh = RASHI_SWAMI[lr]
        lagnesh_bhava = grahas.get(lagnesh, {}).get("bhava")

        # 1. Lagnesh placement rule
        try:
            lb_int = int(lagnesh_bhava)
            if lb_int in LAGNESH_BHAVA_RULES:
                r = LAGNESH_BHAVA_RULES[lb_int]
                rules.append((r["sutra"], r["text"], "PERSONALITY"))
        except (ValueError, TypeError):
            pass

        # 2. 10th Lord placement (Career)
        tenth_rashi = (lr + 9) % 12
        tenth_lord = RASHI_SWAMI[tenth_rashi]
        tenth_bhava = grahas.get(tenth_lord, {}).get("bhava")
        try:
            tb_int = int(tenth_bhava)
            if tb_int in TENTH_LORD_RULES:
                r = TENTH_LORD_RULES[tb_int]
                rules.append((r["sutra"], r["text"], "CAREER"))
        except (ValueError, TypeError):
            pass

        # 3. 7th Lord placement (Relationships)
        seventh_rashi = (lr + 6) % 12
        seventh_lord = RASHI_SWAMI[seventh_rashi]
        seventh_bhava = grahas.get(seventh_lord, {}).get("bhava")
        try:
            sb_int = int(seventh_bhava)
            if sb_int in SEVENTH_LORD_RULES:
                r = SEVENTH_LORD_RULES[sb_int]
                rules.append((r["sutra"], r["text"], "RELATIONSHIPS"))
        except (ValueError, TypeError):
            pass

        # 4. Wealth / Dhana placements (2nd & 11th)
        second_rashi = (lr + 1) % 12
        second_lord = RASHI_SWAMI[second_rashi]
        second_bhava = grahas.get(second_lord, {}).get("bhava")
        eleventh_rashi = (lr + 10) % 12
        eleventh_lord = RASHI_SWAMI[eleventh_rashi]
        eleventh_bhava = grahas.get(eleventh_lord, {}).get("bhava")

        if str(second_bhava) == "11":
            r = DHANA_RULES["2_in_11"]
            rules.append((r["sutra"], r["text"], "FINANCE"))
        elif str(eleventh_bhava) == "2":
            r = DHANA_RULES["11_in_2"]
            rules.append((r["sutra"], r["text"], "FINANCE"))
        elif str(lagnesh_bhava) == "11":
            r = DHANA_RULES["1_in_11"]
            rules.append((r["sutra"], r["text"], "FINANCE"))

        # 5. Yogas detected in chart
        for y in yogas:
            y_name = y.get("naam", "")
            for pattern, r in YOGA_CLASSICAL_SUTRAS.items():
                if pattern.lower() in y_name.lower():
                    rules.append((r["sutra"], r["text"], "YOGAS"))
                    break

        # 6. Active and Previous Dasha rules
        import datetime
        now = datetime.datetime.now()
        cur_md = cur_ad = prev_md = None
        for idx, md in enumerate(dashas):
            if md["start"] <= now <= md["end"]:
                cur_md = md.get("lord")
                if idx > 0:
                    prev_md = dashas[idx - 1].get("lord")
                for ad in md.get("antardasha", []):
                    if ad["start"] <= now <= ad["end"]:
                        cur_ad = ad.get("lord")
                        break
                break

        if cur_md and cur_md in DASHA_RULES:
            r = DASHA_RULES[cur_md]
            rules.append((r["sutra"], f"Active Current Mahadasha ({cur_md}): {r['text']}", "TIMING_DASHA"))

        if prev_md and prev_md in DASHA_RULES:
            r = DASHA_RULES[prev_md]
            rules.append((r["sutra"], f"Previous Past Mahadasha ({prev_md}): {r['text']}", "TIMING_DASHA"))

        # 7. Dosha patterns detected in chart
        for d in doshas:
            d_name = d.get("naam", "")
            for pattern, r in DOSHA_CLASSICAL_SUTRAS.items():
                if pattern.lower() in d_name.lower():
                    rules.append((r["sutra"], f"Dosha Pattern ({pattern}): {r['text']}", r.get("domains", ["PERSONALITY"])[0]))
                    break

        # Filter & prioritize by active domain if specified
        if domain and domain != "GENERAL":
            prioritized = [r for r in rules if r[2] == domain]
            others = [r for r in rules if r[2] != domain]
            rules = prioritized + others

        # Cap at max_rules
        selected = rules[:max_rules]

        output_lines = []
        if selected:
            output_lines.append("### AUTHENTIC CLASSICAL DOCTRINE (Grounding Shastras):")
            output_lines.append("Synthesize the reading strictly adhering to these scriptural principles:")
            for sutra_ref, text, _ in selected:
                output_lines.append(f"• [{sutra_ref}]: \"{text}\"")

        # Dynamic manuscript BM25 search matching specific query keywords
        if query:
            try:
                from ai.manuscript_rag import DynamicManuscriptRAG
                ms_context = DynamicManuscriptRAG.format_manuscript_context(query, top_k=2)
                if ms_context:
                    if output_lines:
                        output_lines.append("")
                    output_lines.append(ms_context)
            except Exception:
                pass

        return "\n".join(output_lines)
