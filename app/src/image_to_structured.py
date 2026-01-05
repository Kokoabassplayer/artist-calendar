import argparse
import json
import mimetypes
import re
from pathlib import Path
from typing import Optional, List, TypedDict

from google import genai
from google.genai import errors, types

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
    confidence: Optional[float]


class TourData(TypedDict):
    artist_name: str
    instagram_handle: Optional[str]
    tour_name: Optional[str]
    contact_info: Optional[str]
    source_month: str
    poster_confidence: Optional[float]
    events: List[TourEvent]


_CLIENT: Optional[genai.Client] = None
MODEL_NAME = Config.GEMINI_MODEL
REPAIR_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "refine_missing_fields.txt"
SYSTEM_INSTRUCTION = (
    "Extract structured tour data from the image. "
    "Return JSON only and follow the schema exactly. "
    "Keep text as close to the original as possible. "
    "You may fix obvious OCR typos or missing spaces, but do not translate, "
    "expand abbreviations, or invent new info. "
    "Always use YYYY-MM for source_month and YYYY-MM-DD for event dates. "
    "If only day is shown, infer month/year from the poster context. "
    "Set event confidence and poster_confidence between 0 and 1. "
    "Use higher values for clearer text and complete fields, lower values for "
    "uncertain or incomplete entries, and vary them across events. "
    "Do not include any *_raw, raw_text, date_text, or time_text fields."
)
SCHEMA_HINT = (
    "Schema:\n"
    "{\n"
    '  "artist_name": "string",\n'
    '  "instagram_handle": "string|null",\n'
    '  "tour_name": "string|null",\n'
    '  "contact_info": "string|null",\n'
    '  "source_month": "YYYY-MM",\n'
    '  "poster_confidence": "number 0-1 or null",\n'
    '  "events": [\n'
    "    {\n"
    '      "date": "YYYY-MM-DD",\n'
    '      "event_name": "string|null",\n'
    '      "venue": "string|null",\n'
    '      "city": "string|null",\n'
    '      "province": "string|null",\n'
    '      "country": "string",\n'
    '      "time": "string|null",\n'
    '      "ticket_info": "string|null",\n'
    '      "status": "string",\n'
    '      "confidence": "number 0-1 or null"\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "Return only JSON with these exact keys."
)


def _get_client() -> genai.Client:
    global _CLIENT
    if _CLIENT is None:
        if not Config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not set.")
        _CLIENT = genai.Client(api_key=Config.GEMINI_API_KEY)
    return _CLIENT


def upload_to_gemini(path: str, mime_type: Optional[str] = None):
    try:
        client = _get_client()
        config = types.UploadFileConfig(mimeType=mime_type) if mime_type else None
        return client.files.upload(file=path, config=config)
    except Exception as exc:
        raise RuntimeError(f"Error uploading file: {exc}") from exc


def _guess_mime_type(path: str) -> Optional[str]:
    mime_type, _ = mimetypes.guess_type(path)
    return mime_type


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

