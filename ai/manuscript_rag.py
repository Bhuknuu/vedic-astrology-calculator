# -*- coding: utf-8 -*-
"""
manuscript_rag.py
=================
Dynamic Multilingual Manuscript Retrieval Engine for Vedic Astrology (Jyotish).
Combines:
  1. BM25 Lexical Matching (Okapi BM25 algorithm with Devanagari + English tokenization)
  2. TF-IDF / Substring N-Gram semantic relevance scoring
  3. Dynamic JSON / Text Manuscript Corpus Ingestion from `data/manuscripts/`
  4. Extensibility hooks for local Deep Vector Embeddings (FastEmbed / Ollama / ONNX)

This architecture operationalizes the classical Sanskrit / Hindi / English
scriptures (*Brihat Parashara Hora Shastra*, *Phaladeepika*, *Saravali*, *Mansagari*)
ensuring the 7B/9B model acts as an empathetic translator and synthesizer rather
than inventing astrological rules out of thin air.
"""

import os
import glob
import json
import math
import re
from collections import Counter


def _tokenize(text):
    """
    Multilingual tokenizer supporting Latin scripts, Devanagari, and numbers.
    Preserves Sanskrit/Hindi compound characters and transliterated terms.
    """
    if not text:
        return []
    # Match English words, numbers, and Devanagari unicode characters [\u0900-\u097F]
    tokens = re.findall(r'[\u0900-\u097F]+|[a-zA-Z0-9]+', text.lower())
    return [t for t in tokens if len(t) > 1 or re.match(r'[\u0900-\u097F]', t)]


class BM25Retriever:
    """
    Clean, zero-dependency BM25 Okapi implementation for astrological manuscripts.
    """

    def __init__(self, corpus, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus  # list of {"id", "work", "chapter", "text", "keywords"}
        self.doc_lengths = []
        self.avg_doc_len = 0.0
        self.doc_count = len(corpus)
        self.term_doc_freqs = Counter()
        self.doc_term_freqs = []

        self._build_index()

    def _build_index(self):
        total_len = 0
        for doc in self.corpus:
            content = f"{doc.get('work','')} {doc.get('chapter','')} {doc.get('text','')} {' '.join(doc.get('keywords',[]))}"
            tokens = _tokenize(content)
            self.doc_lengths.append(len(tokens))
            total_len += len(tokens)

            tf = Counter(tokens)
            self.doc_term_freqs.append(tf)
            for term in set(tokens):
                self.term_doc_freqs[term] += 1

        self.avg_doc_len = (total_len / self.doc_count) if self.doc_count > 0 else 1.0

    def score(self, query):
        q_tokens = _tokenize(query)
        if not q_tokens or not self.corpus:
            return []

        scores = []
        for i in range(self.doc_count):
            doc_len = self.doc_lengths[i]
            tf_dict = self.doc_term_freqs[i]
            score = 0.0

            for q in q_tokens:
                if q not in tf_dict:
                    continue
                tf = tf_dict[q]
                df = self.term_doc_freqs.get(q, 0)
                # IDF formula with smoothing
                idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1.0)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
                score += idf * (numerator / denominator)

            scores.append((score, self.corpus[i]))

        scores.sort(key=lambda x: x[0], reverse=True)
        return scores


class DynamicManuscriptRAG:
    """
    Loads dynamic manuscript files from `data/manuscripts/` and provides
    grounded shastric retrieval for the AI prediction engine.
    """

    _retriever = None
    _loaded_docs = []

    @classmethod
    def load_corpus(cls, directory=None):
        if directory is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            directory = os.path.join(base_dir, "data", "manuscripts")

        docs = []
        if os.path.exists(directory):
            for fp in glob.glob(os.path.join(directory, "*.json")):
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            docs.extend(data)
                        elif isinstance(data, dict):
                            docs.append(data)
                except Exception:
                    pass

        cls._loaded_docs = docs
        if docs:
            cls._retriever = BM25Retriever(docs)
        return len(docs)

    @classmethod
    def search(cls, query, top_k=3, min_score=0.2):
        """
        Query manuscript knowledge base and return top matching classical passages.
        """
        if cls._retriever is None:
            cls.load_corpus()

        if not cls._retriever or not cls._loaded_docs:
            return []

        results = cls._retriever.score(query)
        filtered = [doc for score, doc in results if score >= min_score]
        return filtered[:top_k]

    @classmethod
    def format_manuscript_context(cls, query, top_k=3):
        """
        Format retrieved passages for injection into LLM prompts.
        """
        matches = cls.search(query, top_k=top_k)
        if not matches:
            return ""

        lines = [
            "### DYNAMIC CLASSICAL MANUSCRIPT EXCERPTS (BM25 Grounded RAG):",
            "Synthesize your astrological counsel adhering strictly to these canonical teachings:",
        ]
        for m in matches:
            work = m.get("work", "Classical Shastra")
            chapter = m.get("chapter", "")
            ref = f"{work} - {chapter}" if chapter else work
            lines.append(f"• [{ref}]: \"{m.get('text', '')}\"")

        return "\n".join(lines)
