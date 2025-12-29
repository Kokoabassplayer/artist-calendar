import argparse
import json
import re
from typing import Optional, List
from typing_extensions import TypedDict

from google import genai
from google.genai import types

from config import Config


class TourEvent(TypedDict):
    date: str
    event_name: Optional[str]
    venue: Optional[str]
    city: Optional[str]
    province: Optional[str]
    country: str
    time: Optional[str]
    ticket_info: Optional[str]
    status: str


class TourData(TypedDict):
    artist_name: str
    instagram_handle: Optional[str]
    tour_name: Optional[str]
    contact_info: Optional[str]
    source_month: str
    events: List[TourEvent]


if not Config.GEMINI_API_KEY:
    raise SystemExit("GEMINI_API_KEY not set.")

CLIENT = genai.Client(api_key=Config.GEMINI_API_KEY)
MODEL_NAME = "models/gemini-flash-latest"


def upload_to_gemini(path: str, mime_type: Optional[str] = None):
    try:
        config = types.UploadFileConfig(mimeType=mime_type) if mime_type else None
        return CLIENT.files.upload(file=path, config=config)
    except Exception as exc:
        raise SystemExit(f"Error uploading file: {exc}") from exc


_MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def _extract_year(text: str) -> Optional[int]:
    match = re.search(r"(20\d{2})", text)
    if match:
        return int(match.group(1))
    return None


def _extract_month(text: str) -> Optional[int]:
    lowered = text.lower()
    for name, month in _MONTHS.items():
        if re.search(rf"\b{re.escape(name)}\b", lowered):
            return month
    return None


