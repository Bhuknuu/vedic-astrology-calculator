# -*- coding: utf-8 -*-
"""
ollama_engine.py
================
Fully-offline LLM integration via local Ollama instance.
Targets Qwen2.5-7B-Instruct-Q6_K on RTX 4060 (8GB VRAM).

Key fixes vs v3.0
-----------------
* Clean stop     : sends DELETE /api/generate to Ollama so the model
                   stops computing on the server side, freeing GPU cycles
* State management: uses _has_cleared_placeholder bool, not `del` attr trick
* Dynamic context : num_ctx computed from payload length, not hardcoded 4096
* Configurable URL: all endpoint config in constants.py — LM Studio = 1 edit
* Markdown strip  : removes **, ##, ``` before displaying tokens in Tkinter
"""

import json
import threading
import urllib.request
import urllib.error
from core.constants import (
    OLLAMA_BASE_URL, OLLAMA_GPU_LAYERS, OLLAMA_TEMPERATURE,
    OLLAMA_REPEAT_PENALTY, OLLAMA_TOP_P, OLLAMA_MAX_PREDICT,
    OLLAMA_CTX_MIN, OLLAMA_CTX_MAX,
)

# Rough tokens-per-character estimate for English + JSON
_CHARS_PER_TOKEN = 3.8


def _estimate_tokens(text):
    """Rough token count from character length."""
    return max(1, int(len(text) / _CHARS_PER_TOKEN))


def _dynamic_ctx(system_prompt, user_prompt):
    """
    FIX: Dynamically size num_ctx based on prompt length.
    Keeps VRAM KV-cache lean and reduces Time-To-First-Token (TTFT).
    Clamps between OLLAMA_CTX_MIN and OLLAMA_CTX_MAX.
    """
    prompt_tokens = _estimate_tokens(system_prompt + user_prompt)
    # Add OLLAMA_MAX_PREDICT headroom for output tokens
    needed = prompt_tokens + OLLAMA_MAX_PREDICT + 64
    clamped = max(OLLAMA_CTX_MIN, min(OLLAMA_CTX_MAX, needed))
    return clamped


def _strip_markdown(text):
    """
    FIX: Strip common markdown that renders poorly in Tkinter ScrolledText.
    Converts ** bold **, ## headers, and code fences to plain text.
    """
    import re
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)     # **bold** -> bold
    text = re.sub(r'\*(.+?)\*',   r'\1', text)        # *italic* -> italic
    text = re.sub(r'^#{1,4}\s*',  '',    text, flags=re.MULTILINE)  # ## Header
    text = re.sub(r'```[a-z]*\n', '',    text)        # ```code blocks
    text = re.sub(r'```',         '',    text)
    text = re.sub(r'`(.+?)`',    r'\1', text)         # `inline code`
    return text


# ══════════════════════════════════════════════════════════════════════════════
class OllamaEngine:
    """
    Communicates with a locally-running Ollama instance.
    FIX: endpoint config pulled from constants.py — switch to LM Studio by
    changing OLLAMA_BASE_URL and the payload schema below.
    """

    BASE = OLLAMA_BASE_URL
    _active_request_id = None   # used for clean stop

    # ── Service discovery ─────────────────────────────────────────────────
    @staticmethod
    def ping(timeout=2):
        """Return True if Ollama is reachable."""
        try:
            urllib.request.urlopen(f"{OllamaEngine.BASE}/", timeout=timeout)
            return True
        except Exception:
            return False

    @staticmethod
    def list_models():
        """Return list of installed model names."""
        try:
            req = urllib.request.Request(f"{OllamaEngine.BASE}/api/tags")
            with urllib.request.urlopen(req, timeout=4) as r:
                data = json.loads(r.read())
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    # ── Stop generation cleanly ───────────────────────────────────────────
    @staticmethod
    def request_stop(model_name):
        """
        FIX: Send DELETE to Ollama's generate endpoint to stop server-side
        inference, freeing GPU cycles immediately rather than letting the
        model run to its token limit in the background.
        Runs in its own thread to avoid blocking the UI.
        """
        def _do():
            try:
                body = json.dumps({"model": model_name}).encode()
                req  = urllib.request.Request(
                    f"{OllamaEngine.BASE}/api/generate",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="DELETE",
                )
                urllib.request.urlopen(req, timeout=3)
            except Exception:
                pass   # Ollama may not support DELETE on older versions; ignore
        threading.Thread(target=_do, daemon=True).start()

    # ── Clear AI Cache & Session ──────────────────────────────────────────
    @staticmethod
    def clear_cache(model_name=None):
        """
        FIX: Explicitly purge Ollama's KV context cache and unload active session
        when switching charts or importing a new kundali.
        Prevents cross-chart context leakage, KV-cache pollution, and catastrophic
        forgetting of chart-specific constraints.
        """
        def _do():
            if not model_name:
                return
            # 1. Cancel in-flight generation
            try:
                body = json.dumps({"model": model_name}).encode()
                req  = urllib.request.Request(
                    f"{OllamaEngine.BASE}/api/generate",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="DELETE",
                )
                urllib.request.urlopen(req, timeout=2)
            except Exception:
                pass

            # 2. Release KV cache by setting keep_alive: 0
            try:
                body = json.dumps({
                    "model": model_name,
                    "keep_alive": 0,
                }).encode()
                req = urllib.request.Request(
                    f"{OllamaEngine.BASE}/api/generate",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=3)
            except Exception:
                pass

        threading.Thread(target=_do, daemon=True).start()

    # ── Main streaming generation ─────────────────────────────────────────
    @staticmethod
    def generate_stream(
        model,
        system_prompt,
        user_prompt,
        token_cb,       # callable(str) — one clean text token
        done_cb,        # callable(str|None) — None=ok, str=error
        cancel_event,   # threading.Event
    ):
        """
        Stream generation.  Runs in the caller's background thread.
        Tokens are stripped of markdown before delivery via token_cb.

        Dynamic context: num_ctx is computed per-call from prompt length,
        eliminating the hardcoded 4096 that wasted KV-cache VRAM.
        """
        ctx   = _dynamic_ctx(system_prompt, user_prompt)
        body  = {
            "model":  model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": True,
            "options": {
                "num_gpu":        OLLAMA_GPU_LAYERS,
                "num_ctx":        ctx,
                "temperature":    OLLAMA_TEMPERATURE,
                "top_p":          OLLAMA_TOP_P,
                "repeat_penalty": OLLAMA_REPEAT_PENALTY,
                "num_predict":    OLLAMA_MAX_PREDICT,
                "stop":           ["\n\n\n"],
            },
        }
        data = json.dumps(body).encode()
        req  = urllib.request.Request(
            f"{OllamaEngine.BASE}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                for raw in resp:
                    if cancel_event.is_set():
                        break
                    if not raw.strip():
                        continue
                    try:
                        chunk = json.loads(raw.decode("utf-8", errors="replace"))
                    except json.JSONDecodeError:
                        continue
                    token = chunk.get("response", "")
                    if token:
                        token_cb(_strip_markdown(token))
                    if chunk.get("done", False):
                        break
            done_cb(None)
        except urllib.error.URLError as exc:
            done_cb(f"Connection error: {exc.reason}")
        except Exception as exc:
            done_cb(str(exc))
