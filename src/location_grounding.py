import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict
from urllib.parse import quote_plus

import requests
from google import genai
from google.genai import errors
from google.genai import types

from config import Config


class LocationSource(TypedDict):
    title: str
    url: str


class LocationResult(TypedDict):
    place_name: Optional[str]
    city: Optional[str]
    province: Optional[str]
    country: Optional[str]
    google_maps_url: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    confidence: float
    sources: List[LocationSource]


class RateLimitError(RuntimeError):
    pass


MODEL_NAME = "models/gemini-flash-latest"
_CLIENT: Optional[genai.Client] = None
JINA_SEARCH_URL = os.getenv("JINA_SEARCH_URL", "https://s.jina.ai/{query}")
JINA_READER_URL = os.getenv("JINA_READER_URL", "https://r.jina.ai/{url}")


def _get_gemini_client() -> genai.Client:
    global _CLIENT
    if _CLIENT is None:
        if not Config.GEMINI_API_KEY:
            raise SystemExit("GEMINI_API_KEY not set.")
        _CLIENT = genai.Client(api_key=Config.GEMINI_API_KEY)
    return _CLIENT


def _get_jina_key() -> str:
    if not Config.JINA_API_KEY:
        raise SystemExit("JINA_API_KEY not set.")
    return Config.JINA_API_KEY


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_cache(cache_path: Optional[Path]) -> Dict[str, Any]:
    if not cache_path or not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logging.warning("Failed to read cache %s: %s", cache_path, exc)
        return {}


def _save_cache(cache_path: Optional[Path], cache: Dict[str, Any]) -> None:
    if not cache_path:
        return
    _ensure_parent_dir(cache_path)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def _format_search_url(query: str, base: str) -> str:
    encoded = quote_plus(query)
    if "{query}" in base:
        return base.format(query=encoded)
    if base.endswith("/"):
        return base + encoded
    return base + encoded


def _format_reader_url(url: str, base: str) -> str:
    if "{url}" in base:
        return base.format(url=url)
    if base.endswith("/"):
        return base + url
    return base + url


def _jina_headers(accept: str) -> Dict[str, str]:
    headers = {"Accept": accept}
    key = _get_jina_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _jina_search(
    query: str,
    top_k: int,
    timeout: float,
    search_url: str,
) -> List[Dict[str, Optional[str]]]:
    url = _format_search_url(query, search_url)
    response = requests.get(
        url, headers=_jina_headers("application/json"), timeout=timeout
    )
    response.raise_for_status()
    data = response.json()

    results = None
    if isinstance(data, dict):
        for key in ("data", "results", "items", "hits"):
            if key in data:
                results = data.get(key)
                break
    if results is None:
        results = data
    if isinstance(results, dict):
        results = [results]
    if not isinstance(results, list):
        return []

    parsed = []
    for item in results:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("link")
        title = item.get("title") or item.get("name") or url
        snippet = item.get("description") or item.get("snippet") or item.get("text")
        if url:
            parsed.append({"title": title, "url": url, "snippet": snippet})
        if len(parsed) >= top_k:
            break

    return parsed


def _jina_read(
    url: str,
    timeout: float,
    max_chars: int,
    reader_url: str,
) -> str:
    endpoint = _format_reader_url(url, reader_url)
    response = requests.get(
        endpoint, headers=_jina_headers("text/plain"), timeout=timeout
    )
    response.raise_for_status()
    text = response.text.strip()
    if max_chars and len(text) > max_chars:
        return text[:max_chars]
    return text


