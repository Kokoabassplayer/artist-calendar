import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "database" / "schema_local.sql"


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    _ensure_columns(conn)
    return conn


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def _ensure_column(
    conn: sqlite3.Connection, table: str, column: str, ddl: str
) -> None:
    if _column_exists(conn, table, column):
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _ensure_columns(conn: sqlite3.Connection) -> None:
    _ensure_column(conn, "posters", "poster_confidence", "REAL")
    _ensure_column(conn, "posters", "source_post_id", "TEXT")
    _ensure_column(conn, "posters", "image_hash", "TEXT")
    _ensure_column(conn, "events", "confidence", "REAL")
    _ensure_column(conn, "events", "location_type", "TEXT DEFAULT 'public'")


def _build_image_url(data: Dict[str, Any], fallback: str) -> str:
    return (
        data.get("image_url")
        or data.get("source_image")
        or data.get("source_image_path")
        or fallback
    )


def _get_artist_id(
    conn: sqlite3.Connection,
    name: str,
    instagram_handle: Optional[str],
    contact_info: Optional[str],
) -> str:
    if instagram_handle:
        row = conn.execute(
            "SELECT id FROM artists WHERE instagram_handle = ?",
            (instagram_handle,),
        ).fetchone()
    else:
        row = conn.execute("SELECT id FROM artists WHERE name = ?", (name,)).fetchone()

    if row:
        conn.execute(
            "UPDATE artists SET name = ?, contact_info = ?, updated_at = ? WHERE id = ?",
            (name, contact_info, _now(), row["id"]),
        )
        return row["id"]

    artist_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO artists (id, name, instagram_handle, contact_info, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (artist_id, name, instagram_handle, contact_info, _now(), _now()),
    )
    return artist_id


def _insert_poster(
    conn: sqlite3.Connection,
    artist_id: str,
    image_url: str,
    tour_name: Optional[str],
    source_month: str,
    source_type: str,
    source_url: Optional[str],
    source_post_id: Optional[str],
    image_hash: Optional[str],
    poster_confidence: Optional[float],
    raw_json: Dict[str, Any],
) -> str:
    latest_rows = conn.execute(
        """
        SELECT id, version FROM posters
        WHERE artist_id = ? AND source_month = ? AND is_latest = 1
        """,
        (artist_id, source_month),
    ).fetchall()

    next_version = 1
    for row in latest_rows:
        version = row["version"] or 1
        if version + 1 > next_version:
            next_version = version + 1
        conn.execute(
            "UPDATE posters SET is_latest = 0 WHERE id = ?",
            (row["id"],),
        )

    poster_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO posters (
            id, artist_id, image_url, tour_name, source_month, source_type, source_url,
            source_post_id, image_hash, poster_confidence, version, is_latest, raw_json,
            extraction_status, extracted_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            poster_id,
            artist_id,
            image_url,
            tour_name,
            source_month,
            source_type,
            source_url,
            source_post_id,
            image_hash,
            poster_confidence,
            next_version,
            1,
            json.dumps(raw_json, ensure_ascii=False),
            "success",
            _now(),
            _now(),
        ),
    )
    return poster_id


def _insert_events(
    conn: sqlite3.Connection,
    poster_id: str,
    events: List[Dict[str, Any]],
) -> int:
    count = 0
    for event in events:
        if not event.get("date"):
            continue
        event_id = str(uuid.uuid4())
        location_type = event.get("location_type") or "public"
        conn.execute(
            """
            INSERT INTO events (
                id, poster_id, date, date_text, event_name, venue, city, province,
                country, location_type, time, time_text, ticket_info, status,
                review_status, confidence, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                poster_id,
                event.get("date"),
                event.get("date_text"),
                event.get("event_name"),
                event.get("venue"),
                event.get("city"),
                event.get("province"),
                event.get("country") or "Thailand",
                location_type,
                event.get("time"),
                event.get("time_text"),
                event.get("ticket_info"),
                event.get("status") or "active",
                event.get("review_status") or "pending",
                event.get("confidence"),
                _now(),
                _now(),
            ),
        )
        count += 1
    return count


def ingest_structured(
    data: Dict[str, Any],
    db_path: Path,
    image_url: Optional[str] = None,
    source_type: str = "manual",
    source_url: Optional[str] = None,
) -> Dict[str, Any]:
    artist_name = data.get("artist_name")
    if not artist_name:
        raise ValueError("artist_name is required in the structured JSON.")

    source_month = data.get("source_month") or "unknown"
    instagram_handle = data.get("instagram_handle")
    contact_info = data.get("contact_info")
    tour_name = data.get("tour_name")
    poster_confidence = data.get("poster_confidence")
    source_post_id = data.get("source_post_id")
    image_hash = data.get("image_hash")

    image_url_value = image_url or _build_image_url(data, fallback="unknown")

    conn = init_db(db_path)
    try:
        artist_id = _get_artist_id(
            conn, artist_name, instagram_handle, contact_info
        )
        poster_id = _insert_poster(
            conn,
            artist_id=artist_id,
            image_url=image_url_value,
            tour_name=tour_name,
            source_month=source_month,
            source_type=source_type,
            source_url=source_url,
            source_post_id=source_post_id,
            image_hash=image_hash,
            poster_confidence=poster_confidence,
            raw_json=data,
        )
        event_count = _insert_events(conn, poster_id, data.get("events") or [])
        conn.commit()
    finally:
        conn.close()

    return {
        "artist_id": artist_id,
        "poster_id": poster_id,
        "event_count": event_count,
        "source_month": source_month,
    }
