#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


def _load_env() -> Dict[str, str]:
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        raise SystemExit(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY)."
        )
    return {"url": url.rstrip("/"), "key": key}


def _request(
    base_url: str,
    key: str,
    method: str,
    path: str,
    params: Optional[Dict[str, str]] = None,
    payload: Optional[Any] = None,
    prefer: Optional[str] = None,
) -> Any:
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    url = f"{base_url}{path}"
    response = requests.request(
        method, url, params=params, json=payload, headers=headers, timeout=30
    )
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {url} failed: {response.status_code} {response.text}")
    if not response.text:
        return None
    return response.json()


def _upsert(
    base_url: str,
    key: str,
    table: str,
    payload: Dict[str, Any],
    on_conflict: Optional[str] = None,
) -> Dict[str, Any]:
    params = {"on_conflict": on_conflict} if on_conflict else None
    rows = _request(
        base_url,
        key,
        "POST",
        f"/rest/v1/{table}",
        params=params,
        payload=payload,
        prefer="return=representation,resolution=merge-duplicates",
    )
    if isinstance(rows, list) and rows:
        return rows[0]
    if isinstance(rows, dict):
        return rows
    raise RuntimeError(f"Unexpected upsert response for {table}: {rows}")


def _insert(
    base_url: str,
    key: str,
    table: str,
    payload: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows = _request(
        base_url,
        key,
        "POST",
        f"/rest/v1/{table}",
        payload=payload,
        prefer="return=representation",
    )
    if isinstance(rows, list):
        return rows
    if isinstance(rows, dict):
        return [rows]
    return []


def _select(
    base_url: str,
    key: str,
    table: str,
    params: Dict[str, str],
) -> List[Dict[str, Any]]:
    rows = _request(base_url, key, "GET", f"/rest/v1/{table}", params=params)
    return rows if isinstance(rows, list) else []


def _patch(
    base_url: str,
    key: str,
    table: str,
    params: Dict[str, str],
    payload: Dict[str, Any],
) -> None:
    _request(
        base_url,
        key,
        "PATCH",
        f"/rest/v1/{table}",
        params=params,
        payload=payload,
        prefer="return=representation",
    )


def _find_latest_posters(base_url: str, key: str, artist_id: str, source_month: str):
    params = {
        "select": "id,version",
        "artist_id": f"eq.{artist_id}",
        "source_month": f"eq.{source_month}",
        "is_latest": "eq.true",
    }
    return _select(base_url, key, "posters", params)


def _build_image_url(data: Dict[str, Any], fallback: str) -> str:
    return (
        data.get("image_url")
        or data.get("source_image")
        or data.get("source_image_path")
        or fallback
    )


def ingest_structured(
    input_path: Path,
    image_url: Optional[str],
    source_type: str,
    source_url: Optional[str],
) -> None:
    env = _load_env()
    base_url = env["url"]
    key = env["key"]

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    artist_name = payload.get("artist_name")
    if not artist_name:
        raise SystemExit("artist_name is required in the structured JSON.")

    instagram_handle = payload.get("instagram_handle")
    contact_info = payload.get("contact_info")

    artist_row = _upsert(
        base_url,
        key,
        "artists",
        {
            "name": artist_name,
            "instagram_handle": instagram_handle,
            "contact_info": contact_info,
        },
        on_conflict="instagram_handle" if instagram_handle else None,
    )

    artist_id = artist_row["id"]
    source_month = payload.get("source_month") or "unknown"
    tour_name = payload.get("tour_name")

    image_url_value = image_url or _build_image_url(payload, fallback=str(input_path))

    latest_posters = _find_latest_posters(base_url, key, artist_id, source_month)
    next_version = 1
    for poster in latest_posters:
        next_version = max(next_version, (poster.get("version") or 1) + 1)
        _patch(
            base_url,
            key,
            "posters",
            {"id": f"eq.{poster['id']}"},
            {"is_latest": False},
        )

    poster_row = _upsert(
        base_url,
        key,
        "posters",
        {
            "artist_id": artist_id,
            "image_url": image_url_value,
            "tour_name": tour_name,
            "source_month": source_month,
            "source_type": source_type,
            "source_url": source_url,
            "version": next_version,
            "is_latest": True,
            "raw_json": payload,
            "extraction_status": "success",
        },
    )

    poster_id = poster_row["id"]
    events = payload.get("events") or []
    event_rows = []
    for event in events:
        if not event.get("date"):
            continue
        event_rows.append(
            {
                "poster_id": poster_id,
                "date": event.get("date"),
                "date_text": event.get("date_text"),
                "event_name": event.get("event_name"),
                "venue": event.get("venue"),
                "city": event.get("city"),
                "province": event.get("province"),
                "country": event.get("country") or "Thailand",
                "time": event.get("time"),
                "time_text": event.get("time_text"),
                "ticket_info": event.get("ticket_info"),
                "status": event.get("status") or "active",
                "review_status": "pending",
            }
        )

    if event_rows:
        _insert(base_url, key, "events", event_rows)

    print(
        f"Inserted artist={artist_name}, poster={poster_id}, events={len(event_rows)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest structured tour JSON into Supabase."
    )
    parser.add_argument("input", help="Path to structured JSON file.")
    parser.add_argument(
        "--image-url",
        help="Poster image URL (required if JSON has no source_image).",
    )
    parser.add_argument(
        "--source-type",
        default="manual",
        choices=["manual", "instagram", "facebook", "website"],
        help="Source type for the poster.",
    )
    parser.add_argument(
        "--source-url",
        help="Original source URL (Instagram post, etc.).",
    )
    args = parser.parse_args()

    ingest_structured(
        Path(args.input),
        image_url=args.image_url,
        source_type=args.source_type,
        source_url=args.source_url,
    )


if __name__ == "__main__":
    main()