def _jina_ground_location(
    query: str,
    context: str,
    top_k: int,
    reader_chars: int,
    timeout: float,
    search_url: str,
    reader_url: str,
    mode: str,
) -> Optional[LocationResult]:
    search_results = _jina_search(
        query=query, top_k=top_k, timeout=timeout, search_url=search_url
    )
    if not search_results:
        return None

    if mode == "search":
        reader_limit = 0
    elif mode == "hybrid":
        reader_limit = 1
    else:
        reader_limit = top_k

    source_blocks = []
    sources: List[LocationSource] = []
    for idx, result in enumerate(search_results):
        url = result.get("url")
        if not url:
            continue
        content = ""
        if reader_limit and idx < reader_limit:
            try:
                content = _jina_read(
                    url=url,
                    timeout=timeout,
                    max_chars=reader_chars,
                    reader_url=reader_url,
                )
            except requests.RequestException:
                content = ""

        title = result.get("title") or url
        sources.append({"title": title, "url": url})
        snippet = result.get("snippet") or ""
        if content:
            source_blocks.append(
                f"Title: {title}\nURL: {url}\nSnippet: {snippet}\nContent: {content}"
            )
        else:
            source_blocks.append(f"Title: {title}\nURL: {url}\nSnippet: {snippet}")

    if not source_blocks:
        return None

    prompt = (
        "Use the sources below to extract the event location info. "
        "Return JSON only with place_name, city, province, country, google_maps_url, "
        "latitude, longitude, confidence (0-1), sources (title + url). "
        "Use English names for city/province when possible. "
        "If unsure, lower confidence. Set google_maps_url to null.\n\n"
        f"Event context: {context}\n"
        f"Query: {query}\n\n"
        f"Sources:\n{chr(10).join(source_blocks)}"
    )

    client = _get_gemini_client()
    config = types.GenerateContentConfig(
        temperature=0,
        responseSchema=LocationResult,
    )
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=config,
        )
    except errors.ClientError as exc:
        status = getattr(exc, "status", "") or ""
        message = str(exc)
        if status == "RESOURCE_EXHAUSTED" or "quota" in message.lower():
            raise RateLimitError(message) from exc
        raise

    if not response.text:
        return None

    try:
        parsed = json.loads(response.text)
    except json.JSONDecodeError:
        text = response.text.strip()
        if "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}")
            snippet = text[start : end + 1]
            try:
                parsed = json.loads(snippet)
            except json.JSONDecodeError:
                return None
        else:
            return None

    if isinstance(parsed, dict):
        parsed["sources"] = sources
        return parsed
    return None

def _build_query(event: Dict[str, Any], artist_name: Optional[str]) -> Optional[str]:
    parts: List[str] = []
    for key in ("venue", "event_name", "city", "province"):
        value = event.get(key)
        if value:
            parts.append(str(value))

    if artist_name:
        parts.append(str(artist_name))

    country = event.get("country") or "Thailand"
    parts.append(str(country))

    if not parts:
        return None

    query = " ".join(parts)
    query = " ".join(query.split())
    return query or None


def _build_maps_query(event: Dict[str, Any]) -> Optional[str]:
    parts: List[str] = []
    for key in ("venue", "event_name", "city", "province", "country"):
        value = event.get(key)
        if value:
            parts.append(str(value))
    query = " ".join(parts)
    query = " ".join(query.split())
    return query or None


def _country_code(country: Optional[str]) -> Optional[str]:
    if not country:
        return None
    normalized = str(country).strip().lower()
    mapping = {
        "thailand": "th",
        "thai": "th",
        "cambodia": "kh",
        "laos": "la",
        "malaysia": "my",
        "vietnam": "vn",
        "myanmar": "mm",
    }
    return mapping.get(normalized)


