# -*- coding: utf-8 -*-
"""
ollama_engine.py
================
Fully-offline LLM integration via local Ollama instance.
Supports local reasoning models (DeepSeek-R1, QwQ, Qwen-2.5) with streaming
thinking isolation, dynamic context budgeting, and cutoff prevention.

Key Capabilities:
-----------------
* Thinking Tag Isolation: Isolates <think>...</think> stream tokens using a
  sliding window parser. Prevents internal CoT/monologue from leaking into
  the user prediction view while allowing opt-in inspection.
* Mid-Generation Cutoff Prevention: Removes premature stop-tokens (like "\n\n\n"),
  expands prediction headroom to OLLAMA_MAX_PREDICT, and handles length limits.
* Continuation Support: Exposes done_reason ("stop" vs "length") so callers
  can seamlessly trigger continuous generation.
* Dynamic Context Budgeting: Computes num_ctx dynamically from prompt length
  plus prediction budget, bounded by OLLAMA_CTX_MIN and OLLAMA_CTX_MAX (up to 8k).
* Clean Stop & KV Purge: Sends DELETE and keep_alive: 0 to free GPU resources.
"""

import json
import inspect
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


def _dynamic_ctx(system_prompt, user_prompt, max_predict=None):
    """
    Dynamically size num_ctx based on prompt length and expected output.
    Keeps VRAM KV-cache lean and TTFT fast, while avoiding context starvation.
    Clamps between OLLAMA_CTX_MIN and OLLAMA_CTX_MAX.
    """
    pred = max_predict if max_predict is not None else OLLAMA_MAX_PREDICT
    prompt_tokens = _estimate_tokens(system_prompt + user_prompt)
    needed = prompt_tokens + pred + 128
    clamped = max(OLLAMA_CTX_MIN, min(OLLAMA_CTX_MAX, needed))
    return clamped


class ThinkingStreamParser:
    """
    Streams tokens while isolating and parsing <think>...</think> blocks.
    Guarantees that internal model monologue/reasoning is never leaked into
    the client prediction view unless explicitly routed to a thinking callback.
    """

    def __init__(self, token_cb, thinking_cb=None):
        self.token_cb = token_cb
        self.thinking_cb = thinking_cb
        self.in_thinking = False
        self.buffer = ""
        self.THINK_OPEN = "<think>"
        self.THINK_CLOSE = "</think>"

    def feed(self, chunk):
        if not chunk:
            return
        self.buffer += chunk
        self._process()

    def _process(self):
        while self.buffer:
            if not self.in_thinking:
                idx = self.buffer.find(self.THINK_OPEN)
                if idx != -1:
                    pre = self.buffer[:idx]
                    if pre and self.token_cb:
                        self.token_cb(pre)
                    self.in_thinking = True
                    self.buffer = self.buffer[idx + len(self.THINK_OPEN):]
                else:
                    # Check for partial open tag at buffer end
                    partial_len = 0
                    for i in range(1, len(self.THINK_OPEN)):
                        if self.THINK_OPEN.startswith(self.buffer[-i:]):
                            partial_len = i
                            break
                    if partial_len > 0:
                        emit_len = len(self.buffer) - partial_len
                        if emit_len > 0:
                            pre = self.buffer[:emit_len]
                            if pre and self.token_cb:
                                self.token_cb(pre)
                            self.buffer = self.buffer[emit_len:]
                        break
                    else:
                        if self.token_cb:
                            self.token_cb(self.buffer)
                        self.buffer = ""
            else:
                idx = self.buffer.find(self.THINK_CLOSE)
                if idx != -1:
                    think_text = self.buffer[:idx]
                    if think_text and self.thinking_cb:
                        self.thinking_cb(think_text)
                    self.in_thinking = False
                    self.buffer = self.buffer[idx + len(self.THINK_CLOSE):]
                else:
                    # Check for partial close tag at buffer end
                    partial_len = 0
                    for i in range(1, len(self.THINK_CLOSE)):
                        if self.THINK_CLOSE.startswith(self.buffer[-i:]):
                            partial_len = i
                            break
                    if partial_len > 0:
                        emit_len = len(self.buffer) - partial_len
                        if emit_len > 0:
                            think_text = self.buffer[:emit_len]
                            if think_text and self.thinking_cb:
                                self.thinking_cb(think_text)
                            self.buffer = self.buffer[emit_len:]
                        break
                    else:
                        if self.thinking_cb:
                            self.thinking_cb(self.buffer)
                        self.buffer = ""

    def finish(self):
        if self.buffer:
            if self.in_thinking and self.thinking_cb:
                self.thinking_cb(self.buffer)
            elif not self.in_thinking and self.token_cb:
                self.token_cb(self.buffer)
            self.buffer = ""


