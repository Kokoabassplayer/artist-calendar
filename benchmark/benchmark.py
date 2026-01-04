#!/usr/bin/env python3
import argparse
import base64
import csv
import hashlib
import json
import os
import random
import re
import shutil
import statistics
import subprocess
import threading
import time
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import requests

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional for bench runs
    load_dotenv = None

try:
    from google import genai
    from google.genai import errors, types
except Exception:  # pragma: no cover - optional dependency in bench runs
    genai = None
    errors = None
    types = None


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
DEFAULT_TEMPERATURE = 0.2
DEFAULT_SEED = 23
DEFAULT_OPENROUTER_TIMEOUT = 300
DEFAULT_OLLAMA_TIMEOUT = 600
DEFAULT_GEMINI_PROMPT_TOKENS = 2000
DEFAULT_GEMINI_OUTPUT_TOKENS = 2000
PROVINCE_DATA_PATH = Path("benchmark/data/th_provinces.json")
VENUE_KEYWORDS = (
    "cafe",
    "café",
    "bar",
    "pub",
    "club",
    "hall",
    "stage",
    "theatre",
    "theater",
    "arena",
    "restaurant",
    "music bar",
    "livehouse",
    "lounge",
    "studio",
    "center",
    "centre",
    "mall",
    "market",
    "ร้าน",
    "คาเฟ่",
    "คาเฟ",
    "บาร์",
    "ผับ",
    "ฮอลล์",
    "เวที",
    "สเตจ",
    "โรงละคร",
    "หอประชุม",
    "ศูนย์",
    "สเตเดียม",
    "สนาม",
)
BOOTSTRAP_SAMPLES = 1000
BOOTSTRAP_SEED = 23
BOOTSTRAP_ALPHA = 0.05
TOP_LEVEL_WEIGHTS = {
    "artist_name": 0.35,
    "instagram_handle": 0.15,
    "tour_name": 0.2,
    "contact_info": 0.1,
    "source_month": 0.2,
}
EVENT_SCORE_WEIGHTS = {
    "date": 0.3,
    "time": 0.05,
    "venue": 0.2,
    "city": 0.15,
    "province": 0.1,
    "country": 0.05,
    "event_name": 0.05,
    "ticket_info": 0.05,
    "status": 0.05,
}
CORE_EVENT_SCORE_WEIGHTS = {
    "date": 0.375,
    "venue": 0.25,
    "city": 0.1875,
    "province": 0.125,
    "country": 0.0625,
}
QUALITY_WEIGHTS = {
    "structured": 0.4,
    "event_match": 0.35,
    "top_level": 0.15,
    "event_count": 0.1,
}
MISSING_FIELD_PENALTY = 10.0
POSTER_SCHEMA_NAME = "poster_extraction"
JUDGE_SCHEMA_NAME = "judge_result"
POSTER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "artist_name",
        "instagram_handle",
        "tour_name",
        "contact_info",
        "source_month",
        "poster_confidence",
        "events",
    ],
    "properties": {
        "artist_name": {"type": "string"},
        "instagram_handle": {"type": ["string", "null"]},
        "tour_name": {"type": ["string", "null"]},
        "contact_info": {"type": ["string", "null"]},
        "source_month": {"type": "string", "pattern": r"^\d{4}-\d{2}$"},
        "poster_confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "date",
                    "event_name",
                    "venue",
                    "city",
                    "province",
                    "country",
                    "time",
                    "ticket_info",
                    "status",
                    "confidence",
                ],
                "properties": {
                    "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                    "event_name": {"type": ["string", "null"]},
                    "venue": {"type": ["string", "null"]},
                    "city": {"type": ["string", "null"]},
                    "province": {"type": ["string", "null"]},
                    "country": {"type": "string"},
                    "time": {
                        "anyOf": [
                            {"type": "null"},
                            {"type": "string", "pattern": r"^\d{2}:\d{2}$"},
                        ]
                    },
                    "ticket_info": {"type": ["string", "null"]},
                    "status": {
                        "type": "string",
                        "enum": ["active", "cancelled", "postponed"],
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        },
    },
}
JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "overall_score",
        "schema_ok",
        "event_count_score",
        "date_score",
        "venue_score",
        "location_score",
        "missing_field_penalty",
        "errors",
    ],
    "properties": {
        "overall_score": {"type": "number", "minimum": 0, "maximum": 100},
        "schema_ok": {"type": "boolean"},
        "event_count_score": {"type": "number", "minimum": 0, "maximum": 100},
        "date_score": {"type": "number", "minimum": 0, "maximum": 100},
        "venue_score": {"type": "number", "minimum": 0, "maximum": 100},
        "location_score": {"type": "number", "minimum": 0, "maximum": 100},
        "missing_field_penalty": {"type": "number", "minimum": 0, "maximum": 100},
        "errors": {"type": "array", "items": {"type": "string"}},
    },
}