def _osm_lookup(
    query: str,
    user_agent: str,
    country_code: Optional[str],
    language: str,
    timeout: float,
) -> Optional[LocationResult]:
    params = {
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": 1,
        "accept-language": language,
    }
    if country_code:
        params["countrycodes"] = country_code

    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params=params,
        headers={"User-Agent": user_agent},
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    if not data:
        return None

    item = data[0]
    address = item.get("address", {}) if isinstance(item, dict) else {}
    place_name = item.get("name") or item.get("display_name")
    if place_name and "," in place_name:
        place_name = place_name.split(",")[0].strip()

    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("county")
        or address.get("state_district")
    )
    province = address.get("state") or address.get("region") or address.get("province")
    country = address.get("country")
    lat = item.get("lat")
    lon = item.get("lon")
    importance = item.get("importance")
    confidence = 0.0
    if isinstance(importance, (int, float)):
        confidence = float(importance)
    else:
        confidence = 0.7 if city or province else 0.5

    if city and province:
        confidence = max(confidence, 0.7)
    elif city or province:
        confidence = max(confidence, 0.6)

    search_url = response.url
    return {
        "place_name": place_name,
        "city": city,
        "province": province,
        "country": country,
        "google_maps_url": None,
        "latitude": float(lat) if lat else None,
        "longitude": float(lon) if lon else None,
        "confidence": confidence,
        "sources": [
            {
                "title": "OpenStreetMap Nominatim",
                "url": search_url,
            }
        ],
    }


def _build_maps_url(query: str) -> Optional[str]:
    query = " ".join(str(query).split())
    if not query:
        return None
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


def _is_valid_maps_url(url: Optional[str]) -> bool:
    if not url:
        return False
    text = str(url).strip().lower()
    if not text.startswith("http"):
        return False
    if "maps" not in text:
        return False
    if "222222" in text or "placeholder" in text:
        return False
    return True


def _apply_grounding(
    event: Dict[str, Any],
    result: LocationResult,
    query: str,
    min_confidence: float,
    overwrite: bool,
    source_label: str,
) -> bool:
    confidence = result.get("confidence", 0) or 0
    if confidence < min_confidence:
        event["grounding"] = {
            "source": source_label,
            "query": query,
            "confidence": confidence,
            "sources": result.get("sources", []),
            "place_name": result.get("place_name"),
            "google_maps_url": result.get("google_maps_url"),
            "status": "low_confidence",
        }
        return False

    if overwrite or not event.get("city"):
        event["city"] = result.get("city") or event.get("city")
    if overwrite or not event.get("province"):
        event["province"] = result.get("province") or event.get("province")
    if overwrite or not event.get("country"):
        event["country"] = result.get("country") or event.get("country")
    place_name = result.get("place_name")
    if overwrite or not event.get("venue"):
        if place_name and place_name not in {result.get("city"), result.get("province")}:
            event["venue"] = place_name

    maps_url = result.get("google_maps_url")
    if not _is_valid_maps_url(maps_url):
        fallback_query = (
            result.get("place_name")
            or event.get("venue")
            or event.get("event_name")
            or event.get("city")
            or event.get("province")
            or query
        )
        maps_url = _build_maps_url(fallback_query)

    if maps_url and (overwrite or not event.get("google_maps_url")):
        event["google_maps_url"] = maps_url

    event["grounding"] = {
        "source": source_label,
        "query": query,
        "confidence": confidence,
        "sources": result.get("sources", []),
        "place_name": result.get("place_name"),
        "google_maps_url": maps_url,
        "latitude": result.get("latitude"),
        "longitude": result.get("longitude"),
        "status": "applied",
    }
    return True