def _call_done(done_cb, err, done_reason=None):
    """Safely call done_cb supporting both 1-arg and 2-arg signatures."""
    if not done_cb:
        return
    try:
        sig = inspect.signature(done_cb)
        if len(sig.parameters) >= 2:
            done_cb(err, done_reason)
        else:
            done_cb(err)
    except Exception:
        try:
            done_cb(err)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
class OllamaEngine:
    """
    Communicates with a locally-running Ollama instance.
    Centralized endpoint config in constants.py.
    """

    BASE = OLLAMA_BASE_URL
    _active_request_id = None

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
        Send DELETE to Ollama's generate endpoint to stop server-side inference,
        freeing GPU cycles immediately.
        """
        def _do():
            try:
                body = json.dumps({"model": model_name}).encode()
                req = urllib.request.Request(
                    f"{OllamaEngine.BASE}/api/generate",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="DELETE",
                )
                urllib.request.urlopen(req, timeout=3)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    # ── Clear AI Cache & Session ──────────────────────────────────────────
    @staticmethod
    def clear_cache(model_name=None):
        """
        Purge Ollama's KV context cache and unload active session.
        Prevents cross-chart context leakage and KV pollution.
        """
        def _do():
            if not model_name:
                return
            try:
                body = json.dumps({"model": model_name}).encode()
                req = urllib.request.Request(
                    f"{OllamaEngine.BASE}/api/generate",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="DELETE",
                )
                urllib.request.urlopen(req, timeout=2)
            except Exception:
                pass

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
        token_cb,               # callable(str) — plain text token
        done_cb,                # callable(err, done_reason=None)
        cancel_event,           # threading.Event
        thinking_cb=None,       # optional callable(str) for <think> reasoning tokens
        num_predict=None,       # optional int override for token budget
        temperature=None,       # optional float override
    ):
        """
        Stream generation in caller's thread with thinking tag isolation.
        - Isolates <think>...</think> reasoning blocks via ThinkingStreamParser.
        - Eliminates premature newline cutoff.
        - Dispatches done_reason ("stop" or "length") to done_cb.
        """
        pred_limit = num_predict if num_predict is not None else OLLAMA_MAX_PREDICT
        temp = temperature if temperature is not None else OLLAMA_TEMPERATURE
        ctx = _dynamic_ctx(system_prompt, user_prompt, max_predict=pred_limit)

        body = {
            "model": model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": True,
            "options": {
                "num_gpu": OLLAMA_GPU_LAYERS,
                "num_ctx": ctx,
                "temperature": temp,
                "top_p": OLLAMA_TOP_P,
                "repeat_penalty": OLLAMA_REPEAT_PENALTY,
                "num_predict": pred_limit,
                # Proper model stop tokens instead of "\n\n\n"
                "stop": ["<|im_end|>", "<|endoftext|>", "</s>", "[END_READING]"],
            },
        }

        parser = ThinkingStreamParser(token_cb=token_cb, thinking_cb=thinking_cb)
        last_done_reason = "stop"

        data = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{OllamaEngine.BASE}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                for raw in resp:
                    if cancel_event.is_set():
                        last_done_reason = "cancelled"
                        break
                    if not raw.strip():
                        continue
                    try:
                        chunk = json.loads(raw.decode("utf-8", errors="replace"))
                    except json.JSONDecodeError:
                        continue

                    token = chunk.get("response", "")
                    if token:
                        parser.feed(token)

                    if chunk.get("done", False):
                        last_done_reason = chunk.get("done_reason", "stop")
                        break

            parser.finish()
            _call_done(done_cb, None, last_done_reason)
        except urllib.error.URLError as exc:
            parser.finish()
            _call_done(done_cb, f"Connection error: {exc.reason}", "error")
        except Exception as exc:
            parser.finish()
            _call_done(done_cb, str(exc), "error")