def _parse_max_tokens(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip().lower()
    if text in {"max", "auto", "none"}:
        return None
    return int(text)


_OLLAMA_CONTEXT_CACHE: Dict[str, int] = {}
_GEMINI_OUTPUT_LIMIT_CACHE: Dict[str, int] = {}


def _ollama_context_length(model: str) -> Optional[int]:
    cached = _OLLAMA_CONTEXT_CACHE.get(model)
    if cached:
        return cached
    try:
        result = subprocess.run(
            ["ollama", "show", model],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    match = re.search(r"context length\\s+(\\d+)", result.stdout)
    if not match:
        return None
    length = int(match.group(1))
    _OLLAMA_CONTEXT_CACHE[model] = length
    return length


def _gemini_model_name(model: Optional[str]) -> Optional[str]:
    if not model:
        return None
    return model if model.startswith("models/") else f"models/{model}"


def _gemini_output_limit(model: Optional[str]) -> Optional[int]:
    name = _gemini_model_name(model)
    if not name:
        return None
    cached = _GEMINI_OUTPUT_LIMIT_CACHE.get(name)
    if cached:
        return cached
    if genai is None:
        return None
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        client = genai.Client(api_key=api_key)
        info = client.models.get(model=name)
    except Exception:
        return None
    limit = getattr(info, "output_token_limit", None)
    if isinstance(limit, int) and limit > 0:
        _GEMINI_OUTPUT_LIMIT_CACHE[name] = limit
        return limit
    return None


def _load_plugins_config(value: Optional[str]) -> Optional[List[Dict[str, Any]]]:
    if not value:
        return None
    text = value
    if Path(value).exists():
        text = Path(value).read_text(encoding="utf-8")
    plugins = json.loads(text)
    if isinstance(plugins, dict) and "plugins" in plugins:
        plugins = plugins["plugins"]
    if not isinstance(plugins, list):
        raise ValueError("OpenRouter plugins must be a JSON array or an object with a 'plugins' array.")
    return plugins


def _resolve_max_output(
    value: Optional[str],
    *,
    kind: Optional[str] = None,
    model: Optional[str] = None,
    context_override: Optional[int] = None,
) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"max", "auto", "none"}:
        if text == "max" and kind == "gemini":
            return _gemini_output_limit(model)
        return None
    if text == "half":
        if kind == "ollama":
            length = context_override
            if length is None and model:
                length = _ollama_context_length(model)
            if length:
                return max(1, length // 2)
        return None
    return _parse_max_tokens(value)


class RateLimiter:
    def __init__(self, rpm: Optional[int] = None, tpm: Optional[int] = None, tokens_per_request: Optional[int] = None):
        self.rpm = rpm
        self.tpm = tpm
        self.tokens_per_request = tokens_per_request
        self._lock = threading.Lock()
        self._request_times: Deque[float] = deque()
        self._token_times: Deque[Tuple[float, int]] = deque()

    def acquire(self, tokens: Optional[int] = None) -> None:
        if self.rpm is None and self.tpm is None:
            return
        token_cost = tokens if tokens is not None else self.tokens_per_request
        while True:
            now = time.monotonic()
            with self._lock:
                window = 60.0
                while self._request_times and now - self._request_times[0] >= window:
                    self._request_times.popleft()
                while self._token_times and now - self._token_times[0][0] >= window:
                    self._token_times.popleft()
                token_sum = sum(cost for _, cost in self._token_times) if self.tpm and token_cost else 0
                rpm_ok = self.rpm is None or len(self._request_times) < self.rpm
                tpm_ok = self.tpm is None or token_cost is None or (token_sum + token_cost) <= self.tpm
                if rpm_ok and tpm_ok:
                    self._request_times.append(now)
                    if self.tpm and token_cost is not None:
                        self._token_times.append((now, token_cost))
                    return
                wait_rpm = 0.0
                wait_tpm = 0.0
                if self.rpm is not None and len(self._request_times) >= self.rpm:
                    wait_rpm = window - (now - self._request_times[0])
                if self.tpm is not None and token_cost is not None and token_sum + token_cost > self.tpm:
                    wait_tpm = window - (now - self._token_times[0][0])
                wait_for = max(wait_rpm, wait_tpm, 0.05)
            time.sleep(wait_for)


def _estimate_gemini_tokens(max_output_tokens: Optional[int]) -> int:
    output_tokens = max_output_tokens if max_output_tokens is not None else DEFAULT_GEMINI_OUTPUT_TOKENS
    return max(1, output_tokens + DEFAULT_GEMINI_PROMPT_TOKENS)


_PROVINCES_CACHE: Optional[List[Dict[str, Any]]] = None


def _load_provinces() -> List[Dict[str, Any]]:
    global _PROVINCES_CACHE
    if _PROVINCES_CACHE is not None:
        return _PROVINCES_CACHE
    if not PROVINCE_DATA_PATH.exists():
        _PROVINCES_CACHE = []
        return _PROVINCES_CACHE
    try:
        data = json.loads(PROVINCE_DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        _PROVINCES_CACHE = []
        return _PROVINCES_CACHE
    if not isinstance(data, list):
        _PROVINCES_CACHE = []
        return _PROVINCES_CACHE
    _PROVINCES_CACHE = [item for item in data if isinstance(item, dict)]
    return _PROVINCES_CACHE


def _find_province_in_text(text: Any) -> Optional[str]:
    if not isinstance(text, str) or not text.strip():
        return None
    provinces = _load_provinces()
    if not provinces:
        return None
    for entry in provinces:
        aliases = entry.get("aliases") or []
        for alias in aliases:
            if not isinstance(alias, str) or not alias:
                continue
            if alias.isascii():
                pattern = r"\\b" + re.escape(alias) + r"\\b"
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    return text[match.start() : match.end()]
            else:
                if alias in text:
                    return alias
    return None


def _looks_like_venue(text: Any) -> bool:
    if not isinstance(text, str):
        return False
    stripped = text.strip()
    if not stripped:
        return False
    lowered = stripped.lower()
    for keyword in VENUE_KEYWORDS:
        if keyword.isascii():
            if keyword in lowered:
                return True
        else:
            if keyword in stripped:
                return True
    return False


def _split_event_name_for_venue(text: Any) -> Tuple[Optional[str], Optional[str]]:
    if not isinstance(text, str):
        return None, None
    stripped = text.strip()
    if not stripped:
        return None, None
    patterns = [
        r"\\s*@\\s*",
        r"\\s+at\\s+",
        r"\\s+ณ\\s+",
        r"\\s+ที่\\s+",
    ]
    for pattern in patterns:
        parts = re.split(pattern, stripped, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            left = parts[0].strip()
            right = parts[1].strip()
            if right:
                return left or None, right
    return None, None


def read_lines(path: Path) -> List[str]:
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        lines.append(cleaned)
    return list(dict.fromkeys(lines))


def read_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def safe_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", name)


def extract_shortcode(url: str) -> Optional[str]:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    if not host.endswith("instagram.com"):
        return None
    parts = [part for part in parsed.path.split("/") if part]
    for idx, part in enumerate(parts[:-1]):
        if part in ("p", "reel", "tv"):
            return parts[idx + 1]
    return None


def id_for_url(url: str) -> str:
    shortcode = extract_shortcode(url)
    if shortcode:
        return shortcode
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return digest[:12]


def guess_extension(content_type: Optional[str], url: str) -> str:
    if content_type:
        media_type = content_type.split(";")[0].strip().lower()
        mapping = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        if media_type in mapping:
            return mapping[media_type]
    suffix = Path(urlparse(url).path).suffix
    if suffix:
        return suffix
    return ".jpg"


def extract_og_image(html: str) -> Optional[str]:
    patterns = [
        r'<meta[^>]+property=["\']og:image:secure_url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image:src["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def download_image(
    url: str,
    session: requests.Session,
    user_agent: str,
    timeout: float,
) -> Tuple[bytes, str, str]:
    headers = {"User-Agent": user_agent, "Accept": "image/*,text/html"}
    shortcode = extract_shortcode(url)
    if shortcode:
        media_url = f"https://www.instagram.com/p/{shortcode}/media/?size=l"
        resp = session.get(media_url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.ok and resp.headers.get("Content-Type", "").lower().startswith("image/"):
            ext = guess_extension(resp.headers.get("Content-Type"), resp.url or media_url)
            return resp.content, resp.url or media_url, ext

    resp = session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    if resp.ok and resp.headers.get("Content-Type", "").lower().startswith("image/"):
        ext = guess_extension(resp.headers.get("Content-Type"), resp.url or url)
        return resp.content, resp.url or url, ext

    html = resp.text if resp.ok else ""
    og_image = extract_og_image(html)
    if og_image:
        img_resp = session.get(og_image, headers=headers, timeout=timeout, allow_redirects=True)
        if img_resp.ok and img_resp.headers.get("Content-Type", "").lower().startswith("image/"):
            ext = guess_extension(img_resp.headers.get("Content-Type"), img_resp.url or og_image)
            return img_resp.content, img_resp.url or og_image, ext

    raise RuntimeError("No image found at URL.")


def load_manifest(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(path: Path, entries: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_json(text: str) -> Optional[Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    start = None
    end = None
    for idx, char in enumerate(cleaned):
        if char in "{[":
            start = idx
            break
    for idx in range(len(cleaned) - 1, -1, -1):
        if cleaned[idx] in "}]":
            end = idx
            break
    if start is not None and end is not None and end > start:
        snippet = cleaned[start : end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            return None
    return None


def _load_openrouter_pricing(cache_path: Path) -> Dict[str, Dict[str, Any]]:
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_openrouter_pricing(cache_path: Path, data: Dict[str, Dict[str, Any]]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _fetch_openrouter_pricing(cache_path: Path) -> Dict[str, Dict[str, Any]]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set.")
    response = requests.get(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    models = {}
    for item in data.get("data", []):
        name = item.get("id")
        if not name:
            continue
        pricing = item.get("pricing") or {}
        top_provider = item.get("top_provider") or {}
        models[name] = {
            "pricing": pricing,
            "context_length": item.get("context_length"),
            "max_completion_tokens": top_provider.get("max_completion_tokens"),
            "supported_parameters": item.get("supported_parameters") or [],
        }
    _save_openrouter_pricing(cache_path, models)
    return models


def _get_model_limits(cache_path: Path, model_id: str) -> Dict[str, Optional[int]]:
    data = _load_openrouter_pricing(cache_path)
    info = data.get(model_id) if isinstance(data, dict) else None
    if not info or ("max_completion_tokens" not in info and "context_length" not in info):
        try:
            data = _fetch_openrouter_pricing(cache_path)
        except Exception:
            data = {}
        info = data.get(model_id) if isinstance(data, dict) else None
    if not info:
        return {}
    return {
        "context_length": info.get("context_length"),
        "max_completion_tokens": info.get("max_completion_tokens"),
    }


def _model_supports_param(cache_path: Path, model_id: str, param: str) -> bool:
    data = _load_openrouter_pricing(cache_path)
    info = data.get(model_id) if isinstance(data, dict) else None
    supported = info.get("supported_parameters") if isinstance(info, dict) else None
    if supported is None:
        try:
            data = _fetch_openrouter_pricing(cache_path)
        except Exception:
            data = {}
        info = data.get(model_id) if isinstance(data, dict) else None
        supported = info.get("supported_parameters") if isinstance(info, dict) else None
    if not supported:
        return False
    return param in supported


def _get_pricing(cache_path: Path) -> Dict[str, Dict[str, Any]]:
    data = _load_openrouter_pricing(cache_path)
    if data:
        return data
    return _fetch_openrouter_pricing(cache_path)


def _openrouter_response_format(
    model: str, schema_name: str, schema: Dict[str, Any], cache_path: Path
) -> Tuple[Optional[Dict[str, Any]], bool]:
    if not _model_supports_param(cache_path, model, "response_format"):
        return None, False
    if _model_supports_param(cache_path, model, "structured_outputs"):
        return (
            {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                },
            },
            True,
        )
    return {"type": "json_object"}, False


def _estimate_cost(
    pricing: Dict[str, Any],
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
) -> Optional[float]:
    if prompt_tokens is None or completion_tokens is None:
        return None
    try:
        prompt_rate = float(pricing.get("prompt", 0))
        completion_rate = float(pricing.get("completion", 0))
    except (TypeError, ValueError):
        return None
    # OpenRouter pricing is per token; keep as USD.
    return prompt_tokens * prompt_rate + completion_tokens * completion_rate


def openrouter_chat(
    model: str,
    messages: List[Dict[str, Any]],
    max_tokens: Optional[int],
    temperature: float,
    seed: Optional[int],
    timeout: float,
    pricing_cache: Path,
    response_format: Optional[Dict[str, Any]] = None,
    structured_outputs: bool = False,
    plugins: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, Dict[str, Any]]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set.")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    referer = os.getenv("OPENROUTER_REFERER")
    title = os.getenv("OPENROUTER_TITLE")
    if referer:
        headers["HTTP-Referer"] = referer
    if title:
        headers["X-Title"] = title

    resolved_max_tokens = max_tokens
    if resolved_max_tokens is None:
        limits = _get_model_limits(pricing_cache, model)
        resolved_max_tokens = limits.get("max_completion_tokens")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if resolved_max_tokens is not None:
        payload["max_tokens"] = resolved_max_tokens
    if seed is not None and _model_supports_param(pricing_cache, model, "seed"):
        payload["seed"] = seed
    if response_format is not None and _model_supports_param(pricing_cache, model, "response_format"):
        payload["response_format"] = response_format
    if structured_outputs and _model_supports_param(pricing_cache, model, "structured_outputs"):
        payload["structured_outputs"] = True
    if plugins:
        payload["plugins"] = plugins
    def _post(request_payload: Dict[str, Any]) -> requests.Response:
        return requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=request_payload,
            timeout=timeout,
        )

    def _should_retry_without_format(resp: requests.Response) -> bool:
        if resp.status_code != 400 or (response_format is None and not structured_outputs):
            return False
        try:
            data = resp.json()
        except Exception:
            return False
        err = data.get("error") or {}
        msg = str(err.get("message", ""))
        raw = ""
        meta = err.get("metadata") or {}
        if isinstance(meta, dict):
            raw = str(meta.get("raw", ""))
        text = f"{msg} {raw}".lower()
        return "json mode is not enabled" in text or "response_format" in text or "structured_outputs" in text

    start_time = time.time()
    response = _post(payload)
    duration_sec = time.time() - start_time
    response_format_fallback = False
    if _should_retry_without_format(response):
        payload.pop("response_format", None)
        payload.pop("structured_outputs", None)
        start_time = time.time()
        response = _post(payload)
        duration_sec = time.time() - start_time
        response_format_fallback = True

    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "OpenRouter error."))

    usage = data.get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    model_id = data.get("model") or model

    pricing_data = _get_pricing(pricing_cache)
    pricing = pricing_data.get(model_id, {}).get("pricing", {})
    cost = _estimate_cost(pricing, prompt_tokens, completion_tokens)

    rate_limit = {}
    for key, value in response.headers.items():
        lower = key.lower()
        if lower.startswith("x-ratelimit") or lower.startswith("ratelimit") or lower == "retry-after":
            rate_limit[key] = value

    meta = {
        "model": model_id,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": usage.get("total_tokens"),
        "estimated_cost_usd": cost,
        "max_tokens": resolved_max_tokens,
        "seed": seed,
        "timeout_sec": timeout,
        "duration_sec": round(duration_sec, 3),
        "request_id": response.headers.get("x-request-id"),
    }
    if response_format_fallback:
        meta["response_format_fallback"] = True
    if rate_limit:
        meta["rate_limit"] = rate_limit
    return data["choices"][0]["message"]["content"], meta


def ollama_chat(
    model: str,
    prompt: str,
    image_path: Path,
    temperature: float,
    seed: Optional[int],
    max_output_tokens: Optional[int],
    timeout: float,
    context_length: Optional[int],
) -> Tuple[str, Dict[str, Any]]:
    image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    options: Dict[str, Any] = {"temperature": temperature}
    if seed is not None:
        options["seed"] = seed
    if max_output_tokens is not None:
        options["num_predict"] = max_output_tokens
    if context_length is not None:
        options["num_ctx"] = context_length
    payload = {
        "model": model,
        "stream": False,
        "options": options,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Extract the poster into JSON.", "images": [image_b64]},
        ],
    }
    response = requests.post("http://localhost:11434/api/chat", json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    message = data.get("message", {}).get("content", "")
    prompt_tokens = data.get("prompt_eval_count")
    completion_tokens = data.get("eval_count")
    total_tokens = None
    if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
        total_tokens = prompt_tokens + completion_tokens
    meta = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "total_duration_ns": data.get("total_duration"),
        "load_duration_ns": data.get("load_duration"),
        "prompt_eval_duration_ns": data.get("prompt_eval_duration"),
        "eval_duration_ns": data.get("eval_duration"),
        "num_ctx": context_length,
    }
    return message, meta


def gemini_chat(
    model: str,
    prompt: str,
    image_path: Path,
    temperature: float,
    seed: Optional[int],
    max_output_tokens: Optional[int],
) -> Tuple[str, Dict[str, Any]]:
    if genai is None or types is None:
        raise RuntimeError("google-genai is not available.")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set.")
    client = genai.Client(api_key=api_key)
    mime_type = "image/jpeg"
    uploaded = client.files.upload(
        file=str(image_path),
        config=types.UploadFileConfig(mimeType=mime_type),
    )
    config = types.GenerateContentConfig(
        temperature=temperature,
        seed=seed,
        max_output_tokens=max_output_tokens,
    )
    response = client.models.generate_content(model=model, contents=[uploaded, prompt], config=config)
    text = response.text or ""
    usage = getattr(response, "usage_metadata", None)
    prompt_tokens = None
    completion_tokens = None
    total_tokens = None
    if usage is not None:
        if isinstance(usage, dict):
            prompt_tokens = usage.get("prompt_token_count")
            completion_tokens = usage.get("candidates_token_count")
            total_tokens = usage.get("total_token_count")
        else:
            prompt_tokens = getattr(usage, "prompt_token_count", None)
            completion_tokens = getattr(usage, "candidates_token_count", None)
            total_tokens = getattr(usage, "total_token_count", None)
    meta = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }
    return text, meta


def gemini_text_chat(
    model: str,
    prompt: str,
    text: str,
    temperature: float,
    seed: Optional[int],
    max_output_tokens: Optional[int],
) -> Tuple[str, Dict[str, Any]]:
    if genai is None or types is None:
        raise RuntimeError("google-genai is not available.")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set.")
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        temperature=temperature,
        seed=seed,
        max_output_tokens=max_output_tokens,
    )
    combined = f"{prompt}\n\n{text}"
    response = client.models.generate_content(model=model, contents=[combined], config=config)
    text_out = response.text or ""
    usage = getattr(response, "usage_metadata", None)
    prompt_tokens = None
    completion_tokens = None
    total_tokens = None
    if usage is not None:
        if isinstance(usage, dict):
            prompt_tokens = usage.get("prompt_token_count")
            completion_tokens = usage.get("candidates_token_count")
            total_tokens = usage.get("total_token_count")
        else:
            prompt_tokens = getattr(usage, "prompt_token_count", None)
            completion_tokens = getattr(usage, "candidates_token_count", None)
            total_tokens = getattr(usage, "total_token_count", None)
    meta = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }
    return text_out, meta


def gemini_repair_json(
    model: str,
    prompt: str,
    raw_text: str,
    temperature: float,
    seed: Optional[int],
    max_output_tokens: Optional[int],
) -> Tuple[str, Dict[str, Any]]:
    if genai is None or types is None:
        raise RuntimeError("google-genai is not available.")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set.")
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        temperature=temperature,
        seed=seed,
        max_output_tokens=max_output_tokens,
    )
    repair_prompt = f"{prompt}\n{raw_text}\n"
    response = client.models.generate_content(model=model, contents=[repair_prompt], config=config)
    text = response.text or ""
    usage = getattr(response, "usage_metadata", None)
    prompt_tokens = None
    completion_tokens = None
    total_tokens = None
    if usage is not None:
        if isinstance(usage, dict):
            prompt_tokens = usage.get("prompt_token_count")
            completion_tokens = usage.get("candidates_token_count")
            total_tokens = usage.get("total_token_count")
        else:
            prompt_tokens = getattr(usage, "prompt_token_count", None)
            completion_tokens = getattr(usage, "candidates_token_count", None)
            total_tokens = getattr(usage, "total_token_count", None)
    meta = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }
    return text, meta


def iter_entries(entries: List[Dict[str, Any]], start: int, limit: Optional[int]) -> Iterable[Dict[str, Any]]:
    sliced = entries[start:]
    if limit is not None:
        sliced = sliced[:limit]
    return sliced


def command_download(args: argparse.Namespace) -> None:
    urls = read_lines(Path(args.urls))
    existing = {entry["id"]: entry for entry in load_manifest(Path(args.manifest))}
    entries: List[Dict[str, Any]] = []
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    user_agent = os.getenv("BENCH_USER_AGENT", DEFAULT_USER_AGENT)

    for url in iter_entries([{"url": url} for url in urls], args.start, args.limit):
        source_url = url["url"]
        poster_id = id_for_url(source_url)
        entry = existing.get(poster_id, {"id": poster_id, "url": source_url})
        image_path_str = entry.get("image_path")
        image_path = Path(image_path_str) if image_path_str else None
        if image_path and image_path.exists() and not args.force:
            entries.append(entry)
            continue

        try:
            data, resolved_url, ext = download_image(
                source_url,
                session=session,
                user_agent=user_agent,
                timeout=args.timeout,
            )
            filename = f"{poster_id}{ext}"
            image_path = out_dir / filename
            image_path.write_bytes(data)
            entry.update(
                {
                    "image_path": str(image_path),
                    "resolved_url": resolved_url,
                    "status": "ok",
                    "error": None,
                    "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
            )
        except Exception as exc:
            entry.update(
                {
                    "status": "error",
                    "error": str(exc),
                    "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
            )
        entries.append(entry)
        if args.sleep:
            time.sleep(args.sleep)

    save_manifest(Path(args.manifest), entries)


def command_ocr(args: argparse.Namespace) -> None:
    prompt = read_prompt(Path(args.prompt))
    entries = load_manifest(Path(args.manifest))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    max_output_tokens = _resolve_max_output(args.max_output, kind="gemini", model=args.model)
    tokens_estimate = args.tokens_per_request
    if tokens_estimate is None and (args.rpm or args.tpm):
        tokens_estimate = _estimate_gemini_tokens(max_output_tokens)
    rate_limiter = None
    if args.rpm or args.tpm:
        rate_limiter = RateLimiter(args.rpm, args.tpm, tokens_estimate)

    def _ocr_entry(entry: Dict[str, Any]) -> None:
        if entry.get("status") != "ok":
            return
        poster_id = entry["id"]
        out_path = out_dir / f"{poster_id}.txt"
        if out_path.exists() and not args.force:
            return
        image_path = Path(entry["image_path"])
        if not image_path.exists():
            return
        if rate_limiter:
            rate_limiter.acquire(tokens_estimate)
        try:
            raw_text, model_meta = gemini_chat(
                f"models/{args.model}" if not args.model.startswith("models/") else args.model,
                prompt,
                image_path,
                DEFAULT_TEMPERATURE,
                args.seed,
                max_output_tokens,
            )
        except Exception as exc:
            error_path = out_dir / f"{poster_id}.error.json"
            error_path.write_text(
                json.dumps({"request_error": str(exc), "image_path": str(image_path)}, indent=2),
                encoding="utf-8",
            )
            return
        meta = {
            "model": f"gemini:{args.model}",
            "estimated_cost_usd": 0,
            "seed": args.seed,
            "max_output_tokens": max_output_tokens,
        }
        if model_meta:
            meta.update(model_meta)
        _save_text_with_meta(out_path, raw_text, meta=meta)
        if args.sleep:
            time.sleep(args.sleep)

    with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as executor:
        executor.map(_ocr_entry, iter_entries(entries, args.start, args.limit))


def command_parse_ocr(args: argparse.Namespace) -> None:
    prompt = read_prompt(Path(args.prompt))
    repair_prompt = read_prompt(Path(args.repair_prompt)) if args.repair_json else None
    entries = load_manifest(Path(args.manifest))
    ocr_dir = Path(args.ocr)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_dir = out_dir / safe_name(f"gemini-{args.model}")
    model_dir.mkdir(parents=True, exist_ok=True)
    max_output_tokens = _resolve_max_output(args.max_output, kind="gemini", model=args.model)
    tokens_estimate = args.tokens_per_request
    if tokens_estimate is None and (args.rpm or args.tpm):
        tokens_estimate = _estimate_gemini_tokens(max_output_tokens)
    rate_limiter = None
    if args.rpm or args.tpm:
        rate_limiter = RateLimiter(args.rpm, args.tpm, tokens_estimate)

    def _parse_entry(entry: Dict[str, Any]) -> None:
        if entry.get("status") != "ok":
            return
        poster_id = entry["id"]
        json_path = model_dir / f"{poster_id}.json"
        if json_path.exists() and not args.force:
            return
        ocr_path = ocr_dir / f"{poster_id}.txt"
        if not ocr_path.exists():
            return
        ocr_text = ocr_path.read_text(encoding="utf-8")
        if rate_limiter:
            rate_limiter.acquire(tokens_estimate)
        try:
            raw_text, model_meta = gemini_text_chat(
                f"models/{args.model}" if not args.model.startswith("models/") else args.model,
                prompt,
                ocr_text,
                DEFAULT_TEMPERATURE,
                args.seed,
                max_output_tokens,
            )
        except Exception as exc:
            error_path = model_dir / f"{poster_id}.error.json"
            error_path.write_text(
                json.dumps({"request_error": str(exc), "ocr_path": str(ocr_path)}, indent=2),
                encoding="utf-8",
            )
            return
        meta = {
            "model": f"gemini:{args.model}",
            "estimated_cost_usd": 0,
            "seed": args.seed,
            "max_output_tokens": max_output_tokens,
            "ocr_path": str(ocr_path),
        }
        if model_meta:
            meta.update(model_meta)
        repair_fn = None
        if repair_prompt:
            def _repair(raw: str) -> Tuple[str, Dict[str, Any]]:
                repair_text, repair_meta = gemini_repair_json(
                    f"models/{args.model}" if not args.model.startswith("models/") else args.model,
                    repair_prompt,
                    raw,
                    DEFAULT_TEMPERATURE,
                    args.seed,
                    max_output_tokens,
                )
                meta_out = {
                    "model": f"gemini:{args.model}",
                    "seed": args.seed,
                    "max_output_tokens": max_output_tokens,
                }
                if repair_meta:
                    meta_out.update(repair_meta)
                return repair_text, meta_out
            repair_fn = _repair
        _save_raw_and_json_with_repair(model_dir, poster_id, raw_text, meta=meta, repair_fn=repair_fn)
        if args.sleep:
            time.sleep(args.sleep)

    with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as executor:
        executor.map(_parse_entry, iter_entries(entries, args.start, args.limit))


def command_fill_locations(args: argparse.Namespace) -> None:
    prompt = read_prompt(Path(args.prompt))
    entries = load_manifest(Path(args.manifest))
    pred_root = Path(args.predictions)
    ocr_dir = Path(args.ocr)
    if args.model_dir:
        model_dirs = [Path(args.model_dir)]
    else:
        model_dirs = [p for p in sorted(pred_root.iterdir()) if p.is_dir()]
    if not model_dirs:
        return
    max_output_tokens = _resolve_max_output(args.max_output, kind="gemini", model=args.model)
    tokens_estimate = args.tokens_per_request
    if tokens_estimate is None and (args.rpm or args.tpm):
        tokens_estimate = _estimate_gemini_tokens(max_output_tokens)
    rate_limiter = None
    if args.rpm or args.tpm:
        rate_limiter = RateLimiter(args.rpm, args.tpm, tokens_estimate)

    def _fill_entry(entry: Dict[str, Any], model_dir: Path) -> None:
        if entry.get("status") != "ok":
            return
        poster_id = entry["id"]
        json_path = model_dir / f"{poster_id}.json"
        if not json_path.exists():
            return
        error_path = model_dir / f"{poster_id}.locfill.error.json"
        if args.retry_errors and not error_path.exists():
            return
        pred = _load_json(json_path)
        if not args.force and not _needs_location_fill(pred):
            if error_path.exists():
                error_path.unlink()
            return
        ocr_path = ocr_dir / f"{poster_id}.txt"
        if not ocr_path.exists():
            return
        ocr_text = ocr_path.read_text(encoding="utf-8")
        if rate_limiter:
            rate_limiter.acquire(tokens_estimate)
        try:
            existing_json = json.dumps(pred, ensure_ascii=False, indent=2)
            loc_prompt = f"{prompt}\n{existing_json}\n"
            raw_text, model_meta = gemini_text_chat(
                f"models/{args.model}" if not args.model.startswith("models/") else args.model,
                loc_prompt,
                ocr_text,
                DEFAULT_TEMPERATURE,
                args.seed,
                max_output_tokens,
            )
        except Exception as exc:
            error_path.write_text(
                json.dumps({"locfill_error": str(exc), "ocr_path": str(ocr_path)}, indent=2),
                encoding="utf-8",
            )
            return

        loc_raw_path = model_dir / f"{poster_id}.locfill.raw.txt"
        loc_raw_path.write_text(raw_text, encoding="utf-8")
        if model_meta:
            loc_meta_path = model_dir / f"{poster_id}.locfill.meta.json"
            meta_out = {
                "model": f"gemini:{args.model}",
                "seed": args.seed,
                "max_output_tokens": max_output_tokens,
                "ocr_path": str(ocr_path),
            }
            meta_out.update(model_meta)
            loc_meta_path.write_text(json.dumps(meta_out, ensure_ascii=False, indent=2), encoding="utf-8")

        parsed = extract_json(raw_text)
        if not isinstance(parsed, dict) or not _schema_valid(parsed, strict=True):
            error_payload: Dict[str, Any] = {"locfill_raw_path": str(loc_raw_path)}
            if parsed is None:
                error_payload["locfill_parse_error"] = "invalid_json"
            else:
                error_payload["locfill_schema_error"] = "strict_schema_invalid"
            error_path.write_text(json.dumps(error_payload, indent=2), encoding="utf-8")
            return

        pred_events = pred.get("events") if isinstance(pred, dict) else None
        new_events = parsed.get("events")
        if not isinstance(pred_events, list) or not isinstance(new_events, list) or len(pred_events) != len(new_events):
            error_path.write_text(
                json.dumps({"locfill_error": "event_count_mismatch", "locfill_raw_path": str(loc_raw_path)}, indent=2),
                encoding="utf-8",
            )
            return

        updated = False
        for old_event, new_event in zip(pred_events, new_events):
            if not isinstance(old_event, dict) or not isinstance(new_event, dict):
                continue
            for field in ("venue", "city", "province", "country"):
                if _is_blank(old_event.get(field)) and not _is_blank(new_event.get(field)):
                    old_event[field] = new_event.get(field)
                    updated = True
        if updated:
            json_path.write_text(json.dumps(pred, ensure_ascii=False, indent=2), encoding="utf-8")
        if error_path.exists():
            error_path.unlink()

    for model_dir in model_dirs:
        if not model_dir.exists():
            continue
        with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as executor:
            executor.map(
                lambda entry: _fill_entry(entry, model_dir),
                iter_entries(entries, args.start, args.limit),
            )


def _save_raw_and_json(
    out_dir: Path, poster_id: str, raw_text: str, meta: Optional[Dict[str, Any]] = None
) -> Tuple[Path, Optional[Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"{poster_id}.raw.txt"
    raw_path.write_text(raw_text, encoding="utf-8")
    if meta:
        meta_path = out_dir / f"{poster_id}.meta.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    error_path = out_dir / f"{poster_id}.error.json"
    parsed = extract_json(raw_text)
    if parsed is None:
        error_path.write_text(
            json.dumps({"parse_error": "invalid_json", "raw_path": str(raw_path)}, indent=2),
            encoding="utf-8",
        )
        return raw_path, None
    json_path = out_dir / f"{poster_id}.json"
    json_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    if error_path.exists():
        error_path.unlink()
    return raw_path, parsed


def _save_raw_and_json_with_repair(
    out_dir: Path,
    poster_id: str,
    raw_text: str,
    meta: Optional[Dict[str, Any]] = None,
    repair_fn: Optional[Callable[[str], Tuple[str, Dict[str, Any]]]] = None,
) -> Tuple[Path, Optional[Any]]:
    raw_path, parsed = _save_raw_and_json(out_dir, poster_id, raw_text, meta=meta)
    if repair_fn is None:
        return raw_path, parsed
    if parsed is not None and _schema_valid(parsed, strict=True):
        return raw_path, parsed

    try:
        repair_text, repair_meta = repair_fn(raw_text)
    except Exception as exc:
        repair_error_path = out_dir / f"{poster_id}.repair.error.json"
        repair_error_path.write_text(
            json.dumps({"repair_error": str(exc), "raw_path": str(raw_path)}, indent=2),
            encoding="utf-8",
        )
        return raw_path, parsed

    repair_raw_path = out_dir / f"{poster_id}.repair.raw.txt"
    repair_raw_path.write_text(repair_text, encoding="utf-8")
    if repair_meta:
        repair_meta_path = out_dir / f"{poster_id}.repair.meta.json"
        repair_meta_path.write_text(json.dumps(repair_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    repaired = extract_json(repair_text)
    if repaired is not None and _schema_valid(repaired, strict=True):
        json_path = out_dir / f"{poster_id}.json"
        json_path.write_text(json.dumps(repaired, ensure_ascii=False, indent=2), encoding="utf-8")
        error_path = out_dir / f"{poster_id}.error.json"
        if error_path.exists():
            error_path.unlink()
        return raw_path, repaired

    error_payload: Dict[str, Any] = {"raw_path": str(raw_path), "repair_raw_path": str(repair_raw_path)}
    if parsed is None:
        error_payload["parse_error"] = "invalid_json"
    if repaired is None:
        error_payload["repair_parse_error"] = "invalid_json"
    else:
        error_payload["repair_schema_error"] = "strict_schema_invalid"
    error_path = out_dir / f"{poster_id}.error.json"
    error_path.write_text(json.dumps(error_payload, indent=2), encoding="utf-8")
    return raw_path, parsed


def _save_text_with_meta(out_path: Path, text: str, meta: Optional[Dict[str, Any]] = None) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    if meta:
        meta_path = out_path.with_suffix(".meta.json")
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _needs_refine(pred: Any) -> bool:
    if not isinstance(pred, dict):
        return True
    if _is_blank(pred.get("artist_name")) or _is_blank(pred.get("source_month")):
        return True
    events = pred.get("events") or []
    if not isinstance(events, list):
        return True
    for event in events:
        if not isinstance(event, dict):
            return True
        for field in ("venue", "city", "province"):
            if _is_blank(event.get(field)):
                return True
    return False


def _normalize_locations(pred: Any) -> bool:
    if not isinstance(pred, dict):
        return False
    events = pred.get("events") or []
    if not isinstance(events, list):
        return False
    changed = False
    for event in events:
        if not isinstance(event, dict):
            continue
        if _is_blank(event.get("venue")):
            name = event.get("event_name")
            left, right = _split_event_name_for_venue(name)
            if right:
                event["venue"] = right
                if left is not None:
                    event["event_name"] = left
                changed = True
            elif _looks_like_venue(name):
                event["venue"] = name
                changed = True
        province = event.get("province")
        city = event.get("city")
        filled_province = False
        if _is_blank(province):
            match = None
            if isinstance(city, str):
                match = _find_province_in_text(city)
            if match is None:
                for field in ("venue", "event_name", "ticket_info"):
                    match = _find_province_in_text(event.get(field))
                    if match:
                        break
            if match:
                event["province"] = match
                filled_province = True
                changed = True
        if filled_province and _is_blank(event.get("city")):
            event["city"] = event.get("province")
            changed = True
    return changed


def _format_time(hour: int, minute: int) -> Optional[str]:
    if 0 <= hour < 24 and 0 <= minute < 60:
        return f"{hour:02d}:{minute:02d}"
    return None


def _parse_time_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    range_match = re.search(r"(\\d{1,2})[.:](\\d{2})\\s*[-–~]\\s*(\\d{1,2})[.:](\\d{2})", text)
    if range_match:
        hour = int(range_match.group(1))
        minute = int(range_match.group(2))
        return _format_time(hour, minute)
    match = re.search(r"(\\d{1,2})[.:](\\d{2})", text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        return _format_time(hour, minute)
    return None


def _normalize_times(pred: Any) -> bool:
    if not isinstance(pred, dict):
        return False
    events = pred.get("events") or []
    if not isinstance(events, list):
        return False
    changed = False
    for event in events:
        if not isinstance(event, dict):
            continue
        time_value = event.get("time")
        normalized = None
        if isinstance(time_value, str):
            raw = time_value.strip()
            if raw and not re.match(r"^\\d{2}:\\d{2}$", raw):
                normalized = _parse_time_from_text(raw)
            elif raw and re.match(r"^\\d{2}:\\d{2}$", raw):
                normalized = None
        if normalized is None and _is_blank(time_value):
            ticket_info = event.get("ticket_info")
            if isinstance(ticket_info, str):
                normalized = _parse_time_from_text(ticket_info)
        if normalized and normalized != time_value:
            event["time"] = normalized
            changed = True
    return changed


def _needs_location_fill(pred: Any) -> bool:
    if not isinstance(pred, dict):
        return False
    events = pred.get("events") or []
    if not isinstance(events, list):
        return False
    for event in events:
        if not isinstance(event, dict):
            continue
        for field in ("venue", "city", "province"):
            if _is_blank(event.get(field)):
                return True
    return False


def _compact_judge_payload(data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    events = data.get("events") or []
    if not isinstance(events, list):
        return {"events": []}
    compact_events = []
    for event in events:
        if not isinstance(event, dict):
            continue
        compact_events.append(
            {
                "date": event.get("date"),
                "venue": event.get("venue"),
                "city": event.get("city"),
                "province": event.get("province"),
            }
        )
    return {"events": compact_events}


def command_ground_truth(args: argparse.Namespace) -> None:
    prompt = read_prompt(Path(args.prompt))
    entries = load_manifest(Path(args.manifest))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for entry in iter_entries(entries, args.start, args.limit):
        if entry.get("status") != "ok":
            continue
        poster_id = entry["id"]
        json_path = out_dir / f"{poster_id}.json"
        error_path = out_dir / f"{poster_id}.error.json"
        if args.retry_errors and not error_path.exists():
            continue
        if json_path.exists() and not args.force:
            continue
        image_path = Path(entry["image_path"])
        if not image_path.exists():
            continue

        image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                ],
            }
        ]
        max_tokens = _resolve_max_output(args.max_output)
        try:
            response_format, structured_outputs = _openrouter_response_format(
                args.model, POSTER_SCHEMA_NAME, POSTER_SCHEMA, Path("benchmark/cache/openrouter_models.json")
            )
            raw_text, meta = openrouter_chat(
                model=args.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=DEFAULT_TEMPERATURE,
                seed=args.seed,
                timeout=args.timeout,
                pricing_cache=Path("benchmark/cache/openrouter_models.json"),
                response_format=response_format,
                structured_outputs=structured_outputs,
            )
            _save_raw_and_json(out_dir, poster_id, raw_text, meta=meta)
        except Exception as exc:
            error_path = out_dir / f"{poster_id}.error.json"
            error_path.write_text(
                json.dumps({"request_error": str(exc), "image_path": str(image_path)}, indent=2),
                encoding="utf-8",
            )
        if args.sleep:
            time.sleep(args.sleep)


def _parse_model_spec(spec: str) -> Tuple[str, str]:
    if ":" not in spec:
        raise ValueError(f"Model spec must be kind:name (got {spec})")
    kind, name = spec.split(":", 1)
    return kind, name


def command_predict(args: argparse.Namespace) -> None:
    prompt = read_prompt(Path(args.prompt))
    repair_prompt = read_prompt(Path(args.repair_prompt)) if args.repair_json else None
    entries = load_manifest(Path(args.manifest))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_specs = [_parse_model_spec(spec) for spec in args.models]
    plugins = _load_plugins_config(args.openrouter_plugins)

    for kind, name in model_specs:
        model_dir = out_dir / safe_name(f"{kind}-{name}")
        model_dir.mkdir(parents=True, exist_ok=True)
        if kind == "gemini" and (args.parallel > 1 or args.rpm or args.tpm):
            max_output_tokens = _resolve_max_output(args.max_output, kind=kind, model=name)
            tokens_estimate = args.tokens_per_request
            if tokens_estimate is None and (args.rpm or args.tpm):
                tokens_estimate = _estimate_gemini_tokens(max_output_tokens)
            rate_limiter = None
            if args.rpm or args.tpm:
                rate_limiter = RateLimiter(args.rpm, args.tpm, tokens_estimate)

            def _predict_gemini_entry(entry: Dict[str, Any]) -> None:
                if entry.get("status") != "ok":
                    return
                poster_id = entry["id"]
                json_path = model_dir / f"{poster_id}.json"
                if json_path.exists() and not args.force:
                    return
                image_path = Path(entry["image_path"])
                if not image_path.exists():
                    return
                if rate_limiter:
                    rate_limiter.acquire(tokens_estimate)
                try:
                    raw_text, model_meta = gemini_chat(
                        f"models/{name}" if not name.startswith("models/") else name,
                        prompt,
                        image_path,
                        DEFAULT_TEMPERATURE,
                        args.seed,
                        max_output_tokens,
                    )
                    meta = {
                        "model": f"gemini:{name}",
                        "estimated_cost_usd": 0,
                        "seed": args.seed,
                        "max_output_tokens": max_output_tokens,
                    }
                    if model_meta:
                        meta.update(model_meta)
                    repair_fn = None
                    if repair_prompt:
                        def _repair(raw: str) -> Tuple[str, Dict[str, Any]]:
                            repair_text, repair_meta = gemini_repair_json(
                                f"models/{name}" if not name.startswith("models/") else name,
                                repair_prompt,
                                raw,
                                DEFAULT_TEMPERATURE,
                                args.seed,
                                max_output_tokens,
                            )
                            meta_out = {
                                "model": f"gemini:{name}",
                                "seed": args.seed,
                                "max_output_tokens": max_output_tokens,
                            }
                            if repair_meta:
                                meta_out.update(repair_meta)
                            return repair_text, meta_out
                        repair_fn = _repair
                    _save_raw_and_json_with_repair(model_dir, poster_id, raw_text, meta=meta, repair_fn=repair_fn)
                except Exception as exc:
                    error_path = model_dir / f"{poster_id}.error.json"
                    error_path.write_text(
                        json.dumps({"request_error": str(exc), "image_path": str(image_path)}, indent=2),
                        encoding="utf-8",
                    )
                if args.sleep:
                    time.sleep(args.sleep)

            with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as executor:
                list(executor.map(_predict_gemini_entry, iter_entries(entries, args.start, args.limit)))
            continue
        for entry in iter_entries(entries, args.start, args.limit):
            if entry.get("status") != "ok":
                continue
            poster_id = entry["id"]
            json_path = model_dir / f"{poster_id}.json"
            if json_path.exists() and not args.force:
                continue
            image_path = Path(entry["image_path"])
            if not image_path.exists():
                continue

            try:
                repair_fn = None
                if kind == "ollama":
                    max_output_tokens = _resolve_max_output(
                        args.max_output,
                        kind=kind,
                        model=name,
                        context_override=args.ollama_context,
                    )
                    raw_text, model_meta = ollama_chat(
                        name,
                        prompt,
                        image_path,
                        DEFAULT_TEMPERATURE,
                        args.seed,
                        max_output_tokens,
                        args.ollama_timeout,
                        args.ollama_context,
                    )
                    meta = {
                        "model": f"ollama:{name}",
                        "estimated_cost_usd": 0,
                        "seed": args.seed,
                        "max_output_tokens": max_output_tokens,
                        "timeout_sec": args.ollama_timeout,
                        "num_ctx": args.ollama_context,
                    }
                    if model_meta:
                        meta.update(model_meta)
                elif kind == "openrouter":
                    max_output_tokens = _resolve_max_output(args.max_output, kind=kind, model=name)
                    image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                                },
                            ],
                        }
                    ]
                    response_format, structured_outputs = _openrouter_response_format(
                        name, POSTER_SCHEMA_NAME, POSTER_SCHEMA, Path("benchmark/cache/openrouter_models.json")
                    )
                    raw_text, model_meta = openrouter_chat(
                        model=name,
                        messages=messages,
                        max_tokens=max_output_tokens,
                        temperature=DEFAULT_TEMPERATURE,
                        seed=args.seed,
                        timeout=args.timeout,
                        pricing_cache=Path("benchmark/cache/openrouter_models.json"),
                        response_format=response_format,
                        structured_outputs=structured_outputs,
                        plugins=plugins,
                    )
                    meta = {
                        "requested_model": f"openrouter:{name}",
                        "seed": args.seed,
                        "max_output_tokens": max_output_tokens,
                        "timeout_sec": args.timeout,
                    }
                    if model_meta:
                        meta.update(model_meta)
                elif kind == "gemini":
                    max_output_tokens = _resolve_max_output(args.max_output, kind=kind, model=name)
                    raw_text, model_meta = gemini_chat(
                        f"models/{name}" if not name.startswith("models/") else name,
                        prompt,
                        image_path,
                        DEFAULT_TEMPERATURE,
                        args.seed,
                        max_output_tokens,
                    )
                    meta = {
                        "model": f"gemini:{name}",
                        "estimated_cost_usd": 0,
                        "seed": args.seed,
                        "max_output_tokens": max_output_tokens,
                    }
                    if model_meta:
                        meta.update(model_meta)
                    if repair_prompt:
                        def _repair(raw: str) -> Tuple[str, Dict[str, Any]]:
                            repair_text, repair_meta = gemini_repair_json(
                                f"models/{name}" if not name.startswith("models/") else name,
                                repair_prompt,
                                raw,
                                DEFAULT_TEMPERATURE,
                                args.seed,
                                max_output_tokens,
                            )
                            meta_out = {
                                "model": f"gemini:{name}",
                                "seed": args.seed,
                                "max_output_tokens": max_output_tokens,
                            }
                            if repair_meta:
                                meta_out.update(repair_meta)
                            return repair_text, meta_out
                        repair_fn = _repair
                else:
                    raise ValueError(f"Unknown model kind: {kind}")
                _save_raw_and_json_with_repair(model_dir, poster_id, raw_text, meta=meta, repair_fn=repair_fn)
            except Exception as exc:
                error_path = model_dir / f"{poster_id}.error.json"
                error_path.write_text(
                    json.dumps({"request_error": str(exc), "image_path": str(image_path)}, indent=2),
                    encoding="utf-8",
                )
            if args.sleep:
                time.sleep(args.sleep)


def command_repair(args: argparse.Namespace) -> None:
    prompt = read_prompt(Path(args.prompt))
    entries = load_manifest(Path(args.manifest))
    pred_root = Path(args.predictions)
    if args.model_dir:
        model_dirs = [Path(args.model_dir)]
    else:
        model_dirs = [p for p in sorted(pred_root.iterdir()) if p.is_dir()]
    if not model_dirs:
        return
    max_output_tokens = _resolve_max_output(args.max_output, kind="gemini", model=args.model)
    tokens_estimate = args.tokens_per_request
    if tokens_estimate is None and (args.rpm or args.tpm):
        tokens_estimate = _estimate_gemini_tokens(max_output_tokens)
    rate_limiter = None
    if args.rpm or args.tpm:
        rate_limiter = RateLimiter(args.rpm, args.tpm, tokens_estimate)

    def _repair_entry(model_dir: Path, entry: Dict[str, Any]) -> None:
        if entry.get("status") != "ok":
            return
        poster_id = entry["id"]
        raw_path = model_dir / f"{poster_id}.raw.txt"
        if not raw_path.exists():
            return
        json_path = model_dir / f"{poster_id}.json"
        error_path = model_dir / f"{poster_id}.error.json"
        if json_path.exists() and not args.force:
            pred = _load_json(json_path)
            if isinstance(pred, dict) and _schema_valid(pred, strict=True):
                if error_path.exists():
                    error_path.unlink()
                return

        raw_text = raw_path.read_text(encoding="utf-8")
        parsed = extract_json(raw_text)
        if parsed is not None and _schema_valid(parsed, strict=True) and not args.force:
            json_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
            if error_path.exists():
                error_path.unlink()
            return

        if rate_limiter:
            rate_limiter.acquire(tokens_estimate)
        try:
            repair_text, repair_meta = gemini_repair_json(
                f"models/{args.model}" if not args.model.startswith("models/") else args.model,
                prompt,
                raw_text,
                DEFAULT_TEMPERATURE,
                args.seed,
                max_output_tokens,
            )
        except Exception as exc:
            error_path.write_text(
                json.dumps({"repair_error": str(exc), "raw_path": str(raw_path)}, indent=2),
                encoding="utf-8",
            )
            return

        repair_raw_path = model_dir / f"{poster_id}.repair.raw.txt"
        repair_raw_path.write_text(repair_text, encoding="utf-8")
        if repair_meta:
            repair_meta_path = model_dir / f"{poster_id}.repair.meta.json"
            meta_out = {
                "model": f"gemini:{args.model}",
                "seed": args.seed,
                "max_output_tokens": max_output_tokens,
            }
            meta_out.update(repair_meta)
            repair_meta_path.write_text(json.dumps(meta_out, ensure_ascii=False, indent=2), encoding="utf-8")

        repaired = extract_json(repair_text)
        if repaired is not None and _schema_valid(repaired, strict=True):
            json_path.write_text(json.dumps(repaired, ensure_ascii=False, indent=2), encoding="utf-8")
            if error_path.exists():
                error_path.unlink()
        else:
            error_payload: Dict[str, Any] = {
                "raw_path": str(raw_path),
                "repair_raw_path": str(repair_raw_path),
            }
            if repaired is None:
                error_payload["repair_parse_error"] = "invalid_json"
            else:
                error_payload["repair_schema_error"] = "strict_schema_invalid"
            error_path.write_text(json.dumps(error_payload, indent=2), encoding="utf-8")
        if args.sleep:
            time.sleep(args.sleep)

    for model_dir in model_dirs:
        if not model_dir.exists():
            continue
        with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as executor:
            executor.map(
                lambda entry: _repair_entry(model_dir, entry),
                iter_entries(entries, args.start, args.limit),
            )


def command_refine(args: argparse.Namespace) -> None:
    prompt = read_prompt(Path(args.prompt))
    entries = load_manifest(Path(args.manifest))
    pred_root = Path(args.predictions)
    if args.model_dir:
        model_dirs = [Path(args.model_dir)]
    else:
        model_dirs = [p for p in sorted(pred_root.iterdir()) if p.is_dir()]
    if not model_dirs:
        return
    max_output_tokens = _resolve_max_output(args.max_output, kind="gemini", model=args.model)
    tokens_estimate = args.tokens_per_request
    if tokens_estimate is None and (args.rpm or args.tpm):
        tokens_estimate = _estimate_gemini_tokens(max_output_tokens)
    rate_limiter = None
    if args.rpm or args.tpm:
        rate_limiter = RateLimiter(args.rpm, args.tpm, tokens_estimate)

    def _refine_entry(model_dir: Path, entry: Dict[str, Any]) -> None:
        if entry.get("status") != "ok":
            return
        poster_id = entry["id"]
        image_path = Path(entry["image_path"])
        if not image_path.exists():
            return
        json_path = model_dir / f"{poster_id}.json"
        if not json_path.exists():
            return
        error_path = model_dir / f"{poster_id}.refine.error.json"
        if args.retry_errors and not error_path.exists():
            return
        pred = _load_json(json_path)
        if not args.force and not _needs_refine(pred):
            if error_path.exists():
                error_path.unlink()
            return
        if rate_limiter:
            rate_limiter.acquire(tokens_estimate)
        try:
            existing_json = json.dumps(pred, ensure_ascii=False, indent=2)
            refine_prompt = f"{prompt}\n{existing_json}\n"
            raw_text, model_meta = gemini_chat(
                f"models/{args.model}" if not args.model.startswith("models/") else args.model,
                refine_prompt,
                image_path,
                DEFAULT_TEMPERATURE,
                args.seed,
                max_output_tokens,
            )
        except Exception as exc:
            error_path = model_dir / f"{poster_id}.refine.error.json"
            error_path.write_text(
                json.dumps({"refine_error": str(exc), "image_path": str(image_path)}, indent=2),
                encoding="utf-8",
            )
            return

        refine_raw_path = model_dir / f"{poster_id}.refine.raw.txt"
        refine_raw_path.write_text(raw_text, encoding="utf-8")
        if model_meta:
            refine_meta_path = model_dir / f"{poster_id}.refine.meta.json"
            meta_out = {
                "model": f"gemini:{args.model}",
                "seed": args.seed,
                "max_output_tokens": max_output_tokens,
            }
            meta_out.update(model_meta)
            refine_meta_path.write_text(json.dumps(meta_out, ensure_ascii=False, indent=2), encoding="utf-8")

        parsed = extract_json(raw_text)
        if parsed is not None and _schema_valid(parsed, strict=True):
            json_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
            if error_path.exists():
                error_path.unlink()
        else:
            error_payload: Dict[str, Any] = {"refine_raw_path": str(refine_raw_path)}
            if parsed is None:
                error_payload["refine_parse_error"] = "invalid_json"
            else:
                error_payload["refine_schema_error"] = "strict_schema_invalid"
            error_path.write_text(json.dumps(error_payload, indent=2), encoding="utf-8")
        if args.sleep:
            time.sleep(args.sleep)

    for model_dir in model_dirs:
        if not model_dir.exists():
            continue
        with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as executor:
            executor.map(
                lambda entry: _refine_entry(model_dir, entry),
                iter_entries(entries, args.start, args.limit),
            )


def command_normalize(args: argparse.Namespace) -> None:
    entries = load_manifest(Path(args.manifest))
    pred_root = Path(args.predictions)
    if args.model_dir:
        model_dirs = [Path(args.model_dir)]
    else:
        model_dirs = [p for p in sorted(pred_root.iterdir()) if p.is_dir()]
    if not model_dirs:
        return
    for model_dir in model_dirs:
        if not model_dir.exists():
            continue
        for entry in iter_entries(entries, args.start, args.limit):
            if entry.get("status") != "ok":
                continue
            poster_id = entry["id"]
            json_path = model_dir / f"{poster_id}.json"
            if not json_path.exists():
                continue
            pred = _load_json(json_path)
            if not isinstance(pred, dict):
                continue
            changed = _normalize_locations(pred)
            if changed or args.force:
                json_path.write_text(json.dumps(pred, ensure_ascii=False, indent=2), encoding="utf-8")


def command_normalize_time(args: argparse.Namespace) -> None:
    entries = load_manifest(Path(args.manifest))
    pred_root = Path(args.predictions)
    if args.model_dir:
        model_dirs = [Path(args.model_dir)]
    else:
        model_dirs = [p for p in sorted(pred_root.iterdir()) if p.is_dir()]
    if not model_dirs:
        return
    for model_dir in model_dirs:
        if not model_dir.exists():
            continue
        for entry in iter_entries(entries, args.start, args.limit):
            if entry.get("status") != "ok":
                continue
            poster_id = entry["id"]
            json_path = model_dir / f"{poster_id}.json"
            if not json_path.exists():
                continue
            pred = _load_json(json_path)
            if not isinstance(pred, dict):
                continue
            changed = _normalize_times(pred)
            if changed or args.force:
                json_path.write_text(json.dumps(pred, ensure_ascii=False, indent=2), encoding="utf-8")


def command_judge(args: argparse.Namespace) -> None:
    prompt = read_prompt(Path(args.prompt))
    entries = load_manifest(Path(args.manifest))
    gt_dir = Path(args.ground_truth)
    pred_root = Path(args.predictions)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for model_dir in sorted(pred_root.iterdir()):
        if not model_dir.is_dir():
            continue
        model_out = out_dir / model_dir.name
        model_out.mkdir(parents=True, exist_ok=True)
        for entry in iter_entries(entries, args.start, args.limit):
            if entry.get("status") != "ok":
                continue
            poster_id = entry["id"]
            out_path = model_out / f"{poster_id}.json"
            if out_path.exists() and not args.force:
                continue

            gt_path = gt_dir / f"{poster_id}.json"
            pred_path = model_dir / f"{poster_id}.json"
            if not gt_path.exists() or not pred_path.exists():
                continue

            gt_text = gt_path.read_text(encoding="utf-8")
            pred_text = pred_path.read_text(encoding="utf-8")
            if args.compact:
                try:
                    gt_data = json.loads(gt_text)
                except Exception:
                    gt_data = None
                if gt_data is not None:
                    gt_text = json.dumps(
                        _compact_judge_payload(gt_data),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                try:
                    pred_data = json.loads(pred_text)
                except Exception:
                    pred_data = None
                if pred_data is not None:
                    pred_text = json.dumps(
                        _compact_judge_payload(pred_data),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
            judge_prompt = (
                f"{prompt}\n\nGround truth JSON:\n{gt_text}\n\nPrediction JSON:\n{pred_text}\n"
            )
            messages = [{"role": "user", "content": judge_prompt}]
            max_tokens = _resolve_max_output(args.max_output)
            try:
                response_format, structured_outputs = _openrouter_response_format(
                    args.model, JUDGE_SCHEMA_NAME, JUDGE_SCHEMA, Path("benchmark/cache/openrouter_models.json")
                )
                raw_text, meta = openrouter_chat(
                    model=args.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=DEFAULT_TEMPERATURE,
                    seed=args.seed,
                    timeout=args.timeout,
                    pricing_cache=Path("benchmark/cache/openrouter_models.json"),
                    response_format=response_format,
                    structured_outputs=structured_outputs,
                )
                _save_raw_and_json(model_out, poster_id, raw_text, meta=meta)
            except Exception as exc:
                error_path = model_out / f"{poster_id}.error.json"
                error_path.write_text(
                    json.dumps(
                        {"request_error": str(exc), "ground_truth": str(gt_path), "prediction": str(pred_path)},
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            if args.sleep:
                time.sleep(args.sleep)


def _load_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_meta(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _date_metrics(gold: Any, pred: Any) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if not isinstance(gold, dict) or not isinstance(pred, dict):
        return None, None, None
    gold_events = gold.get("events") or []
    pred_events = pred.get("events") or []
    gold_dates = [e.get("date") for e in gold_events if isinstance(e, dict)]
    pred_dates = [e.get("date") for e in pred_events if isinstance(e, dict)]
    gold_dates = [d for d in gold_dates if isinstance(d, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", d)]
    pred_dates = [d for d in pred_dates if isinstance(d, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", d)]
    if not gold_dates and not pred_dates:
        return None, None, None
    gold_counter = Counter(gold_dates)
    pred_counter = Counter(pred_dates)
    matches = sum((gold_counter & pred_counter).values())
    precision = matches / len(pred_dates) if pred_dates else 0.0
    recall = matches / len(gold_dates) if gold_dates else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def _schema_valid(data: Any, strict: bool = False) -> bool:
    if not isinstance(data, dict):
        return False
    required_keys = {
        "artist_name",
        "instagram_handle",
        "tour_name",
        "contact_info",
        "source_month",
        "poster_confidence",
        "events",
    }
    data_keys = set(data.keys())
    if strict:
        if data_keys != required_keys:
            return False
    else:
        if not required_keys.issubset(data_keys):
            return False

    artist_name = data.get("artist_name")
    if not isinstance(artist_name, str):
        return False
    for key in ("instagram_handle", "tour_name", "contact_info"):
        value = data.get(key)
        if value is not None and not isinstance(value, str):
            return False
    source_month = data.get("source_month")
    if not isinstance(source_month, str) or not re.match(r"^\d{4}-\d{2}$", source_month):
        return False
    if not isinstance(data.get("events"), list):
        return False
    poster_conf = data.get("poster_confidence")
    if poster_conf is not None:
        if not isinstance(poster_conf, (int, float)):
            return False
        if poster_conf < 0 or poster_conf > 1:
            return False

    status_values = {"active", "cancelled", "postponed"}
    for event in data["events"]:
        if not isinstance(event, dict):
            return False
        event_keys = {
            "date",
            "event_name",
            "venue",
            "city",
            "province",
            "country",
            "time",
            "ticket_info",
            "status",
            "confidence",
        }
        event_key_set = set(event.keys())
        if strict:
            if event_key_set != event_keys:
                return False
        else:
            if not event_keys.issubset(event_key_set):
                return False
        date = event.get("date")
        if not isinstance(date, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
            return False
        country = event.get("country")
        if not isinstance(country, str):
            return False
        status = event.get("status")
        if not isinstance(status, str) or status not in status_values:
            return False
        time_value = event.get("time")
        if time_value is not None:
            if not isinstance(time_value, str) or not re.match(r"^\d{2}:\d{2}$", time_value):
                return False
        for key in ("event_name", "venue", "city", "province", "ticket_info"):
            value = event.get(key)
            if value is not None and not isinstance(value, str):
                return False
        confidence = event.get("confidence")
        if confidence is not None:
            if not isinstance(confidence, (int, float)):
                return False
            if confidence < 0 or confidence > 1:
                return False
    return True


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = value.strip().lower()
    value = re.sub(r"\\s+", " ", value)
    return value


def _normalize_handle(value: Any) -> str:
    text = _normalize_text(value)
    if text.startswith("@"):
        text = text[1:]
    return text


def _string_score(gold: Any, pred: Any) -> float:
    gold_norm = _normalize_text(gold)
    pred_norm = _normalize_text(pred)
    if not gold_norm and not pred_norm:
        return 1.0
    if not gold_norm or not pred_norm:
        return 0.0
    if gold_norm == pred_norm:
        return 1.0
    return SequenceMatcher(None, gold_norm, pred_norm).ratio()


def _exact_score(gold: Any, pred: Any) -> float:
    gold_norm = _normalize_text(gold)
    pred_norm = _normalize_text(pred)
    if not gold_norm and not pred_norm:
        return 1.0
    if not gold_norm or not pred_norm:
        return 0.0
    return 1.0 if gold_norm == pred_norm else 0.0


def _event_list(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("events"), list):
        return [event for event in data["events"] if isinstance(event, dict)]
    return []


def _event_count_score(gold_events: List[Dict[str, Any]], pred_events: List[Dict[str, Any]]) -> float:
    gold_count = len(gold_events)
    pred_count = len(pred_events)
    if gold_count == 0 and pred_count == 0:
        return 1.0
    denom = max(gold_count, pred_count, 1)
    return max(0.0, 1.0 - abs(gold_count - pred_count) / denom)


def _score_top_level(gold: Any, pred: Any) -> float:
    if not isinstance(gold, dict) or not isinstance(pred, dict):
        return 0.0
    total = 0.0
    weight_sum = 0.0
    for field, weight in TOP_LEVEL_WEIGHTS.items():
        if field == "instagram_handle":
            score = _exact_score(_normalize_handle(gold.get(field)), _normalize_handle(pred.get(field)))
        elif field == "source_month":
            score = _exact_score(gold.get(field), pred.get(field))
        else:
            score = _string_score(gold.get(field), pred.get(field))
        total += weight * score
        weight_sum += weight
    return total / weight_sum if weight_sum else 0.0


def _location_score(gold_event: Dict[str, Any], pred_event: Dict[str, Any]) -> float:
    city = _string_score(gold_event.get("city"), pred_event.get("city"))
    province = _string_score(gold_event.get("province"), pred_event.get("province"))
    country = _exact_score(gold_event.get("country"), pred_event.get("country"))
    return (city + province + country) / 3.0


def _event_similarity(gold_event: Dict[str, Any], pred_event: Dict[str, Any]) -> float:
    scores = {
        "date": _exact_score(gold_event.get("date"), pred_event.get("date")),
        "time": _exact_score(gold_event.get("time"), pred_event.get("time")),
        "venue": _string_score(gold_event.get("venue"), pred_event.get("venue")),
        "city": _string_score(gold_event.get("city"), pred_event.get("city")),
        "province": _string_score(gold_event.get("province"), pred_event.get("province")),
        "country": _exact_score(gold_event.get("country"), pred_event.get("country")),
        "event_name": _string_score(gold_event.get("event_name"), pred_event.get("event_name")),
        "ticket_info": _string_score(gold_event.get("ticket_info"), pred_event.get("ticket_info")),
        "status": _exact_score(gold_event.get("status"), pred_event.get("status")),
    }
    total = 0.0
    for field, weight in EVENT_SCORE_WEIGHTS.items():
        total += weight * scores.get(field, 0.0)
    return total


def _event_similarity_core(gold_event: Dict[str, Any], pred_event: Dict[str, Any]) -> float:
    scores = {
        "date": _exact_score(gold_event.get("date"), pred_event.get("date")),
        "venue": _string_score(gold_event.get("venue"), pred_event.get("venue")),
        "city": _string_score(gold_event.get("city"), pred_event.get("city")),
        "province": _string_score(gold_event.get("province"), pred_event.get("province")),
        "country": _exact_score(gold_event.get("country"), pred_event.get("country")),
    }
    total = 0.0
    for field, weight in CORE_EVENT_SCORE_WEIGHTS.items():
        total += weight * scores.get(field, 0.0)
    return total


def _hungarian(cost: List[List[float]]) -> List[int]:
    size = len(cost)
    if size == 0:
        return []
    u = [0.0] * (size + 1)
    v = [0.0] * (size + 1)
    p = [0] * (size + 1)
    way = [0] * (size + 1)
    for i in range(1, size + 1):
        p[0] = i
        j0 = 0
        minv = [float("inf")] * (size + 1)
        used = [False] * (size + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float("inf")
            j1 = 0
            for j in range(1, size + 1):
                if used[j]:
                    continue
                cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1 = j
            for j in range(size + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    assignment = [-1] * size
    for j in range(1, size + 1):
        if p[j] > 0:
            assignment[p[j] - 1] = j - 1
    return assignment


def _optimal_event_matches(
    gold_events: List[Dict[str, Any]],
    pred_events: List[Dict[str, Any]],
    similarity_fn: Callable[[Dict[str, Any], Dict[str, Any]], float] = _event_similarity,
) -> List[Tuple[int, Optional[int], float]]:
    gold_count = len(gold_events)
    pred_count = len(pred_events)
    size = max(gold_count, pred_count)
    if size == 0:
        return []
    similarity = [[0.0 for _ in range(size)] for _ in range(size)]
    for i in range(gold_count):
        for j in range(pred_count):
            similarity[i][j] = float(similarity_fn(gold_events[i], pred_events[j]))
    cost = [[1.0 - similarity[i][j] for j in range(size)] for i in range(size)]
    assignment = _hungarian(cost)
    matches: List[Tuple[int, Optional[int], float]] = []
    for i in range(gold_count):
        j = assignment[i] if i < len(assignment) else -1
        if j is None or j < 0 or j >= pred_count:
            matches.append((i, None, 0.0))
        else:
            matches.append((i, j, similarity[i][j]))
    return matches


def _match_events(
    gold_events: List[Dict[str, Any]],
    pred_events: List[Dict[str, Any]],
    similarity_fn: Callable[[Dict[str, Any], Dict[str, Any]], float] = _event_similarity,
) -> Tuple[float, float, float]:
    if not gold_events and not pred_events:
        return 1.0, 1.0, 1.0
    if not gold_events:
        return 0.0, 0.0, 0.0
    matches = _optimal_event_matches(gold_events, pred_events, similarity_fn=similarity_fn)
    match_total = 0.0
    venue_total = 0.0
    location_total = 0.0
    for gold_idx, pred_idx, score in matches:
        match_total += score
        if pred_idx is None:
            continue
        venue_total += _string_score(gold_events[gold_idx].get("venue"), pred_events[pred_idx].get("venue"))
        location_total += _location_score(gold_events[gold_idx], pred_events[pred_idx])
    total_gold = len(gold_events)
    if total_gold == 0:
        return 0.0, 0.0, 0.0
    return (match_total / total_gold, venue_total / total_gold, location_total / total_gold)


def _missing_field_rate(pred_events: List[Dict[str, Any]], expected_events: int) -> float:
    if expected_events == 0:
        return 0.0
    if not pred_events:
        return 1.0
    essential_fields = ("date", "venue", "city", "province")
    total = len(pred_events) * len(essential_fields)
    if total == 0:
        return 0.0
    missing = 0
    for event in pred_events:
        for field in essential_fields:
            if _is_blank(event.get(field)):
                missing += 1
    return missing / total


def _structured_score(parse_ok: bool, schema_strict_ok: bool) -> float:
    return 0.7 * (1.0 if schema_strict_ok else 0.0) + 0.3 * (1.0 if parse_ok else 0.0)


def _app_quality_score(
    structured_score: float,
    top_level_score: float,
    event_match_score: float,
    event_count_score: float,
    missing_field_rate: float,
) -> float:
    base = (
        QUALITY_WEIGHTS["structured"] * structured_score
        + QUALITY_WEIGHTS["top_level"] * top_level_score
        + QUALITY_WEIGHTS["event_match"] * event_match_score
        + QUALITY_WEIGHTS["event_count"] * event_count_score
    )
    score = base * 100.0
    score -= MISSING_FIELD_PENALTY * missing_field_rate
    return max(0.0, min(score, 100.0))


def _bootstrap_ci(values: List[float]) -> Optional[Tuple[float, float]]:
    if not values:
        return None
    rng = random.Random(BOOTSTRAP_SEED)
    count = len(values)
    means = []
    for _ in range(BOOTSTRAP_SAMPLES):
        total = 0.0
        for _ in range(count):
            total += values[rng.randrange(count)]
        means.append(total / count)
    means.sort()
    low_idx = int((BOOTSTRAP_ALPHA / 2) * BOOTSTRAP_SAMPLES)
    high_idx = int((1 - BOOTSTRAP_ALPHA / 2) * BOOTSTRAP_SAMPLES) - 1
    return means[low_idx], means[high_idx]


def _bootstrap_diff_stats(
    values_a: List[float],
    values_b: List[float],
) -> Optional[Dict[str, Any]]:
    if not values_a or not values_b:
        return None
    rng = random.Random(BOOTSTRAP_SEED)
    count_a = len(values_a)
    count_b = len(values_b)
    diffs = []
    for _ in range(BOOTSTRAP_SAMPLES):
        mean_a = sum(values_a[rng.randrange(count_a)] for _ in range(count_a)) / count_a
        mean_b = sum(values_b[rng.randrange(count_b)] for _ in range(count_b)) / count_b
        diffs.append(mean_a - mean_b)
    diffs.sort()
    low_idx = int((BOOTSTRAP_ALPHA / 2) * BOOTSTRAP_SAMPLES)
    high_idx = int((1 - BOOTSTRAP_ALPHA / 2) * BOOTSTRAP_SAMPLES) - 1
    diff_mean = (sum(values_a) / count_a) - (sum(values_b) / count_b)
    negative = sum(1 for d in diffs if d <= 0)
    positive = BOOTSTRAP_SAMPLES - negative
    p_value = 2 * min(negative / BOOTSTRAP_SAMPLES, positive / BOOTSTRAP_SAMPLES)
    return {
        "diff_mean": diff_mean,
        "ci_low": diffs[low_idx],
        "ci_high": diffs[high_idx],
        "p_value": p_value,
    }


def _format_ci(ci: Optional[Tuple[float, float]], digits: int = 2) -> Optional[List[float]]:
    if ci is None:
        return None
    return [round(ci[0], digits), round(ci[1], digits)]


def _format_ci_text(ci: Optional[List[float]]) -> str:
    if not ci:
        return "n/a"
    return f"{ci[0]}–{ci[1]}"


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_seed_values(paths: Iterable[Path]) -> List[int]:
    seeds = set()
    for path in paths:
        if not path.exists():
            continue
        if path.is_dir():
            candidates = path.rglob("*.meta.json")
        else:
            candidates = [path]
        for candidate in candidates:
            if candidate.suffix != ".json":
                continue
            meta = _load_meta(candidate)
            if not meta:
                continue
            seed = meta.get("seed")
            if isinstance(seed, int):
                seeds.add(seed)
    return sorted(seeds)


def command_report(args: argparse.Namespace) -> None:
    entries = load_manifest(Path(args.manifest))
    gt_dir = Path(args.ground_truth)
    pred_root = Path(args.predictions)
    judge_root = Path(args.judgements)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    total_posters = sum(1 for entry in entries if entry.get("status") == "ok")
    gt_cache: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        if entry.get("status") != "ok":
            continue
        poster_id = entry["id"]
        gt = _load_json(gt_dir / f"{poster_id}.json")
        if isinstance(gt, dict):
            gt_cache[poster_id] = gt
    total_gt = len(gt_cache)
    missing_gt = total_posters - total_gt

    ground_truth_cost = 0.0
    for poster_id in gt_cache:
        meta = _load_meta(gt_dir / f"{poster_id}.meta.json")
        if meta and isinstance(meta.get("estimated_cost_usd"), (int, float)):
            ground_truth_cost += meta["estimated_cost_usd"]
    rows = []
    model_quality: Dict[str, List[float]] = {}
    for model_dir in sorted(pred_root.iterdir()):
        if not model_dir.is_dir():
            continue
        model_name = model_dir.name
        judge_dir = judge_root / model_name
        scores = []
        schema_ok = []
        schema_valid = 0
        schema_strict = 0
        parse_ok = 0
        pred_missing = 0
        event_diff = []
        date_f1 = []
        app_quality_scores = []
        top_level_scores = []
        event_match_scores = []
        core_event_match_scores = []
        event_count_scores = []
        location_scores = []
        venue_scores = []
        missing_field_rates = []
        app_core_scores = []
        model_costs = []
        judge_costs = []
        for entry in entries:
            if entry.get("status") != "ok":
                continue
            poster_id = entry["id"]
            gt = gt_cache.get(poster_id)
            if gt is None:
                continue
            pred = _load_json(model_dir / f"{poster_id}.json")
            if pred is None:
                pred_missing += 1
            pred_ok = isinstance(pred, dict)
            if pred_ok:
                parse_ok += 1
            schema_valid_ok = _schema_valid(pred, strict=False) if pred_ok else False
            schema_strict_ok = _schema_valid(pred, strict=True) if pred_ok else False
            if schema_valid_ok:
                schema_valid += 1
            if schema_strict_ok:
                schema_strict += 1

            gold_events = _event_list(gt)
            pred_events = _event_list(pred)
            event_diff.append(abs(len(gold_events) - len(pred_events)))
            precision, recall, f1 = _date_metrics(gt, pred)
            date_f1.append(f1 if f1 is not None else 0.0)

            event_count_score = _event_count_score(gold_events, pred_events)
            event_match_score, venue_score, location_score = _match_events(gold_events, pred_events)
            core_event_match_score, _, _ = _match_events(
                gold_events,
                pred_events,
                similarity_fn=_event_similarity_core,
            )
            top_level_score = _score_top_level(gt, pred)
            missing_field_rate = _missing_field_rate(pred_events, len(gold_events))
            structured_score = _structured_score(pred_ok, schema_strict_ok)
            app_quality_score = _app_quality_score(
                structured_score,
                top_level_score,
                event_match_score,
                event_count_score,
                missing_field_rate,
            )
            app_core_score = _app_quality_score(
                structured_score,
                top_level_score,
                core_event_match_score,
                event_count_score,
                missing_field_rate,
            )
            app_quality_scores.append(app_quality_score)
            top_level_scores.append(top_level_score)
            event_match_scores.append(event_match_score)
            core_event_match_scores.append(core_event_match_score)
            event_count_scores.append(event_count_score)
            location_scores.append(location_score)
            venue_scores.append(venue_score)
            missing_field_rates.append(missing_field_rate)
            app_core_scores.append(app_core_score)
            judge = _load_json(judge_dir / f"{poster_id}.json") if judge_dir.exists() else None
            if isinstance(judge, dict) and isinstance(judge.get("overall_score"), (int, float)):
                scores.append(judge["overall_score"])
                schema_ok.append(1 if judge.get("schema_ok") else 0)

            meta = _load_meta(model_dir / f"{poster_id}.meta.json")
            if meta and isinstance(meta.get("estimated_cost_usd"), (int, float)):
                model_costs.append(meta["estimated_cost_usd"])
            meta = _load_meta(judge_dir / f"{poster_id}.meta.json") if judge_dir.exists() else None
            if meta and isinstance(meta.get("estimated_cost_usd"), (int, float)):
                judge_costs.append(meta["estimated_cost_usd"])

        total_cost = sum(model_costs) if model_costs else 0.0
        total_judge_cost = sum(judge_costs) if judge_costs else 0.0
        total_all = ground_truth_cost + total_cost + total_judge_cost
        app_quality_ci = _bootstrap_ci(app_quality_scores)
        app_quality_ci_formatted = _format_ci(app_quality_ci, digits=2)
        app_quality_std = statistics.pstdev(app_quality_scores) if len(app_quality_scores) > 1 else 0.0
        app_core_ci = _bootstrap_ci(app_core_scores)
        app_core_ci_formatted = _format_ci(app_core_ci, digits=2)
        app_core_std = statistics.pstdev(app_core_scores) if len(app_core_scores) > 1 else 0.0
        model_quality[model_name] = app_quality_scores
        rows.append(
            {
                "model": model_name,
                "posters": total_gt,
                "missing_predictions": pred_missing,
                "judged": len(scores),
                "app_quality_score": round(sum(app_quality_scores) / len(app_quality_scores), 2)
                if app_quality_scores
                else None,
                "app_quality_ci95": app_quality_ci_formatted,
                "app_quality_std": round(app_quality_std, 3),
                "app_core_score": round(sum(app_core_scores) / len(app_core_scores), 2)
                if app_core_scores
                else None,
                "app_core_ci95": app_core_ci_formatted,
                "app_core_std": round(app_core_std, 3),
                "avg_score": round(sum(scores) / len(scores), 2) if scores else None,
                "schema_ok_rate": round(sum(schema_ok) / len(schema_ok), 3) if schema_ok else None,
                "schema_valid_rate": round(schema_valid / total_gt, 3) if total_gt else None,
                "schema_strict_rate": round(schema_strict / total_gt, 3) if total_gt else None,
                "json_parse_rate": round(parse_ok / total_gt, 3) if total_gt else None,
                "avg_top_level_score": round(sum(top_level_scores) / len(top_level_scores), 3)
                if top_level_scores
                else None,
                "avg_event_match_score": round(sum(event_match_scores) / len(event_match_scores), 3)
                if event_match_scores
                else None,
                "avg_core_event_match_score": round(
                    sum(core_event_match_scores) / len(core_event_match_scores), 3
                )
                if core_event_match_scores
                else None,
                "avg_event_count_score": round(sum(event_count_scores) / len(event_count_scores), 3)
                if event_count_scores
                else None,
                "avg_location_score": round(sum(location_scores) / len(location_scores), 3)
                if location_scores
                else None,
                "avg_venue_score": round(sum(venue_scores) / len(venue_scores), 3)
                if venue_scores
                else None,
                "avg_missing_field_rate": round(sum(missing_field_rates) / len(missing_field_rates), 3)
                if missing_field_rates
                else None,
                "avg_event_diff": round(sum(event_diff) / len(event_diff), 3) if event_diff else None,
                "avg_date_f1": round(sum(date_f1) / len(date_f1), 3) if date_f1 else None,
                "prediction_cost_usd": round(total_cost, 6),
                "judge_cost_usd": round(total_judge_cost, 6),
                "ground_truth_cost_usd": round(ground_truth_cost, 6),
                "total_cost_usd": round(total_all, 6),
            }
        )

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report_lines = [
        "# Benchmark Report",
        "",
        f"Generated: {timestamp}",
        f"Posters (manifest ok): {total_posters}",
        f"Ground truth available: {total_gt}",
        f"Missing ground truth: {missing_gt}",
        "",
        "## Model summary",
        "",
        "| Model | Posters | Missing preds | App quality | App core | App 95% CI | Schema strict rate | JSON parse rate | Event match score | Core event match | Top-level score | Event count score | Missing field rate | Avg judge score | Total cost (USD) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        report_lines.append(
            f"| {row['model']} | {row['posters']} | {row['missing_predictions']} | {row['app_quality_score']} | "
            f"{row['app_core_score']} | {_format_ci_text(row['app_quality_ci95'])} | "
            f"{row['schema_strict_rate']} | {row['json_parse_rate']} | {row['avg_event_match_score']} | "
            f"{row['avg_core_event_match_score']} | {row['avg_top_level_score']} | "
            f"{row['avg_event_count_score']} | {row['avg_missing_field_rate']} | {row['avg_score']} | "
            f"{row['total_cost_usd']} |"
        )

    report_path = out_dir / "summary.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    summary_json = out_dir / "summary.json"
    summary_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    comparisons = []
    model_names = sorted(model_quality.keys())
    for i, left in enumerate(model_names):
        for right in model_names[i + 1 :]:
            stats = _bootstrap_diff_stats(model_quality[left], model_quality[right])
            if stats is None:
                continue
            comparisons.append(
                {
                    "model_a": left,
                    "model_b": right,
                    "diff_mean": round(stats["diff_mean"], 3),
                    "ci95": _format_ci((stats["ci_low"], stats["ci_high"]), digits=3),
                    "p_value": round(stats["p_value"], 4),
                    "significant": not (stats["ci_low"] <= 0 <= stats["ci_high"]),
                }
            )
    comparisons_path = out_dir / "comparisons.json"
    comparisons_path.write_text(json.dumps(comparisons, ensure_ascii=False, indent=2), encoding="utf-8")
    comparisons_lines = [
        "# Model comparisons (app quality, bootstrap)",
        "",
        "| Model A | Model B | Mean diff | 95% CI | p-value | Significant |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in comparisons:
        comparisons_lines.append(
            f"| {item['model_a']} | {item['model_b']} | {item['diff_mean']} | "
            f"{_format_ci_text(item['ci95'])} | {item['p_value']} | {item['significant']} |"
        )
    comparisons_md = out_dir / "comparisons.md"
    comparisons_md.write_text("\n".join(comparisons_lines) + "\n", encoding="utf-8")

    prompt_hashes = {}
    prompt_dir = Path("benchmark/prompts")
    if prompt_dir.exists():
        for prompt_path in sorted(prompt_dir.glob("*.txt")):
            prompt_hashes[str(prompt_path)] = _hash_file(prompt_path)
    seed_values = _collect_seed_values([gt_dir, pred_root, judge_root])
    meta = {
        "generated_at": timestamp,
        "posters_manifest_ok": total_posters,
        "ground_truth_available": total_gt,
        "missing_ground_truth": missing_gt,
        "temperature": DEFAULT_TEMPERATURE,
        "seed_values": seed_values,
        "bootstrap": {
            "samples": BOOTSTRAP_SAMPLES,
            "seed": BOOTSTRAP_SEED,
            "alpha": BOOTSTRAP_ALPHA,
        },
        "weights": {
            "top_level": TOP_LEVEL_WEIGHTS,
            "event": EVENT_SCORE_WEIGHTS,
            "core_event": CORE_EVENT_SCORE_WEIGHTS,
            "quality": QUALITY_WEIGHTS,
            "missing_field_penalty": MISSING_FIELD_PENALTY,
        },
        "prompt_hashes": prompt_hashes,
    }
    meta_path = out_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _format_svg_scatter(points: List[Dict[str, Any]], out_path: Path) -> None:
    width = 720
    height = 480
    margin = 60
    plot_w = width - margin * 2
    plot_h = height - margin * 2

    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    min_x = min(xs) if xs else 0.0
    max_x = max(xs) if xs else 1.0
    min_y = min(ys) if ys else 0.0
    max_y = max(ys) if ys else 100.0
    if min_x == max_x:
        max_x = min_x + 1.0
    if min_y == max_y:
        max_y = min_y + 1.0

    def sx(value: float) -> float:
        return margin + (value - min_x) / (max_x - min_x) * plot_w

    def sy(value: float) -> float:
        return margin + (max_y - value) / (max_y - min_y) * plot_h

    median_x = sorted(xs)[len(xs) // 2] if xs else 0.0
    median_y = sorted(ys)[len(ys) // 2] if ys else 0.0

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<rect x="{margin}" y="{margin}" width="{plot_w}" height="{plot_h}" fill="#f6f4f0" stroke="#d8d2c8"/>',
        f'<line x1="{sx(median_x)}" y1="{margin}" x2="{sx(median_x)}" y2="{height - margin}" stroke="#b7b0a8" stroke-dasharray="4 4"/>',
        f'<line x1="{margin}" y1="{sy(median_y)}" x2="{width - margin}" y2="{sy(median_y)}" stroke="#b7b0a8" stroke-dasharray="4 4"/>',
        f'<text x="{width / 2}" y="{margin - 22}" text-anchor="middle" font-size="16" fill="#3a3127">App Quality vs Cost</text>',
        f'<text x="{width / 2}" y="{height - 16}" text-anchor="middle" font-size="12" fill="#3a3127">Cost (USD)</text>',
        f'<text x="{18}" y="{height / 2}" text-anchor="middle" font-size="12" fill="#3a3127" transform="rotate(-90 18 {height/2})">App quality score</text>',
    ]

    for point in points:
        cx = sx(point["x"])
        cy = sy(point["y"])
        lines.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="#d95d39"/>')
        label = point["label"]
        lines.append(f'<text x="{cx + 10:.1f}" y="{cy - 8:.1f}" font-size="11" fill="#3a3127">{label}</text>')

    lines.append("</svg>")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def command_plot(args: argparse.Namespace) -> None:
    report_path = Path(args.report)
    if not report_path.exists():
        raise SystemExit(f"Missing report: {report_path}")
    rows = json.loads(report_path.read_text(encoding="utf-8"))
    points = []
    for row in rows:
        score = row.get("app_quality_score")
        cost = row.get("total_cost_usd")
        if cost is None:
            cost = row.get("prediction_cost_usd")
        if score is None or cost is None:
            continue
        points.append(
            {
                "label": row.get("model", "unknown"),
                "x": float(cost),
                "y": float(score),
            }
        )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    svg_path = out_dir / "scatter.svg"
    _format_svg_scatter(points, svg_path)


def _git_commit() -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


def command_publish(args: argparse.Namespace) -> None:
    report_dir = Path(args.report_dir)
    out_dir = Path(args.out)
    label = safe_name(args.label) if args.label else "run"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = out_dir / f"{timestamp}-{label}"
    run_dir.mkdir(parents=True, exist_ok=True)

    files_to_copy = [
        "summary.json",
        "summary.md",
        "scatter.svg",
        "comparisons.json",
        "comparisons.md",
        "meta.json",
        "final_report.md",
    ]
    copied = []
    for name in files_to_copy:
        src = report_dir / name
        if not src.exists():
            continue
        dest = run_dir / name
        shutil.copy2(src, dest)
        copied.append(name)

    urls_path = Path(args.urls) if args.urls else None
    manifest_path = Path(args.manifest) if args.manifest else None
    summary_path = report_dir / "summary.json"
    models = []
    if summary_path.exists():
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            models = [row.get("model") for row in data if isinstance(row, dict)]
        except Exception:
            models = []
    metadata = {
        "run_id": run_dir.name,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "temperature": DEFAULT_TEMPERATURE,
        "models": [model for model in models if model],
        "report_source": str(report_dir),
        "files": copied,
    }
    meta_report_path = report_dir / "meta.json"
    if meta_report_path.exists():
        try:
            report_meta = json.loads(meta_report_path.read_text(encoding="utf-8"))
            if isinstance(report_meta, dict):
                metadata["seed_values"] = report_meta.get("seed_values")
                metadata["bootstrap"] = report_meta.get("bootstrap")
        except Exception:
            pass
    if urls_path and urls_path.exists():
        metadata["urls_file"] = str(urls_path)
        metadata["urls_sha256"] = _hash_file(urls_path)
    if manifest_path and manifest_path.exists():
        metadata["manifest_file"] = str(manifest_path)
        metadata["manifest_sha256"] = _hash_file(manifest_path)

    meta_path = run_dir / "run_metadata.json"
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.note:
        note_path = run_dir / "notes.md"
        note_path.write_text(args.note.strip() + "\n", encoding="utf-8")


def _published_label(run_id: str) -> str:
    match = re.match(r"^\\d{8}-\\d{6}-(.+)$", run_id)
    return match.group(1) if match else run_id


def _format_ci_range(ci: Any) -> str:
    if isinstance(ci, (list, tuple)) and len(ci) == 2:
        return f"{ci[0]:.2f}-{ci[1]:.2f}"
    return ""


def command_ledger(args: argparse.Namespace) -> None:
    published_dir = Path(args.published)
    out_csv = Path(args.out)
    out_md = Path(args.md) if args.md else None
    rows: List[Dict[str, Any]] = []
    if not published_dir.exists():
        raise RuntimeError(f"Published directory not found: {published_dir}")

    for run_dir in sorted([p for p in published_dir.iterdir() if p.is_dir()]):
        summary_path = run_dir / "summary.json"
        if not summary_path.exists():
            continue
        try:
            summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(summary_data, list):
            continue
        run_meta = {}
        meta_path = run_dir / "run_metadata.json"
        if meta_path.exists():
            try:
                run_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                run_meta = {}
        report_meta = {}
        report_meta_path = run_dir / "meta.json"
        if report_meta_path.exists():
            try:
                report_meta = json.loads(report_meta_path.read_text(encoding="utf-8"))
            except Exception:
                report_meta = {}

        for row in summary_data:
            if not isinstance(row, dict):
                continue
            ci = row.get("app_quality_ci95")
            core_ci = row.get("app_core_ci95")
            rows.append(
                {
                    "run_id": run_dir.name,
                    "label": _published_label(run_dir.name),
                    "created_at": run_meta.get("created_at"),
                    "git_commit": run_meta.get("git_commit"),
                    "temperature": run_meta.get("temperature"),
                    "model": row.get("model"),
                    "posters": row.get("posters"),
                    "missing_predictions": row.get("missing_predictions"),
                    "judged": row.get("judged"),
                    "app_quality_score": row.get("app_quality_score"),
                    "app_quality_ci95": ci if isinstance(ci, list) and len(ci) == 2 else None,
                    "app_quality_ci95_low": ci[0] if isinstance(ci, list) and len(ci) == 2 else None,
                    "app_quality_ci95_high": ci[1] if isinstance(ci, list) and len(ci) == 2 else None,
                    "app_core_score": row.get("app_core_score"),
                    "app_core_ci95": core_ci if isinstance(core_ci, list) and len(core_ci) == 2 else None,
                    "app_core_ci95_low": core_ci[0] if isinstance(core_ci, list) and len(core_ci) == 2 else None,
                    "app_core_ci95_high": core_ci[1] if isinstance(core_ci, list) and len(core_ci) == 2 else None,
                    "schema_strict_rate": row.get("schema_strict_rate"),
                    "schema_valid_rate": row.get("schema_valid_rate"),
                    "json_parse_rate": row.get("json_parse_rate"),
                    "avg_top_level_score": row.get("avg_top_level_score"),
                    "avg_event_match_score": row.get("avg_event_match_score"),
                    "avg_core_event_match_score": row.get("avg_core_event_match_score"),
                    "avg_event_count_score": row.get("avg_event_count_score"),
                    "avg_location_score": row.get("avg_location_score"),
                    "avg_venue_score": row.get("avg_venue_score"),
                    "avg_missing_field_rate": row.get("avg_missing_field_rate"),
                    "avg_date_f1": row.get("avg_date_f1"),
                    "prediction_cost_usd": row.get("prediction_cost_usd"),
                    "judge_cost_usd": row.get("judge_cost_usd"),
                    "ground_truth_cost_usd": row.get("ground_truth_cost_usd"),
                    "total_cost_usd": row.get("total_cost_usd"),
                    "urls_sha256": run_meta.get("urls_sha256"),
                    "manifest_sha256": run_meta.get("manifest_sha256"),
                    "bootstrap_seed": (report_meta.get("bootstrap") or {}).get("seed"),
                    "prompt_hashes": report_meta.get("prompt_hashes"),
                }
            )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run_id",
        "label",
        "created_at",
        "git_commit",
        "temperature",
        "model",
        "posters",
        "missing_predictions",
        "judged",
        "app_quality_score",
        "app_quality_ci95",
        "app_quality_ci95_low",
        "app_quality_ci95_high",
        "app_core_score",
        "app_core_ci95",
        "app_core_ci95_low",
        "app_core_ci95_high",
        "schema_strict_rate",
        "schema_valid_rate",
        "json_parse_rate",
        "avg_top_level_score",
        "avg_event_match_score",
        "avg_core_event_match_score",
        "avg_event_count_score",
        "avg_location_score",
        "avg_venue_score",
        "avg_missing_field_rate",
        "avg_date_f1",
        "prediction_cost_usd",
        "judge_cost_usd",
        "ground_truth_cost_usd",
        "total_cost_usd",
        "urls_sha256",
        "manifest_sha256",
        "bootstrap_seed",
        "prompt_hashes",
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    if out_md:
        rows_sorted = sorted(
            rows,
            key=lambda item: item.get("app_quality_score") if isinstance(item.get("app_quality_score"), (int, float)) else -1,
            reverse=True,
        )
        headers = [
            "run_id",
            "model",
            "app_quality_score",
            "app_core_score",
            "app_quality_ci95",
            "schema_strict_rate",
            "missing_predictions",
            "judged",
            "total_cost_usd",
        ]
        lines = ["# Experiment Ledger", "", "| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
        for row in rows_sorted:
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row.get("run_id", "")),
                        str(row.get("model", "")),
                        f"{row.get('app_quality_score', '')}",
                        f"{row.get('app_core_score', '')}",
                        _format_ci_range(row.get("app_quality_ci95")),
                        f"{row.get('schema_strict_rate', '')}",
                        f"{row.get('missing_predictions', '')}",
                        f"{row.get('judged', '')}",
                        f"{row.get('total_cost_usd', '')}",
                    ]
                )
                + " |"
            )
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def command_interpret(args: argparse.Namespace) -> None:
    report_dir = Path(args.report_dir)
    summary_path = report_dir / "summary.json"
    comparisons_path = report_dir / "comparisons.md"
    meta_path = report_dir / "meta.json"

    if not summary_path.exists():
        raise SystemExit(f"Missing summary: {summary_path}")

    summary_text = summary_path.read_text(encoding="utf-8")
    comparisons_text = comparisons_path.read_text(encoding="utf-8") if comparisons_path.exists() else ""
    meta_text = meta_path.read_text(encoding="utf-8") if meta_path.exists() else "{}"
    protocol_text = Path("benchmark/PROTOCOL.md").read_text(encoding="utf-8") if Path("benchmark/PROTOCOL.md").exists() else ""
    dataset_text = Path("benchmark/DATASET_CARD.md").read_text(encoding="utf-8") if Path("benchmark/DATASET_CARD.md").exists() else ""

    prompt = read_prompt(Path(args.prompt))
    payload = (
        f"{prompt}\n\n"
        f"Ground truth quality: {args.ground_truth_quality}\n\n"
        f"Summary JSON:\n{summary_text}\n\n"
        f"Comparisons table:\n{comparisons_text}\n\n"
        f"Meta JSON:\n{meta_text}\n\n"
        f"Protocol:\n{protocol_text}\n\n"
        f"Dataset card:\n{dataset_text}\n"
    )

    max_tokens = _resolve_max_output(args.max_output)
    raw_text, meta = openrouter_chat(
        model=args.model,
        messages=[{"role": "user", "content": payload}],
        max_tokens=max_tokens,
        temperature=DEFAULT_TEMPERATURE,
        seed=args.seed,
        timeout=args.timeout,
        pricing_cache=Path("benchmark/cache/openrouter_models.json"),
    )
    _save_text_with_meta(Path(args.out), raw_text.strip() + "\n", meta=meta)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run poster extraction benchmarks.")
    sub = parser.add_subparsers(dest="command", required=True)

    download = sub.add_parser("download", help="Download poster images.")
    download.add_argument("--urls", required=True, help="Path to URL list.")
    download.add_argument("--out", required=True, help="Output image directory.")
    download.add_argument("--manifest", required=True, help="Manifest JSON path.")
    download.add_argument("--limit", type=int, help="Limit number of URLs.")
    download.add_argument("--start", type=int, default=0, help="Start index.")
    download.add_argument("--timeout", type=float, default=20.0, help="Download timeout.")
    download.add_argument("--sleep", type=float, default=0.0, help="Delay between downloads.")
    download.add_argument("--force", action="store_true", help="Redownload existing images.")
    download.set_defaults(func=command_download)

    ocr = sub.add_parser("ocr", help="OCR posters with Gemini.")
    ocr.add_argument("--manifest", required=True, help="Manifest JSON path.")
    ocr.add_argument("--out", required=True, help="OCR output directory.")
    ocr.add_argument("--model", required=True, help="Gemini model ID.")
    ocr.add_argument("--prompt", default="benchmark/prompts/ocr.txt")
    ocr.add_argument("--limit", type=int, help="Limit number of posters.")
    ocr.add_argument("--start", type=int, default=0, help="Start index.")
    ocr.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ocr.add_argument(
        "--max-output",
        default="max",
        help="Max output tokens for OCR (Gemini). Use an int or 'max'.",
    )
    ocr.add_argument("--parallel", type=int, default=4, help="Parallel workers for OCR.")
    ocr.add_argument("--rpm", type=int, help="Requests per minute limit for OCR.")
    ocr.add_argument("--tpm", type=int, help="Tokens per minute limit for OCR.")
    ocr.add_argument("--tokens-per-request", type=int, help="Estimated tokens per OCR request.")
    ocr.add_argument("--sleep", type=float, default=0.0, help="Delay between requests.")
    ocr.add_argument("--force", action="store_true", help="Overwrite existing OCR outputs.")
    ocr.set_defaults(func=command_ocr)

    parse_ocr = sub.add_parser("parse-ocr", help="Parse OCR text into JSON with Gemini.")
    parse_ocr.add_argument("--manifest", required=True, help="Manifest JSON path.")
    parse_ocr.add_argument("--ocr", required=True, help="OCR directory with .txt files.")
    parse_ocr.add_argument("--out", required=True, help="Prediction output directory.")
    parse_ocr.add_argument("--model", required=True, help="Gemini model ID.")
    parse_ocr.add_argument("--prompt", default="benchmark/prompts/parse_ocr.txt")
    parse_ocr.add_argument("--limit", type=int, help="Limit number of posters.")
    parse_ocr.add_argument("--start", type=int, default=0, help="Start index.")
    parse_ocr.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parse_ocr.add_argument(
        "--max-output",
        default="max",
        help="Max output tokens for parsing (Gemini). Use an int or 'max'.",
    )
    parse_ocr.add_argument("--parallel", type=int, default=4, help="Parallel workers for parsing.")
    parse_ocr.add_argument("--rpm", type=int, help="Requests per minute limit for parsing.")
    parse_ocr.add_argument("--tpm", type=int, help="Tokens per minute limit for parsing.")
    parse_ocr.add_argument("--tokens-per-request", type=int, help="Estimated tokens per parse request.")
    parse_ocr.add_argument("--sleep", type=float, default=0.0, help="Delay between requests.")
    parse_ocr.add_argument("--force", action="store_true", help="Overwrite existing outputs.")
    parse_ocr.add_argument(
        "--repair-json",
        action="store_true",
        help="Attempt JSON repair for schema-strict output.",
    )
    parse_ocr.add_argument(
        "--repair-prompt",
        default="benchmark/prompts/repair_json.txt",
        help="Prompt file used for JSON repair.",
    )
    parse_ocr.set_defaults(func=command_parse_ocr)

    fill_locations = sub.add_parser("fill-locations", help="Fill missing location fields from OCR.")
    fill_locations.add_argument("--manifest", required=True, help="Manifest JSON path.")
    fill_locations.add_argument("--predictions", required=True, help="Predictions root directory.")
    fill_locations.add_argument("--ocr", required=True, help="OCR directory with .txt files.")
    fill_locations.add_argument("--model", required=True, help="Gemini model ID.")
    fill_locations.add_argument("--model-dir", help="Specific model directory to fill.")
    fill_locations.add_argument("--prompt", default="benchmark/prompts/fill_locations.txt")
    fill_locations.add_argument("--limit", type=int, help="Limit number of posters.")
    fill_locations.add_argument("--start", type=int, default=0, help="Start index.")
    fill_locations.add_argument("--seed", type=int, default=DEFAULT_SEED)
    fill_locations.add_argument(
        "--max-output",
        default="max",
        help="Max output tokens for location fill (Gemini). Use an int or 'max'.",
    )
    fill_locations.add_argument("--parallel", type=int, default=4, help="Parallel workers for fill.")
    fill_locations.add_argument("--rpm", type=int, help="Requests per minute limit for fill.")
    fill_locations.add_argument("--tpm", type=int, help="Tokens per minute limit for fill.")
    fill_locations.add_argument("--tokens-per-request", type=int, help="Estimated tokens per fill request.")
    fill_locations.add_argument("--sleep", type=float, default=0.0, help="Delay between requests.")
    fill_locations.add_argument("--force", action="store_true", help="Force fill even if not needed.")
    fill_locations.add_argument(
        "--retry-errors",
        action="store_true",
        help="Only rerun posters that have a .locfill.error.json file.",
    )
    fill_locations.set_defaults(func=command_fill_locations)

    ground = sub.add_parser("ground-truth", help="Generate ground truth with OpenRouter.")
    ground.add_argument("--manifest", required=True, help="Manifest JSON path.")
    ground.add_argument("--out", required=True, help="Ground truth output directory.")
    ground.add_argument("--model", required=True, help="OpenRouter model name.")
    ground.add_argument("--prompt", default="benchmark/prompts/ground_truth.txt")
    ground.add_argument("--limit", type=int, help="Limit number of posters.")
    ground.add_argument("--start", type=int, default=0, help="Start index.")
    ground.add_argument(
        "--max-output",
        "--max-tokens",
        dest="max_output",
        default="max",
        help="Max output tokens for OpenRouter (use 'max' for model limit).",
    )
    ground.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ground.add_argument("--timeout", type=float, default=DEFAULT_OPENROUTER_TIMEOUT)
    ground.add_argument("--sleep", type=float, default=0.0, help="Delay between requests.")
    ground.add_argument("--force", action="store_true", help="Overwrite existing outputs.")
    ground.add_argument(
        "--retry-errors",
        action="store_true",
        help="Only rerun posters that have a .error.json file.",
    )
    ground.set_defaults(func=command_ground_truth)

    predict = sub.add_parser("predict", help="Run model predictions.")
    predict.add_argument("--manifest", required=True, help="Manifest JSON path.")
    predict.add_argument("--out", required=True, help="Prediction output directory.")
    predict.add_argument("--models", nargs="+", required=True, help="Model specs: kind:name.")
    predict.add_argument("--prompt", default="benchmark/prompts/predict.txt")
    predict.add_argument("--limit", type=int, help="Limit number of posters.")
    predict.add_argument("--start", type=int, default=0, help="Start index.")
    predict.add_argument("--seed", type=int, default=DEFAULT_SEED)
    predict.add_argument(
        "--max-output",
        default="half",
        help="Max output tokens for predictions (Gemini/Ollama). Use an int, 'max', or 'half' (Ollama only).",
    )
    predict.add_argument("--ollama-timeout", type=float, default=DEFAULT_OLLAMA_TIMEOUT)
    predict.add_argument("--timeout", type=float, default=DEFAULT_OPENROUTER_TIMEOUT)
    predict.add_argument(
        "--openrouter-plugins",
        help="JSON array (or file path) of OpenRouter plugins to enable for predictions.",
    )
    predict.add_argument(
        "--repair-json",
        action="store_true",
        help="Attempt JSON repair for schema-strict output (Gemini predictions).",
    )
    predict.add_argument(
        "--repair-prompt",
        default="benchmark/prompts/repair_json.txt",
        help="Prompt file used for JSON repair.",
    )
    predict.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Parallel workers for Gemini predictions.",
    )
    predict.add_argument(
        "--rpm",
        type=int,
        help="Requests per minute limit for Gemini predictions.",
    )
    predict.add_argument(
        "--tpm",
        type=int,
        help="Tokens per minute limit for Gemini predictions.",
    )
    predict.add_argument(
        "--tokens-per-request",
        type=int,
        help="Estimated tokens per Gemini request (used with --tpm).",
    )
    predict.add_argument(
        "--ollama-context",
        type=int,
        help="Override Ollama context length (num_ctx) for performance tuning.",
    )
    predict.add_argument("--sleep", type=float, default=0.0, help="Delay between requests.")
    predict.add_argument("--force", action="store_true", help="Overwrite existing outputs.")
    predict.set_defaults(func=command_predict)

    repair = sub.add_parser("repair", help="Repair prediction JSON using Gemini.")
    repair.add_argument("--manifest", required=True, help="Manifest JSON path.")
    repair.add_argument("--predictions", required=True, help="Predictions root directory.")
    repair.add_argument("--model", required=True, help="Gemini model ID for repair.")
    repair.add_argument("--model-dir", help="Specific model directory to repair.")
    repair.add_argument("--prompt", default="benchmark/prompts/repair_json.txt")
    repair.add_argument("--limit", type=int, help="Limit number of posters.")
    repair.add_argument("--start", type=int, default=0, help="Start index.")
    repair.add_argument("--seed", type=int, default=DEFAULT_SEED)
    repair.add_argument(
        "--max-output",
        default="max",
        help="Max output tokens for repair (Gemini). Use an int or 'max'.",
    )
    repair.add_argument("--parallel", type=int, default=4, help="Parallel workers for repair.")
    repair.add_argument("--rpm", type=int, help="Requests per minute limit for repair.")
    repair.add_argument("--tpm", type=int, help="Tokens per minute limit for repair.")
    repair.add_argument("--tokens-per-request", type=int, help="Estimated tokens per repair request.")
    repair.add_argument("--sleep", type=float, default=0.0, help="Delay between requests.")
    repair.add_argument("--force", action="store_true", help="Force repair even if schema is valid.")
    repair.set_defaults(func=command_repair)

    refine = sub.add_parser("refine", help="Refine predictions with image + JSON.")
    refine.add_argument("--manifest", required=True, help="Manifest JSON path.")
    refine.add_argument("--predictions", required=True, help="Predictions root directory.")
    refine.add_argument("--model", required=True, help="Gemini model ID for refinement.")
    refine.add_argument("--model-dir", help="Specific model directory to refine.")
    refine.add_argument("--prompt", default="benchmark/prompts/refine_v1.txt")
    refine.add_argument("--limit", type=int, help="Limit number of posters.")
    refine.add_argument("--start", type=int, default=0, help="Start index.")
    refine.add_argument("--seed", type=int, default=DEFAULT_SEED)
    refine.add_argument(
        "--max-output",
        default="max",
        help="Max output tokens for refinement (Gemini). Use an int or 'max'.",
    )
    refine.add_argument("--parallel", type=int, default=4, help="Parallel workers for refinement.")
    refine.add_argument("--rpm", type=int, help="Requests per minute limit for refinement.")
    refine.add_argument("--tpm", type=int, help="Tokens per minute limit for refinement.")
    refine.add_argument("--tokens-per-request", type=int, help="Estimated tokens per refine request.")
    refine.add_argument("--sleep", type=float, default=0.0, help="Delay between requests.")
    refine.add_argument("--force", action="store_true", help="Force refinement even if not needed.")
    refine.add_argument(
        "--retry-errors",
        action="store_true",
        help="Only rerun posters that have a .refine.error.json file.",
    )
    refine.set_defaults(func=command_refine)

    normalize = sub.add_parser("normalize", help="Normalize locations in prediction JSON.")
    normalize.add_argument("--manifest", required=True, help="Manifest JSON path.")
    normalize.add_argument("--predictions", required=True, help="Predictions root directory.")
    normalize.add_argument("--model-dir", help="Specific model directory to normalize.")
    normalize.add_argument("--limit", type=int, help="Limit number of posters.")
    normalize.add_argument("--start", type=int, default=0, help="Start index.")
    normalize.add_argument("--force", action="store_true", help="Write outputs even if unchanged.")
    normalize.set_defaults(func=command_normalize)

    normalize_time = sub.add_parser("normalize-time", help="Normalize time fields in prediction JSON.")
    normalize_time.add_argument("--manifest", required=True, help="Manifest JSON path.")
    normalize_time.add_argument("--predictions", required=True, help="Predictions root directory.")
    normalize_time.add_argument("--model-dir", help="Specific model directory to normalize.")
    normalize_time.add_argument("--limit", type=int, help="Limit number of posters.")
    normalize_time.add_argument("--start", type=int, default=0, help="Start index.")
    normalize_time.add_argument("--force", action="store_true", help="Write outputs even if unchanged.")
    normalize_time.set_defaults(func=command_normalize_time)

    judge = sub.add_parser("judge", help="Judge predictions with OpenRouter.")
    judge.add_argument("--manifest", required=True, help="Manifest JSON path.")
    judge.add_argument("--ground-truth", required=True, help="Ground truth directory.")
    judge.add_argument("--predictions", required=True, help="Predictions directory.")
    judge.add_argument("--out", required=True, help="Judge output directory.")
    judge.add_argument("--model", required=True, help="OpenRouter judge model.")
    judge.add_argument("--prompt", default="benchmark/prompts/judge.txt")
    judge.add_argument("--limit", type=int, help="Limit number of posters.")
    judge.add_argument("--start", type=int, default=0, help="Start index.")
    judge.add_argument(
        "--max-output",
        "--max-tokens",
        dest="max_output",
        default="1024",
        help="Max output tokens for OpenRouter judge (use 'max' for model limit).",
    )
    judge.add_argument("--seed", type=int, default=DEFAULT_SEED)
    judge.add_argument("--timeout", type=float, default=DEFAULT_OPENROUTER_TIMEOUT)
    judge.add_argument("--sleep", type=float, default=0.0, help="Delay between requests.")
    judge.add_argument(
        "--compact",
        action="store_true",
        help="Judge with a compact JSON view (date/venue/city/province only).",
    )
    judge.add_argument("--force", action="store_true", help="Overwrite existing outputs.")
    judge.set_defaults(func=command_judge)

    report = sub.add_parser("report", help="Build a summary report.")
    report.add_argument("--manifest", required=True, help="Manifest JSON path.")
    report.add_argument("--ground-truth", required=True, help="Ground truth directory.")
    report.add_argument("--predictions", required=True, help="Predictions directory.")
    report.add_argument("--judgements", required=True, help="Judge output directory.")
    report.add_argument("--out", required=True, help="Report output directory.")
    report.set_defaults(func=command_report)

    plot = sub.add_parser("plot", help="Create a cost vs performance scatter plot.")
    plot.add_argument("--report", required=True, help="Path to summary.json.")
    plot.add_argument("--out", required=True, help="Output directory for plot.")
    plot.set_defaults(func=command_plot)

    interpret = sub.add_parser("interpret", help="Generate a narrative benchmark report.")
    interpret.add_argument("--report-dir", default="benchmark/report", help="Report directory.")
    interpret.add_argument("--out", default="benchmark/report/final_report.md", help="Output markdown path.")
    interpret.add_argument("--model", default="openai/gpt-5.2", help="OpenRouter model name.")
    interpret.add_argument("--prompt", default="benchmark/prompts/interpret.txt")
    interpret.add_argument("--max-output", default="4096")
    interpret.add_argument("--seed", type=int, default=DEFAULT_SEED)
    interpret.add_argument("--timeout", type=float, default=DEFAULT_OPENROUTER_TIMEOUT)
    interpret.add_argument("--ground-truth-quality", default="silver")
    interpret.set_defaults(func=command_interpret)

    publish = sub.add_parser("publish", help="Copy a report into a versioned publish folder.")
    publish.add_argument("--report-dir", default="benchmark/report", help="Report directory.")
    publish.add_argument("--out", default="benchmark/published", help="Publish output directory.")
    publish.add_argument("--label", default="run", help="Label for this run.")
    publish.add_argument("--urls", default="docs/test_poster_urls.txt", help="Dataset URL list.")
    publish.add_argument("--manifest", default="benchmark/manifest.json", help="Manifest file.")
    publish.add_argument("--note", help="Optional markdown note to include.")
    publish.set_defaults(func=command_publish)

    ledger = sub.add_parser("ledger", help="Build a dataset of published runs.")
    ledger.add_argument("--published", default="benchmark/published", help="Published runs directory.")
    ledger.add_argument("--out", default="benchmark/experiments.csv", help="Output CSV path.")
    ledger.add_argument("--md", default="benchmark/experiments.md", help="Optional markdown summary path.")
    ledger.set_defaults(func=command_ledger)

    return parser


def main() -> None:
    if load_dotenv is not None:
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