def ground_tour_data(
    data: Dict[str, Any],
    cache_path: Optional[Path] = None,
    min_confidence: float = 0.6,
    overwrite: bool = False,
    max_events: Optional[int] = None,
    source: str = "osm",
    osm_user_agent: Optional[str] = None,
    osm_delay: float = 1.0,
    osm_language: str = "en",
    osm_timeout: float = 10.0,
    jina_mode: str = "search",
    jina_top_k: int = 1,
    jina_reader_chars: int = 400,
    jina_timeout: float = 35.0,
    jina_search_url: Optional[str] = None,
    jina_reader_url: Optional[str] = None,
) -> Dict[str, Any]:
    jina_search_url = jina_search_url or JINA_SEARCH_URL
    jina_reader_url = jina_reader_url or JINA_READER_URL
    cache = _load_cache(cache_path)
    events = data.get("events") or []
    artist_name = data.get("artist_name")
    processed = 0
    last_request_time = 0.0

    for event in events:
        if max_events is not None and processed >= max_events:
            break

        if not overwrite and event.get("city") and event.get("province"):
            continue

        query = _build_query(event, artist_name)
        if not query:
            continue

        context_parts = []
        for key in ("event_name", "venue", "date", "city", "province", "country"):
            value = event.get(key)
            if value:
                context_parts.append(f"{key}: {value}")
        if artist_name:
            context_parts.append(f"artist_name: {artist_name}")
        context = "; ".join(context_parts) if context_parts else "No extra context."

        if source == "jina":
            source_key = f"jina:{jina_mode}:{jina_top_k}:{jina_reader_chars}"
        else:
            source_key = source
        cache_key = f"{source_key}:{query}"
        cached = cache.get(cache_key)
        if cached:
            result = cached.get("result")
            if source == "osm" and result:
                confidence = result.get("confidence", 0) or 0
                if confidence < min_confidence:
                    fallback = " ".join(
                        str(part)
                        for part in (
                            event.get("city"),
                            event.get("province"),
                            event.get("country") or "Thailand",
                        )
                        if part
                    )
                    fallback = " ".join(fallback.split())
                    if fallback and fallback != query:
                        fallback_key = f"{source}:{fallback}"
                        fallback_cached = cache.get(fallback_key, {})
                        fallback_result = fallback_cached.get("result")
                        if not fallback_result:
                            elapsed = time.monotonic() - last_request_time
                            if elapsed < osm_delay:
                                time.sleep(osm_delay - elapsed)
                            try:
                                fallback_result = _osm_lookup(
                                    query=fallback,
                                    user_agent=osm_user_agent
                                    or os.getenv("OSM_USER_AGENT")
                                    or "ArtistCalendar/0.1",
                                    country_code=_country_code(event.get("country")),
                                    language=osm_language,
                                    timeout=osm_timeout,
                                )
                            except requests.RequestException as exc:
                                logging.warning(
                                    "OSM lookup failed for query %s: %s",
                                    fallback,
                                    exc,
                                )
                                fallback_result = None
                            last_request_time = time.monotonic()
                            cache[fallback_key] = {"result": fallback_result}
                            _save_cache(cache_path, cache)
                        if fallback_result:
                            fallback_conf = fallback_result.get("confidence", 0) or 0
                            if fallback_conf > confidence:
                                result = fallback_result
                                cache[cache_key] = {"result": result}
                                _save_cache(cache_path, cache)
        else:
            if source == "jina":
                try:
                    result = _jina_ground_location(
                        query=query,
                        context=context,
                        top_k=jina_top_k,
                        reader_chars=jina_reader_chars,
                        timeout=jina_timeout,
                        search_url=jina_search_url,
                        reader_url=jina_reader_url,
                        mode=jina_mode,
                    )
                except RateLimitError as exc:
                    event["grounding"] = {
                        "source": "jina",
                        "query": query,
                        "confidence": 0,
                        "sources": [],
                        "place_name": None,
                        "google_maps_url": None,
                        "status": "rate_limited",
                    }
                    logging.warning("Grounding stopped due to rate limit: %s", exc)
                    break
                except requests.RequestException as exc:
                    logging.warning("Jina lookup failed for query %s: %s", query, exc)
                    result = None
            else:
                elapsed = time.monotonic() - last_request_time
                if elapsed < osm_delay:
                    time.sleep(osm_delay - elapsed)
                try:
                    user_agent = (
                        osm_user_agent
                        or os.getenv("OSM_USER_AGENT")
                        or "ArtistCalendar/0.1"
                    )
                    country_code = _country_code(event.get("country"))
                    result = _osm_lookup(
                        query=query,
                        user_agent=user_agent,
                        country_code=country_code,
                        language=osm_language,
                        timeout=osm_timeout,
                    )
                    if not result or (result.get("confidence", 0) or 0) < min_confidence:
                        fallback = " ".join(
                            str(part)
                            for part in (
                                event.get("city"),
                                event.get("province"),
                                event.get("country") or "Thailand",
                            )
                            if part
                        )
                        fallback = " ".join(fallback.split())
                        if fallback and fallback != query:
                            result = _osm_lookup(
                                query=fallback,
                                user_agent=user_agent,
                                country_code=country_code,
                                language=osm_language,
                                timeout=osm_timeout,
                            )
                except requests.RequestException as exc:
                    logging.warning("OSM lookup failed for query %s: %s", query, exc)
                    result = None
                last_request_time = time.monotonic()

            cache[cache_key] = {"result": result}
            _save_cache(cache_path, cache)

        if result:
            applied = _apply_grounding(
                event,
                result,
                query,
                min_confidence=min_confidence,
                overwrite=overwrite,
                source_label=source,
            )
            if applied:
                processed += 1
        else:
            event["grounding"] = {
                "source": source,
                "query": query,
                "confidence": 0,
                "sources": [],
                "place_name": None,
                "google_maps_url": None,
                "status": "not_found",
            }

        if not event.get("google_maps_url"):
            maps_query = _build_maps_query(event)
            if maps_query:
                event["google_maps_url"] = _build_maps_url(maps_query)

    data["events"] = events
    return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich tour data with location grounding."
    )
    parser.add_argument("input", help="Path to structured JSON input.")
    parser.add_argument("--output", help="Path to write enriched JSON.")
    parser.add_argument(
        "--cache",
        default="output/grounding_cache.json",
        help="Path to grounding cache JSON.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.6,
        help="Minimum confidence to apply grounded data.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing city/province/country/venue values.",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        help="Max number of events to ground (useful for quick tests).",
    )
    parser.add_argument(
        "--source",
        choices=["osm", "jina"],
        default="osm",
        help="Grounding source to use.",
    )
    parser.add_argument(
        "--osm-user-agent",
        help="User-Agent for OSM Nominatim requests. Also reads OSM_USER_AGENT env.",
    )
    parser.add_argument(
        "--osm-delay",
        type=float,
        default=1.0,
        help="Minimum delay in seconds between OSM requests.",
    )
    parser.add_argument(
        "--osm-language",
        default="en",
        help="OSM response language (accept-language).",
    )
    parser.add_argument(
        "--osm-timeout",
        type=float,
        default=10.0,
        help="Timeout in seconds for OSM requests.",
    )
    parser.add_argument(
        "--jina-top-k",
        type=int,
        default=1,
        help="Number of Jina search results to use.",
    )
    parser.add_argument(
        "--jina-mode",
        choices=["search", "reader", "hybrid"],
        default="search",
        help="Jina grounding mode (search-only, reader, or hybrid).",
    )
    parser.add_argument(
        "--jina-reader-chars",
        type=int,
        default=400,
        help="Max characters to keep from each Jina reader result.",
    )
    parser.add_argument(
        "--jina-timeout",
        type=float,
        default=35.0,
        help="Timeout in seconds for Jina requests.",
    )
    parser.add_argument(
        "--jina-search-url",
        default=JINA_SEARCH_URL,
        help="Override Jina search endpoint (supports {query}).",
    )
    parser.add_argument(
        "--jina-reader-url",
        default=JINA_READER_URL,
        help="Override Jina reader endpoint (supports {url}).",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    output_path = Path(args.output) if args.output else input_path

    enriched = ground_tour_data(
        data,
        cache_path=Path(args.cache) if args.cache else None,
        min_confidence=args.min_confidence,
        overwrite=args.overwrite,
        max_events=args.max_events,
        source=args.source,
        osm_user_agent=args.osm_user_agent,
        osm_delay=args.osm_delay,
        osm_language=args.osm_language,
        osm_timeout=args.osm_timeout,
        jina_mode=args.jina_mode,
        jina_top_k=args.jina_top_k,
        jina_reader_chars=args.jina_reader_chars,
        jina_timeout=args.jina_timeout,
        jina_search_url=args.jina_search_url,
        jina_reader_url=args.jina_reader_url,
    )

    _ensure_parent_dir(output_path)
    output_path.write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
