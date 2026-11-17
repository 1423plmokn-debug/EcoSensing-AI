"""
EcoSensing AI – Central Dynamic Groq Cloud Orchestration Service
100% Real Live AI Enforcement – Zero Canned / Deterministic Fallback Texts.
Dual-Key Automatic Failover (Primary -> Backup) & Dynamic Active Model Discovery.
Academic Affiliation: Middle Technical University / Polytechnic College
"""

from __future__ import annotations

import base64
import datetime
import json
import logging
import re
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.config import sanitize_emojis, settings

logger = logging.getLogger("EcoSensing.GroqService")

try:
    from groq import Groq
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False
    Groq = None


# Cached models catalog per API key: api_key -> (timestamp, model_ids_list)
_MODELS_CACHE_BY_KEY: Dict[str, Tuple[float, List[str]]] = {}
_CACHE_TTL_SECONDS = 600.0


def parse_json_safely(raw: str) -> Dict[str, Any]:
    """
    Robust JSON parser engineered to prevent Unterminated string and EOF truncation failures:
    1. Strips markdown fences (```json ... ```).
    2. Isolates JSON payload starting from the first '{'.
    3. Quotes unquoted fractions (e.g. 3.7/10 -> "3.7/10").
    4. Auto-heals truncated strings, colons, commas, and unmatched brackets via character-by-character scan.
    5. Fallback regex field-extractor guarantees real LLM output is never discarded.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Extract outermost JSON object if surrounded by prose
    start_idx = cleaned.find("{")
    if start_idx != -1:
        cleaned = cleaned[start_idx:]

    # Fix unquoted fractions like 3.7/10 or 7/10
    cleaned = re.sub(r'(?<=[:\s])(\d+(?:\.\d+)?)\s*/\s*(\d+)(?=[,\s\}\]])', r'"\1/\2"', cleaned)

    try:
        return json.loads(cleaned, strict=False)
    except Exception:
        pass

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        candidate = match.group(0)
        candidate = re.sub(r'(?<=[:\s])(\d+(?:\.\d+)?)\s*/\s*(\d+)(?=[,\s\}\]])', r'"\1/\2"', candidate)
        try:
            return json.loads(candidate, strict=False)
        except Exception:
            pass

    # Resilient character-by-character auto-healing for truncated strings and bracket stacks
    in_string = False
    escape = False
    stack: List[str] = []
    for c in cleaned:
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c == "{":
                stack.append("}")
            elif c == "[":
                stack.append("]")
            elif c == "}":
                if stack and stack[-1] == "}":
                    stack.pop()
            elif c == "]":
                if stack and stack[-1] == "]":
                    stack.pop()

    repaired = cleaned
    if in_string:
        repaired += '"'

    repaired = repaired.rstrip()
    while repaired and repaired[-1] in (",", ":"):
        if repaired.endswith(":"):
            repaired += ' ""'
            break
        repaired = repaired[:-1].rstrip()

    for closing in reversed(stack):
        repaired += closing

    try:
        return json.loads(repaired, strict=False)
    except Exception:
        pass

    # Regex field-extractor backup to ensure real vision/text output is never discarded
    extracted: Dict[str, Any] = {}
    str_matches = re.findall(r'"([a-zA-Z0-9_]+)"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"?', cleaned)
    for k, v in str_matches:
        extracted[k] = v

    num_matches = re.findall(r'"([a-zA-Z0-9_]+)"\s*:\s*(-?\d+(?:\.\d+)?)(?=[,\s\}\]])', cleaned)
    for k, v in num_matches:
        if k not in extracted:
            try:
                extracted[k] = float(v) if "." in v else int(v)
            except Exception:
                extracted[k] = v

    if extracted and ("scientific_name" in extracted or "arabic_common_name" in extracted or "specimen_category" in extracted or "visual_symptoms_ar" in extracted or "investigator_reply_ar" in extracted):
        return extracted

    return json.loads(cleaned)


class GroqService:
    """
    Central, zero-compromise Groq Cloud inference service:
    - Dual-Key automatic failover (Primary -> Backup) on 429/401/403.
    - Dynamic active model discovery from account catalog.
    - Resilient JSON parsing without buggy server-side json_object enforcement.
    - 18.0s realistic cloud timeout.
    """

    @classmethod
    def get_client_for_key(cls, api_key: str, timeout: float = 18.0) -> Optional[Any]:
        """Instantiate Groq client with specified key and timeout."""
        if not _GROQ_AVAILABLE or not api_key:
            return None
        return Groq(api_key=api_key.strip(), timeout=timeout)

    @classmethod
    def execute_groq_with_failover(
        cls,
        call_fn: Callable[[Any, str], Any],
        timeout: float = 18.0,
    ) -> Any:
        """
        Execute a Groq call with dual-key automatic failover:
        1. Verifies Groq SDK availability.
        2. Attempts PRIMARY key first.
        3. On 429 Rate Limit, 401/403 Auth error, immediately switches to BACKUP key.
        4. Raises transparent diagnostic exception if both fail.
        """
        if not _GROQ_AVAILABLE:
            raise RuntimeError(
                "Groq Python SDK ('groq') is not installed in the active Python environment. "
                "Please run: pip install groq"
            )

        primary_key = (settings.GROQ_API_KEY_PRIMARY or settings.GROQ_API_KEY or "").strip()
        backup_key = (settings.GROQ_API_KEY_BACKUP or "").strip()

        if not primary_key and not backup_key:
            raise RuntimeError("No Groq API keys configured. Please set GROQ_API_KEY_PRIMARY or GROQ_API_KEY in .env.")

        last_exc: Optional[Exception] = None

        # Attempt 1: Primary Key
        if primary_key:
            try:
                primary_client = cls.get_client_for_key(primary_key, timeout=timeout)
                if primary_client:
                    return call_fn(primary_client, "PRIMARY")
                else:
                    last_exc = RuntimeError("Failed to instantiate Groq client for PRIMARY key.")
            except Exception as exc:
                last_exc = exc
                err_str = str(exc).lower()
                is_failover_worthy = any(
                    code in err_str
                    for code in ["429", "rate limit", "ratelimit", "tokens per day", "tpd", "401", "403", "unauthorized"]
                )
                logger.warning("Groq Primary Key failed (%s). Failover eligible: %s", exc, is_failover_worthy)
                if not is_failover_worthy and (not backup_key or backup_key == primary_key):
                    raise exc

        # Attempt 2: Backup Key
        if backup_key and backup_key != primary_key:
            logger.info("Executing Groq automatic failover to BACKUP key...")
            try:
                backup_client = cls.get_client_for_key(backup_key, timeout=timeout)
                if backup_client:
                    return call_fn(backup_client, "BACKUP")
                else:
                    last_exc = RuntimeError("Failed to instantiate Groq client for BACKUP key.")
            except Exception as exc:
                last_exc = exc
                logger.error("Groq Backup Key also failed: %s", exc)

        err_msg = f"All Groq Cloud keys failed. Last exception: {last_exc}"
        logger.error(err_msg)
        raise RuntimeError(err_msg)

    @classmethod
    def get_discovered_models(cls, client: Any) -> List[str]:
        """Dynamically query Groq models catalog with per-key in-memory caching."""
        global _MODELS_CACHE_BY_KEY
        api_key = getattr(client, "api_key", "default")
        now = time.time()

        if api_key in _MODELS_CACHE_BY_KEY:
            cache_time, models_list = _MODELS_CACHE_BY_KEY[api_key]
            if (now - cache_time) < _CACHE_TTL_SECONDS and models_list:
                return models_list

        try:
            resp = client.models.list()
            models_data = resp.data if hasattr(resp, "data") else []
            model_ids = [getattr(m, "id", "") for m in models_data if getattr(m, "id", "")]
            _MODELS_CACHE_BY_KEY[api_key] = (now, model_ids)
            return model_ids
        except Exception as exc:
            logger.warning("Failed to query client.models.list(): %s", exc)
            if api_key in _MODELS_CACHE_BY_KEY:
                return _MODELS_CACHE_BY_KEY[api_key][1]
            return []

    @classmethod
    def discover_vision_models(cls, client: Any) -> List[str]:
        """
        Dynamically determine active vision models on this account.
        Checks settings.GROQ_VISION_MODEL first, then priority candidates against discovered models.
        """
        active_ids = set(cls.get_discovered_models(client))
        configured_vision = (getattr(settings, "GROQ_VISION_MODEL", "") or "").strip()

        priority_candidates = [
            configured_vision,
            "qwen/qwen3.8-27b",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
        ]
        available_vision = [m for m in priority_candidates if m and m in active_ids]

        # Dynamic fallback: check any discovered models with vision/qwen tags
        if not available_vision:
            for m in active_ids:
                if any(tag in m.lower() for tag in ["vision", "vl", "qwen", "multimodal"]):
                    if m not in available_vision:
                        available_vision.append(m)

        return available_vision

    @classmethod
    def discover_text_models(cls, client: Any) -> List[str]:
        """
        Dynamically determine active text models on this account.
        Checks settings.GROQ_MODEL first, then priority candidates against discovered models.
        """
        active_ids = set(cls.get_discovered_models(client))
        configured_text = (getattr(settings, "GROQ_MODEL", "") or "").strip()

        priority_candidates = [
            configured_text,
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.8-27b",
            "allam-2-7b",
            "llama-3.3-70b-versatile",
        ]
        available_text = [m for m in priority_candidates if m and m in active_ids]

        # Append any remaining active analytical models
        for m in sorted(active_ids):
            if (
                m not in available_text
                and not m.startswith("whisper")
                and "guard" not in m
                and not m.startswith("canopylabs")
            ):
                available_text.append(m)

        return available_text

    @classmethod
    def call_vision(
        cls,
        image_bytes: bytes,
        system_prompt: str,
        user_prompt: str,
        biometric_fallback_prompt: str = "",
        max_tokens: int = 8192,
        temperature: float = 0.20,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Execute Groq Vision analysis with dual-key failover:
        1. Attempt discovered multimodal vision models in priority order.
        2. STRICT ZERO-HALLUCINATION ENFORCEMENT: Never fall back to blind text-only
           models (e.g. gpt-oss-120b) that cannot see image pixels.
        3. Returns (parsed_json_dict, ai_telemetry_dict).
        Raises RuntimeError with transparent details if all vision calls fail.
        """
        b64_img = base64.b64encode(image_bytes).decode("utf-8")

        def _do_call(client: Any, key_label: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
            vision_models = cls.discover_vision_models(client)
            if not vision_models:
                all_discovered = cls.get_discovered_models(client)
                for m in all_discovered:
                    if ("vision" in m.lower() or "qwen" in m.lower()) and m not in vision_models:
                        vision_models.append(m)

            if not vision_models:
                raise RuntimeError(f"No multimodal vision models available on Groq key [{key_label}].")

            last_err: Optional[Exception] = None

            for v_model in vision_models:
                t0 = time.perf_counter()
                eff_tokens = max_tokens
                logger.info("[%s] Attempting Groq Vision model: %s (max_tokens: %d)", key_label, v_model, eff_tokens)
                for attempt in range(2):
                    try:
                        u_prompt = user_prompt if attempt == 0 else (user_prompt + "\nيرجى الاختصار والإجابة المباشرة المركزة بصيغة JSON.")
                        resp = client.chat.completions.create(
                            model=v_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": u_prompt},
                                        {
                                            "type": "image_url",
                                            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                                        },
                                    ],
                                },
                            ],
                            temperature=temperature,
                            max_tokens=eff_tokens,
                        )
                        content = resp.choices[0].message.content
                        if content:
                            parsed = parse_json_safely(content)
                            elapsed_ms = int((time.perf_counter() - t0) * 1000)
                            req_id = getattr(resp, "id", None) or f"groq-{uuid.uuid4().hex[:8]}"
                            telemetry = {
                                "model_name": f"{v_model} ({key_label})",
                                "latency_ms": elapsed_ms,
                                "request_id": req_id,
                                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                "is_live_cloud": True,
                            }
                            return sanitize_emojis(parsed), telemetry
                    except Exception as exc:
                        last_err = exc
                        err_str = str(exc).lower()
                        logger.warning("[%s] Vision model %s (attempt %d) failed: %s", key_label, v_model, attempt + 1, exc)
                        if "429" in err_str or "rate limit" in err_str or "tokens per day" in err_str or "tpd" in err_str:
                            raise exc  # Trigger key failover to BACKUP key immediately
                        if "max_tokens" in err_str or "maximum context" in err_str:
                            eff_tokens = 4096
                            continue
                        if attempt == 0:
                            continue

            raise RuntimeError(f"All multimodal vision models exhausted on {key_label}. Last error: {last_err}")

        return cls.execute_groq_with_failover(_do_call, timeout=22.0)

    @classmethod
    def call_text(
        cls,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8192,
        temperature: float = 0.20,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Execute Groq Text inference with dual-key failover and 18.0s timeout.
        Returns (parsed_json_dict, ai_telemetry_dict).
        Raises RuntimeError with exact exception if all live Groq calls fail.
        """
        def _do_call(client: Any, key_label: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
            text_models = cls.discover_text_models(client)
            last_err: Optional[Exception] = None

            for t_model in text_models:
                t0 = time.perf_counter()
                eff_tokens = max_tokens
                logger.info("[%s] Attempting Groq Text Model: %s (tokens: %d)", key_label, t_model, eff_tokens)
                for attempt in range(2):
                    try:
                        resp = client.chat.completions.create(
                            model=t_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=temperature,
                            max_tokens=eff_tokens,
                        )
                        content = resp.choices[0].message.content
                        if content:
                            parsed = parse_json_safely(content)
                            elapsed_ms = int((time.perf_counter() - t0) * 1000)
                            req_id = getattr(resp, "id", None) or f"groq-{uuid.uuid4().hex[:8]}"
                            telemetry = {
                                "model_name": f"{t_model} ({key_label})",
                                "latency_ms": elapsed_ms,
                                "request_id": req_id,
                                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                "is_live_cloud": True,
                            }
                            return sanitize_emojis(parsed), telemetry
                    except Exception as exc:
                        last_err = exc
                        err_str = str(exc).lower()
                        logger.warning("[%s] Text model %s attempt %d failed: %s", key_label, t_model, attempt + 1, exc)
                        if "429" in err_str or "rate limit" in err_str or "tokens per day" in err_str or "tpd" in err_str:
                            raise exc  # Trigger key failover
                        if "max_tokens" in err_str or "maximum context" in err_str:
                            eff_tokens = 4096
                            continue
                        if attempt == 0:
                            continue

            raise RuntimeError(f"All text models exhausted on {key_label}. Last exception: {last_err}")

        return cls.execute_groq_with_failover(_do_call, timeout=18.0)