_THAI_PROVINCES = {
    "กรุงเทพมหานคร",
    "กระบี่",
    "กาญจนบุรี",
    "กาฬสินธุ์",
    "กำแพงเพชร",
    "ขอนแก่น",
    "จันทบุรี",
    "ฉะเชิงเทรา",
    "ชลบุรี",
    "ชัยนาท",
    "ชัยภูมิ",
    "ชุมพร",
    "เชียงราย",
    "เชียงใหม่",
    "ตรัง",
    "ตราด",
    "ตาก",
    "นครนายก",
    "นครปฐม",
    "นครพนม",
    "นครราชสีมา",
    "นครศรีธรรมราช",
    "นครสวรรค์",
    "นนทบุรี",
    "นราธิวาส",
    "น่าน",
    "บึงกาฬ",
    "บุรีรัมย์",
    "ปทุมธานี",
    "ประจวบคีรีขันธ์",
    "ปราจีนบุรี",
    "ปัตตานี",
    "พะเยา",
    "พระนครศรีอยุธยา",
    "พังงา",
    "พัทลุง",
    "พิจิตร",
    "พิษณุโลก",
    "เพชรบุรี",
    "เพชรบูรณ์",
    "แพร่",
    "ภูเก็ต",
    "มหาสารคาม",
    "มุกดาหาร",
    "แม่ฮ่องสอน",
    "ยะลา",
    "ยโสธร",
    "ระนอง",
    "ระยอง",
    "ราชบุรี",
    "ร้อยเอ็ด",
    "ลพบุรี",
    "ลำปาง",
    "ลำพูน",
    "เลย",
    "ศรีสะเกษ",
    "สกลนคร",
    "สงขลา",
    "สตูล",
    "สมุทรปราการ",
    "สมุทรสงคราม",
    "สมุทรสาคร",
    "สระแก้ว",
    "สระบุรี",
    "สิงห์บุรี",
    "สุโขทัย",
    "สุพรรณบุรี",
    "สุราษฎร์ธานี",
    "สุรินทร์",
    "หนองคาย",
    "หนองบัวลำภู",
    "อ่างทอง",
    "อำนาจเจริญ",
    "อุดรธานี",
    "อุตรดิตถ์",
    "อุทัยธานี",
    "อุบลราชธานี",
}

_RAW_EVENT_KEYS = {"raw_text", "date_text", "time_text"}


def _strip_raw_fields(data: dict) -> dict:
    cleaned = {key: value for key, value in data.items() if not key.endswith("_raw")}
    events = cleaned.get("events") or []
    cleaned_events = []
    for event in events:
        if not isinstance(event, dict):
            continue
        cleaned_event = {
            key: value
            for key, value in event.items()
            if not key.endswith("_raw") and key not in _RAW_EVENT_KEYS
        }
        cleaned_events.append(cleaned_event)
    cleaned["events"] = cleaned_events
    return cleaned


def _split_city_province(value: str) -> Optional[tuple[str, str]]:
    cleaned = value.strip()
    if not cleaned:
        return None
    for province in _THAI_PROVINCES:
        if cleaned.endswith(province) and len(cleaned) > len(province):
            city = cleaned[: -len(province)].strip(" -/|,")
            if city:
                return city, province
    return None


def _normalize_location_fields(event: dict) -> None:
    city = (event.get("city") or "").strip()
    province = (event.get("province") or "").strip()

    if not province and city in _THAI_PROVINCES:
        event["province"] = city

    if not event.get("province") and city:
        split = _split_city_province(city)
        if split:
            event["city"] = split[0]
            event["province"] = split[1]


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
    data = _strip_raw_fields(data)
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

        _normalize_location_fields(event)

        event["date"] = _normalize_date(raw_date, source_month)
        event["time"] = _normalize_time(raw_time)
        event["status"] = _normalize_status(event.get("status"))

        if not event.get("country"):
            event["country"] = "Thailand"

        confidence = event.get("confidence")
        try:
            if confidence is None:
                event["confidence"] = None
            else:
                value = float(confidence)
                if value < 0:
                    value = 0.0
                if value > 1:
                    value = 1.0
                event["confidence"] = round(value, 3)
        except (TypeError, ValueError):
            event["confidence"] = None
        normalized_events.append(event)

    data["events"] = normalized_events
    poster_conf = data.get("poster_confidence")
    try:
        if poster_conf is None:
            data["poster_confidence"] = None
        else:
            value = float(poster_conf)
            if value < 0:
                value = 0.0
            if value > 1:
                value = 1.0
            data["poster_confidence"] = round(value, 3)
    except (TypeError, ValueError):
        data["poster_confidence"] = None
    return data


def _is_instruction_error(exc: Exception) -> bool:
    return "Developer instruction is not enabled" in str(exc)


def _is_json_mode_error(exc: Exception) -> bool:
    return "JSON mode is not enabled" in str(exc)