def _normalize_source_month(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None

    match = re.match(r"^(\d{4})[-_/](\d{1,2})$", text)
    if match:
        year, month = match.groups()
        return f"{int(year):04d}-{int(month):02d}"

    match = re.match(r"^(\d{4})(\d{2})$", text)
    if match:
        year, month = match.groups()
        return f"{int(year):04d}-{int(month):02d}"

    year = _extract_year(text)
    month = _extract_month(text)
    if year and month:
        return f"{year:04d}-{month:02d}"
    return None


def _normalize_status(value: Optional[str]) -> str:
    if not value:
        return "active"
    text = str(value).strip().lower()
    if text in {"active", "cancelled", "postponed"}:
        return text
    if "cancel" in text:
        return "cancelled"
    if "postpon" in text:
        return "postponed"
    if "confirm" in text or "scheduled" in text:
        return "active"
    return "active"


def _normalize_time(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None

    match = re.search(r"(\d{1,2})[:\.](\d{2})", text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if "pm" in text and hour < 12:
            hour += 12
        if "am" in text and hour == 12:
            hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"

    match = re.search(r"\b(\d{1,2})\b", text)
    if match:
        hour = int(match.group(1))
        if "pm" in text and hour < 12:
            hour += 12
        if "am" in text and hour == 12:
            hour = 0
        if 0 <= hour <= 23:
            return f"{hour:02d}:00"

    return None


def _normalize_date(value: Optional[str], source_month: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    match = re.match(r"^(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})$", text)
    if match:
        year, month, day = map(int, match.groups())
        return f"{year:04d}-{month:02d}-{day:02d}"

    match = re.match(r"^(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{2,4})$", text)
    if match:
        day, month, year = match.groups()
        year = int(year)
        if year < 100:
            year += 2000
        return f"{year:04d}-{int(month):02d}-{int(day):02d}"

    match = re.match(r"^(\d{1,2})[-/\.](\d{1,2})$", text)
    if match:
        day, month = map(int, match.groups())
        year = None
        if source_month:
            year = int(source_month.split("-")[0])
        if year:
            return f"{year:04d}-{month:02d}-{day:02d}"

    match = re.match(r"^(\d{1,2})\s*([A-Za-z]+)\s*,?\s*(\d{4})?$", text)
    if match:
        day = int(match.group(1))
        month = _MONTHS.get(match.group(2).lower())
        year = match.group(3)
        if month:
            if year:
                return f"{int(year):04d}-{month:02d}-{day:02d}"
            if source_month:
                year = int(source_month.split("-")[0])
                return f"{year:04d}-{month:02d}-{day:02d}"

    match = re.match(r"^([A-Za-z]+)\s*(\d{1,2})\s*,?\s*(\d{4})?$", text)
    if match:
        month = _MONTHS.get(match.group(1).lower())
        day = int(match.group(2))
        year = match.group(3)
        if month:
            if year:
                return f"{int(year):04d}-{month:02d}-{day:02d}"
            if source_month:
                year = int(source_month.split("-")[0])
                return f"{year:04d}-{month:02d}-{day:02d}"

    match = re.match(r"^(\d{1,2})$", text)
    if match and source_month:
        day = int(match.group(1))
        year, month = source_month.split("-")
        return f"{int(year):04d}-{int(month):02d}-{day:02d}"

    return None


def _normalize_tour_data(data: dict) -> dict:
    source_month = _normalize_source_month(data.get("source_month"))
    if source_month:
        data["source_month"] = source_month

    events = data.get("events") or []
    normalized_events = []
    for event in events:
        if not isinstance(event, dict):
            continue
        raw_date = event.get("date")
        raw_time = event.get("time")

        if "date_text" not in event:
            event["date_text"] = raw_date
        if "time_text" not in event:
            event["time_text"] = raw_time

        event["date"] = _normalize_date(raw_date, source_month)
        event["time"] = _normalize_time(raw_time)
        event["status"] = _normalize_status(event.get("status"))

        if not event.get("country"):
            event["country"] = "Thailand"

        normalized_events.append(event)

    data["events"] = normalized_events
    return data


def image_to_structured(image_path: str) -> TourData:
    config = types.GenerateContentConfig(
        temperature=0,
        responseMimeType="application/json",
        responseSchema=TourData,
        systemInstruction=(
            "Extract structured tour data from the image. "
            "Return JSON only and follow the schema exactly. "
            "Always use YYYY-MM for source_month and YYYY-MM-DD for event dates. "
            "If only day is shown, infer month/year from the poster context."
        ),
    )

    uploaded_file = upload_to_gemini(image_path, mime_type="image/jpeg")
    response = CLIENT.models.generate_content(
        model=MODEL_NAME,
        contents=[uploaded_file, "extract"],
        config=config,
    )
    data = json.loads(response.text or "{}")
    if isinstance(data, dict):
        return _normalize_tour_data(data)
    return data


def main():
    parser = argparse.ArgumentParser(
        description="Extract structured tour data from a single image."
    )
    parser.add_argument("image", help="Path to the tour date image.")
    parser.add_argument(
        "--output",
        help="Optional path to save JSON output.",
    )
    parser.add_argument(
        "--ground",
        action="store_true",
        help="Use location grounding to enrich city/province/venue.",
    )
    parser.add_argument(
        "--ground-cache",
        default="output/grounding_cache.json",
        help="Path to grounding cache JSON.",
    )
    parser.add_argument(
        "--ground-min-confidence",
        type=float,
        default=0.6,
        help="Minimum confidence to apply grounded data.",
    )
    parser.add_argument(
        "--ground-overwrite",
        action="store_true",
        help="Overwrite existing city/province/country/venue values.",
    )
    parser.add_argument(
        "--ground-max-events",
        type=int,
        help="Max number of events to ground (useful for quick tests).",
    )
    parser.add_argument(
        "--ground-source",
        choices=["osm", "jina"],
        default="osm",
        help="Grounding source to use.",
    )
    parser.add_argument(
        "--ground-osm-user-agent",
        help="User-Agent for OSM Nominatim requests.",
    )
    parser.add_argument(
        "--ground-osm-delay",
        type=float,
        default=1.0,
        help="Minimum delay in seconds between OSM requests.",
    )
    parser.add_argument(
        "--ground-osm-language",
        default="en",
        help="OSM response language (accept-language).",
    )
    parser.add_argument(
        "--ground-osm-timeout",
        type=float,
        default=10.0,
        help="Timeout in seconds for OSM requests.",
    )
    parser.add_argument(
        "--ground-jina-top-k",
        type=int,
        default=1,
        help="Number of Jina search results to use.",
    )
    parser.add_argument(
        "--ground-jina-mode",
        choices=["search", "reader", "hybrid"],
        default="search",
        help="Jina grounding mode (search-only, reader, or hybrid).",
    )
    parser.add_argument(
        "--ground-jina-reader-chars",
        type=int,
        default=400,
        help="Max characters to keep from each Jina reader result.",
    )
    parser.add_argument(
        "--ground-jina-timeout",
        type=float,
        default=35.0,
        help="Timeout in seconds for Jina requests.",
    )
    parser.add_argument(
        "--ground-jina-search-url",
        help="Override Jina search endpoint (supports {query}).",
    )
    parser.add_argument(
        "--ground-jina-reader-url",
        help="Override Jina reader endpoint (supports {url}).",
    )
    args = parser.parse_args()

    data = image_to_structured(args.image)
    if args.ground:
        from location_grounding import ground_tour_data
        from pathlib import Path

        data = ground_tour_data(
            data,
            cache_path=Path(args.ground_cache) if args.ground_cache else None,
            min_confidence=args.ground_min_confidence,
            overwrite=args.ground_overwrite,
            max_events=args.ground_max_events,
            source=args.ground_source,
            osm_user_agent=args.ground_osm_user_agent,
            osm_delay=args.ground_osm_delay,
            osm_language=args.ground_osm_language,
            osm_timeout=args.ground_osm_timeout,
            jina_mode=args.ground_jina_mode,
            jina_top_k=args.ground_jina_top_k,
            jina_reader_chars=args.ground_jina_reader_chars,
            jina_timeout=args.ground_jina_timeout,
            jina_search_url=(
                args.ground_jina_search_url if args.ground_jina_search_url else None
            ),
            jina_reader_url=(
                args.ground_jina_reader_url if args.ground_jina_reader_url else None
            ),
        )
    output = json.dumps(data, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)

    print(output)


if __name__ == "__main__":
    main()