def _build_config(system_instruction: str | None, structured: bool) -> types.GenerateContentConfig:
    config = types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=8192,
    )
    if structured:
        config.response_mime_type = "application/json"
        config.response_schema = TourData
    if system_instruction:
        config.system_instruction = system_instruction
    return config


def _generate_content(
    client: genai.Client,
    contents: list,
    system_instruction: str,
    *,
    structured: bool,
    inline_instruction: bool,
) -> object:
    if inline_instruction:
        contents = [system_instruction, *contents]
        system_instruction = ""
    config = _build_config(system_instruction or None, structured=structured)
    return client.models.generate_content(
        model=MODEL_NAME,
        contents=contents,
        config=config,
    )


def _generate_with_instruction(contents: list, system_instruction: str) -> object:
    client = _get_client()
    fallback_instruction = f"{system_instruction}\n\n{SCHEMA_HINT}"
    try:
        return _generate_content(
            client,
            contents,
            system_instruction,
            structured=True,
            inline_instruction=False,
        )
    except Exception as exc:
        if _is_instruction_error(exc):
            try:
                return _generate_content(
                    client,
                    contents,
                    fallback_instruction,
                    structured=True,
                    inline_instruction=True,
                )
            except Exception as inner_exc:
                if _is_json_mode_error(inner_exc):
                    return _generate_content(
                        client,
                        contents,
                        fallback_instruction,
                        structured=False,
                        inline_instruction=True,
                    )
                raise
        if _is_json_mode_error(exc):
            try:
                return _generate_content(
                    client,
                    contents,
                    fallback_instruction,
                    structured=False,
                    inline_instruction=False,
                )
            except Exception as inner_exc:
                if _is_instruction_error(inner_exc):
                    return _generate_content(
                        client,
                        contents,
                        fallback_instruction,
                        structured=False,
                        inline_instruction=True,
                    )
                raise
        raise


def _strip_code_fences(text: str) -> str:
    if "```" not in text:
        return text
    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    return cleaned.replace("```", "").strip()


def _parse_json_response(text: str) -> object:
    if not text:
        return {}
    cleaned = _strip_code_fences(text.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                return {}
    return {}


def _has_missing_core_fields(data: dict) -> bool:
    events = data.get("events") or []
    if not isinstance(events, list):
        return True
    for event in events:
        if not isinstance(event, dict):
            return True
        for field in ("date", "venue", "city", "province"):
            value = event.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                return True
    return False


def _repair_missing_core_fields(image_path: str, data: dict) -> Optional[dict]:
    if not REPAIR_PROMPT_PATH.exists():
        return None
    prompt = REPAIR_PROMPT_PATH.read_text(encoding="utf-8")
    mime_type = _guess_mime_type(image_path) or "image/jpeg"
    uploaded_file = upload_to_gemini(image_path, mime_type=mime_type)
    response = _generate_with_instruction(
        [uploaded_file, json.dumps(data, ensure_ascii=False)],
        prompt,
    )
    repaired = _parse_json_response(response.text or "")
    if isinstance(repaired, dict):
        return repaired
    return None


def image_to_structured(image_path: str) -> TourData:
    mime_type = _guess_mime_type(image_path) or "image/jpeg"
    uploaded_file = upload_to_gemini(image_path, mime_type=mime_type)
    response = _generate_with_instruction(
        [uploaded_file, "extract"],
        SYSTEM_INSTRUCTION,
    )
    data = _parse_json_response(response.text or "")
    if isinstance(data, dict):
        normalized = _normalize_tour_data(data)
        if Config.REPAIR_MISSING_CORE and _has_missing_core_fields(normalized):
            repaired = _repair_missing_core_fields(image_path, normalized)
            if isinstance(repaired, dict):
                normalized = _normalize_tour_data(repaired)
        return normalized
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
    args = parser.parse_args()

    data = image_to_structured(args.image)
    output = json.dumps(data, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)

    print(output)


if __name__ == "__main__":
    main()
