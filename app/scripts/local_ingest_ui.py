#!/usr/bin/env python3
import hashlib
import html
import json
import re
import mimetypes
import os
import sqlite3
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path
import sys

from flask import Flask, request, send_from_directory, redirect
import requests
from werkzeug.utils import secure_filename

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from image_to_structured import image_to_structured
from local_db import ingest_structured


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

UPLOAD_DIR = PROJECT_ROOT / "output" / "uploads"
DB_PATH = Path(os.getenv("LOCAL_DB_PATH", PROJECT_ROOT / "output" / "local.db"))
KEEP_REMOTE_DOWNLOADS = os.getenv("KEEP_REMOTE_DOWNLOADS", "0") == "1"
REMOTE_CACHE_MAX_FILES = int(os.getenv("REMOTE_CACHE_MAX_FILES", "200"))


def _render_page(body: str, title: str = "Artist Calendar") -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <style>
      @import url("https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Space+Grotesk:wght@400;500;600&display=swap");
      :root {{
        --bg: #f6f1ea;
        --bg-2: #fbe8d1;
        --surface: #fffaf3;
        --ink: #1f1a17;
        --muted: #6d625a;
        --accent: #1c7c7b;
        --accent-2: #e26d5c;
        --accent-3: #f2c14e;
        --border: #e6dbcf;
        --shadow: 0 18px 40px rgba(60, 40, 20, 0.12);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: "Space Grotesk", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(1200px 420px at 10% -10%, rgba(28, 124, 123, 0.18), transparent 60%),
          radial-gradient(900px 380px at 90% 0%, rgba(226, 109, 92, 0.18), transparent 60%),
          linear-gradient(180deg, var(--bg) 0%, #f8f3ed 60%, #f4ede4 100%);
        min-height: 100vh;
      }}
      .container {{
        max-width: 980px;
        margin: 0 auto;
        padding: 28px 20px 60px;
      }}
      .topbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 24px;
      }}
      .brand {{
        display: flex;
        gap: 12px;
        align-items: center;
      }}
      .logo {{
        width: 44px;
        height: 44px;
        border-radius: 14px;
        background: linear-gradient(135deg, var(--accent), var(--accent-2));
        color: white;
        display: grid;
        place-items: center;
        font-weight: 700;
        font-size: 18px;
        letter-spacing: 0.5px;
      }}
      .brand-title {{
        font-family: "Fraunces", serif;
        font-size: 20px;
      }}
      .brand-sub {{
        font-size: 13px;
        color: var(--muted);
      }}
      h1, h2, h3 {{
        font-family: "Fraunces", serif;
        margin: 0 0 12px;
      }}
      h1 {{
        font-size: 32px;
        line-height: 1.1;
      }}
      p {{
        margin: 0 0 12px;
        color: var(--muted);
      }}
      .hero {{
        display: grid;
        gap: 20px;
      }}
      .card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 20px;
        box-shadow: var(--shadow);
      }}
      .card.tight {{
        padding: 16px;
      }}
      .pill {{
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        background: rgba(28, 124, 123, 0.12);
        color: var(--accent);
      }}
      .pill.accent {{
        background: rgba(226, 109, 92, 0.12);
        color: var(--accent-2);
      }}
      .button {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 12px 16px;
        border-radius: 12px;
        border: none;
        background: var(--accent);
        color: white;
        font-weight: 600;
        text-decoration: none;
        cursor: pointer;
        width: 100%;
      }}
      .button.secondary {{
        background: var(--accent-2);
      }}
      .button.small {{
        padding: 8px 12px;
        font-size: 12px;
      }}
      .button.ghost {{
        background: transparent;
        color: var(--accent);
        border: 1px solid var(--border);
        width: auto;
      }}
      .segmented {{
        display: flex;
        background: white;
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
      }}
      .mode-switch input[type="radio"] {{
        display: none;
      }}
      .segmented label {{
        flex: 1;
        text-align: center;
        padding: 8px 10px;
        border-radius: 8px;
        cursor: pointer;
        font-weight: 600;
        color: var(--muted);
      }}
      #mode_upload:checked ~ .segmented label[for="mode_upload"],
      #mode_url:checked ~ .segmented label[for="mode_url"] {{
        background: var(--accent);
        color: white;
      }}
      .mode-panels .panel {{
        display: none;
        margin-top: 14px;
      }}
      #mode_upload:checked ~ .mode-panels .panel.upload {{
        display: block;
      }}
      #mode_url:checked ~ .mode-panels .panel.url {{
        display: block;
      }}
      .actions {{
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 16px;
      }}
      .actions .button {{
        width: 100%;
      }}
      .field {{
        margin-top: 14px;
      }}
      label {{
        display: block;
        font-weight: 600;
        margin-bottom: 6px;
      }}
      input, select {{
        width: 100%;
        padding: 12px 14px;
        border-radius: 12px;
        border: 1px solid var(--border);
        background: white;
        font-family: inherit;
      }}
      input:focus, select:focus {{
        outline: 2px solid rgba(28, 124, 123, 0.25);
        border-color: var(--accent);
      }}
      .hint {{
        font-size: 12px;
        color: var(--muted);
        margin-top: 6px;
      }}
      .hint.warn {{
        color: var(--accent-2);
      }}
      .or {{
        text-align: center;
        margin: 14px 0;
        color: var(--muted);
        font-size: 13px;
        letter-spacing: 0.1em;
      }}
      .section-title {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 12px;
      }}
      .section-title form {{
        margin: 0;
      }}
      .list {{
        display: grid;
        gap: 12px;
      }}
      .poster-card {{
        display: grid;
        grid-template-columns: 64px 1fr;
        gap: 12px;
        padding: 12px;
        border-radius: 14px;
        border: 1px solid var(--border);
        background: white;
        text-decoration: none;
        color: inherit;
      }}
      .poster-thumb {{
        width: 64px;
        height: 64px;
        border-radius: 10px;
        background: #f0e7dd;
        overflow: hidden;
        display: grid;
        place-items: center;
        font-size: 12px;
        color: var(--muted);
      }}
      .poster-thumb img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
      }}
      .poster-meta h3 {{
        font-size: 18px;
        margin-bottom: 4px;
      }}
      .meta-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        font-size: 13px;
        color: var(--muted);
      }}
      .event-list {{
        display: grid;
        gap: 10px;
      }}
      .event-card {{
        display: grid;
        grid-template-columns: 72px 1fr;
        gap: 12px;
        padding: 12px;
        border-radius: 14px;
        border: 1px solid var(--border);
        background: white;
      }}
      .poster-image {{
        width: 100%;
        border-radius: 16px;
        max-height: 520px;
        object-fit: contain;
        background: #f0e7dd;
      }}
      .poster-image.full {{
        max-height: 80vh;
      }}
      .event-card.focus {{
        outline: 2px solid rgba(28, 124, 123, 0.4);
        box-shadow: 0 0 0 4px rgba(28, 124, 123, 0.08);
        animation: pulse 1.2s ease;
      }}
      .event-date {{
        font-weight: 700;
        color: var(--accent);
        text-align: center;
        background: rgba(28, 124, 123, 0.08);
        border-radius: 12px;
        padding: 8px 6px;
      }}
      .event-title {{
        font-weight: 600;
        margin-bottom: 4px;
      }}
      .event-meta {{
        font-size: 13px;
        color: var(--muted);
      }}
      .event-meta.missing {{
        color: var(--accent-2);
      }}
      .event-card.has-missing {{
        border-color: rgba(226, 109, 92, 0.28);
        background: #fff9f6;
      }}
      .missing-chips {{
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 6px;
      }}
      .chip {{
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 11px;
        background: #f1e9df;
        color: var(--muted);
      }}
      .chip.warn {{
        background: rgba(226, 109, 92, 0.14);
        color: var(--accent-2);
      }}
      .filter-row {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: center;
        margin-top: 10px;
      }}
      .filter-label {{
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--muted);
      }}
      .pill.selected {{
        background: var(--accent);
        color: white;
      }}
      .pill.soft {{
        background: #f1e9df;
        color: var(--muted);
      }}
      .missing-summary {{
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin: 10px 0 2px;
      }}
      .req {{
        color: var(--accent-2);
        margin-left: 4px;
        font-weight: 600;
      }}
      .field.required input,
      .field.required select {{
        border-color: rgba(226, 109, 92, 0.45);
        background: #fff4f1;
      }}
      .field-hint {{
        font-size: 12px;
        color: var(--muted);
        margin-top: 4px;
      }}
      .field-hint.warn {{
        color: var(--accent-2);
      }}
      .edit-form {{
        margin-top: 10px;
      }}
      .edit-form .field {{
        margin-top: 10px;
      }}
      .edit-actions {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 12px;
      }}
      .badge {{
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 11px;
        background: rgba(226, 109, 92, 0.12);
        color: var(--accent-2);
        margin-left: 8px;
      }}
      .badge.pending {{
        background: rgba(226, 109, 92, 0.12);
        color: var(--accent-2);
      }}
      .badge.approved {{
        background: rgba(28, 124, 123, 0.12);
        color: var(--accent);
      }}
      .badge.rejected {{
        background: rgba(226, 109, 92, 0.2);
        color: var(--accent-2);
      }}
      .badge.conf {{
        margin-left: 6px;
      }}
      .badge.conf.status-good {{
        background: rgba(28, 124, 123, 0.12);
        color: var(--accent);
      }}
      .badge.conf.status-warn {{
        background: rgba(242, 193, 78, 0.18);
        color: #a96d00;
      }}
      .badge.conf.status-bad {{
        background: rgba(226, 109, 92, 0.18);
        color: var(--accent-2);
      }}
      .pill.status-good {{
        background: rgba(28, 124, 123, 0.16);
        color: var(--accent);
      }}
      .pill.status-warn {{
        background: rgba(242, 193, 78, 0.18);
        color: #a96d00;
      }}
      .pill.status-bad {{
        background: rgba(226, 109, 92, 0.18);
        color: var(--accent-2);
      }}
      .review-grid {{
        display: grid;
        gap: 20px;
      }}
      .event-actions {{
        margin-top: 10px;
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }}
      .loading {{
        position: fixed;
        inset: 0;
        background: rgba(246, 241, 234, 0.9);
        display: none;
        align-items: center;
        justify-content: center;
        z-index: 999;
      }}
      .loading-card {{
        background: white;
        padding: 18px 22px;
        border-radius: 16px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow);
        text-align: center;
      }}
      .spinner {{
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 3px solid var(--border);
        border-top-color: var(--accent);
        margin: 0 auto 10px;
        animation: spin 1s linear infinite;
      }}
      @keyframes pulse {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.01); }}
        100% {{ transform: scale(1); }}
      }}
      .modal {{
        position: fixed;
        inset: 0;
        background: rgba(20, 15, 10, 0.6);
        display: none;
        align-items: center;
        justify-content: center;
        padding: 20px;
        z-index: 1000;
      }}
      .modal.active {{
        display: flex;
      }}
      .modal-content {{
        background: white;
        border-radius: 16px;
        padding: 14px;
        max-width: 92vw;
        max-height: 90vh;
        overflow: auto;
        border: 1px solid var(--border);
      }}
      .modal-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
      }}
      @keyframes spin {{
        to {{ transform: rotate(360deg); }}
      }}
      details {{
        margin-top: 14px;
      }}
      details summary {{
        cursor: pointer;
        font-weight: 600;
      }}
      pre {{
        white-space: pre-wrap;
        word-break: break-word;
        background: #f5efe7;
        padding: 12px;
        border-radius: 12px;
        border: 1px solid var(--border);
      }}
      .reveal {{
        animation: fadeUp 0.6s ease both;
      }}
      @keyframes fadeUp {{
        from {{ opacity: 0; transform: translateY(12px); }}
        to {{ opacity: 1; transform: translateY(0); }}
      }}
      @media (min-width: 900px) {{
        .hero {{
          grid-template-columns: 1.1fr 0.9fr;
          align-items: start;
        }}
        .review-grid {{
          grid-template-columns: 1.2fr 0.8fr;
          grid-template-areas:
            "summary poster"
            "list poster";
          align-items: start;
        }}
        .review-summary {{ grid-area: summary; }}
        .review-poster {{ grid-area: poster; }}
        .review-list {{ grid-area: list; }}
        .button {{
          width: auto;
        }}
        .actions .button {{
          width: auto;
        }}
      }}
    </style>
  </head>
  <body>
    <div class="container">
      {body}
    </div>
    <div class="loading" id="loading">
      <div class="loading-card">
        <div class="spinner"></div>
        <div id="loading-status">Importing poster…</div>
        <div class="hint">This can take up to 30 seconds.</div>
      </div>
    </div>
    <script>
      document.addEventListener('DOMContentLoaded', () => {{
        const form = document.querySelector('form[data-import]');
        const loading = document.getElementById('loading');
        const status = document.getElementById('loading-status');
        if (form && loading) {{
          form.addEventListener('submit', () => {{
            loading.style.display = 'flex';
            if (status) {{
              const messages = [
                'Downloading image…',
                'Reading poster…',
                'Extracting dates…',
                'Saving to your library…'
              ];
              let index = 0;
              status.textContent = messages[index];
              setInterval(() => {{
                index = (index + 1) % messages.length;
                status.textContent = messages[index];
              }}, 3500);
            }}
          }});
        }}

        const openButtons = document.querySelectorAll('[data-modal-open]');
        const closeButtons = document.querySelectorAll('[data-modal-close]');
        openButtons.forEach((button) => {{
          button.addEventListener('click', () => {{
            const target = button.getAttribute('data-modal-open');
            const modal = document.getElementById(target);
            if (modal) {{
              modal.classList.add('active');
            }}
          }});
        }});
        closeButtons.forEach((button) => {{
          button.addEventListener('click', () => {{
            const modal = button.closest('.modal');
            if (modal) {{
              modal.classList.remove('active');
            }}
          }});
        }});
        document.querySelectorAll('.modal').forEach((modal) => {{
          modal.addEventListener('click', (event) => {{
            if (event.target === modal) {{
              modal.classList.remove('active');
            }}
          }});
        }});

        const params = new URLSearchParams(window.location.search);
        const focusId = params.get('focus');
        if (focusId) {{
          const target = document.getElementById(`event-${{focusId}}`);
          if (target) {{
            target.classList.add('focus');
            target.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
          }}
        }}
      }});
    </script>
  </body>
</html>
"""


@app.get("/")
def index() -> str:
    return _render_page(
        """
        <header class="topbar">
          <div class="brand">
            <div class="logo">AC</div>
            <div>
              <div class="brand-title">Artist Calendar</div>
              <div class="brand-sub">Poster to tour dates in seconds</div>
            </div>
          </div>
          <a class="button ghost" href="/db">Library</a>
        </header>
        <section class="hero">
          <div class="reveal">
            <h1>Capture tour dates without the chaos.</h1>
            <p>Upload a tour poster or paste an image URL. We extract dates and store them for review.</p>
            <div class="meta-row" style="margin-top: 12px;">
              <span class="pill">mobile first</span>
              <span class="pill accent">review flow</span>
              <span class="pill">fast ingest</span>
            </div>
          </div>
          <div class="card reveal">
            <div class="section-title">
              <h2>New poster</h2>
              <span class="pill">Start here</span>
            </div>
            <form action="/ingest" method="post" enctype="multipart/form-data" data-import>
              <div class="mode-switch">
                <input type="radio" id="mode_upload" name="input_mode" value="upload" checked>
                <input type="radio" id="mode_url" name="input_mode" value="url">
                <div class="segmented">
                  <label for="mode_upload">Upload</label>
                  <label for="mode_url">Paste link</label>
                </div>
                <div class="mode-panels">
                  <div class="panel upload">
                    <div class="field">
                      <label for="image">Upload file</label>
                      <input id="image" type="file" name="image" accept="image/*">
                      <div class="hint">JPG or PNG, up to 20MB.</div>
                    </div>
                  </div>
                  <div class="panel url">
                    <div class="field">
                      <label for="image_url">Image URL</label>
                      <input id="image_url" type="text" name="image_url" placeholder="https://example.com/poster.jpg">
                      <div class="hint">Direct image links or Instagram posts. Reels/videos are not supported.</div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="field">
                <button type="submit" class="button">Import poster</button>
              </div>
              <div class="hint">Next you will review and approve the events.</div>
            </form>
          </div>
        </section>
        """
    )


def _fetch_posters(limit: int = 50):
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT p.id, p.image_url, p.source_month, p.tour_name, p.created_at,
               p.poster_confidence, p.source_url, p.source_post_id, p.image_hash,
               a.name AS artist_name,
               COUNT(e.id) AS event_count,
               SUM(CASE WHEN e.review_status = 'approved' THEN 1 ELSE 0 END) AS approved_count,
               SUM(CASE WHEN e.review_status = 'pending' THEN 1 ELSE 0 END) AS pending_count,
               SUM(CASE WHEN e.review_status = 'rejected' THEN 1 ELSE 0 END) AS rejected_count
        FROM posters p
        JOIN artists a ON a.id = p.artist_id
        LEFT JOIN events e ON e.poster_id = p.id
        GROUP BY p.id, p.image_url, p.source_month, p.tour_name, p.created_at,
                 p.poster_confidence, p.source_url, p.source_post_id, p.image_hash, a.name
        ORDER BY p.created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def _fetch_poster(poster_id: str):
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT p.id, p.image_url, p.source_month, p.tour_name, p.created_at,
               p.source_url, p.raw_json, p.poster_confidence, a.name AS artist_name
        FROM posters p
        JOIN artists a ON a.id = p.artist_id
        WHERE p.id = ?
        """,
        (poster_id,),
    ).fetchone()
    conn.close()
    return row


def _fetch_events(poster_id: str):
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, date, event_name, venue, city, province, time, ticket_info,
               status, review_status, confidence
        FROM events
        WHERE poster_id = ?
        ORDER BY date
        """,
        (poster_id,),
    ).fetchall()
    conn.close()
    return rows


def _fetch_event(event_id: str):
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT id, poster_id, date, event_name, venue, city, province, time,
               ticket_info, status, review_status, confidence
        FROM events
        WHERE id = ?
        """,
        (event_id,),
    ).fetchone()
    conn.close()
    return row


def _update_event(event_id: str, fields: dict, review_status: str | None) -> None:
    updates = []
    params = []
    for key in (
        "date",
        "event_name",
        "venue",
        "city",
        "province",
        "time",
        "ticket_info",
        "status",
    ):
        if key in fields:
            updates.append(f"{key} = ?")
            params.append(fields[key] or None)

    if review_status:
        updates.append("review_status = ?")
        params.append(review_status)

    updates.append("updated_at = ?")
    params.append(_now())

    params.append(event_id)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        f"UPDATE events SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    conn.commit()
    conn.close()


def _approve_all_events(poster_id: str) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "UPDATE events SET review_status = ?, updated_at = ? WHERE poster_id = ?",
        ("approved", _now(), poster_id),
    )
    conn.commit()
    conn.close()


def _next_pending_event_id(poster_id: str, current_event_id: str) -> str | None:
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    current = conn.execute(
        "SELECT date FROM events WHERE id = ?",
        (current_event_id,),
    ).fetchone()
    current_date = current["date"] if current else None
    rows = conn.execute(
        """
        SELECT id, date
        FROM events
        WHERE poster_id = ? AND review_status = 'pending'
        ORDER BY date, id
        """,
        (poster_id,),
    ).fetchall()
    conn.close()
    if not rows:
        return None
    if current_date:
        for row in rows:
            if row["date"] >= current_date and row["id"] != current_event_id:
                return row["id"]
    return rows[0]["id"]


@app.get("/review/<poster_id>")
def review_view(poster_id: str) -> str:
    poster = _fetch_poster(poster_id)
    if not poster:
        return _render_page(
            """
            <header class="topbar">
              <div class="brand">
                <div class="logo">AC</div>
                <div>
                  <div class="brand-title">Artist Calendar</div>
                  <div class="brand-sub">Review</div>
                </div>
              </div>
              <a class="button ghost" href="/db">Back</a>
            </header>
            <div class="card">
              <h2>Poster not found</h2>
              <p>We could not locate this poster in the local database.</p>
            </div>
            """
        )

    events = _fetch_events(poster_id)
    pending_events = [row for row in events if row["review_status"] == "pending"]
    pending_count = len(pending_events)
    approved_count = sum(1 for row in events if row["review_status"] == "approved")
    rejected_count = sum(1 for row in events if row["review_status"] == "rejected")
    status_label, status_class = _poster_status(len(events), pending_count, rejected_count)
    poster_conf_pill = _confidence_pill(poster["poster_confidence"])
    show_all = request.args.get("show") == "all"
    missing_filter = request.args.get("missing")
    allowed_missing = {"any", "venue", "city", "province", "complete"}
    if missing_filter not in allowed_missing:
        missing_filter = None
    base_events = events if show_all else pending_events
    missing_counts = {key: 0 for key in allowed_missing}
    for row in base_events:
        missing_fields = _missing_fields(row)
        if missing_fields:
            missing_counts["any"] += 1
        else:
            missing_counts["complete"] += 1
        for field in missing_fields:
            if field in missing_counts:
                missing_counts[field] += 1

    def _matches_missing(row: dict) -> bool:
        missing_fields = _missing_fields(row)
        if missing_filter == "any":
            return bool(missing_fields)
        if missing_filter == "complete":
            return not missing_fields
        if missing_filter in {"venue", "city", "province"}:
            return missing_filter in missing_fields
        return True

    filtered = [row for row in base_events if _matches_missing(row)]
    pending_missing_count = sum(1 for row in pending_events if _missing_fields(row))
    confirm_message = "Approve all events?"
    if pending_missing_count:
        confirm_message = (
            f"Approve all events? {pending_missing_count} pending events still missing "
            "venue, city, or province."
        )
    confirm_message_js = json.dumps(confirm_message)
    missing_total = len(base_events)
    pending_url = _review_url(poster_id, False, missing_filter)
    all_url = _review_url(poster_id, True, missing_filter)
    missing_all_url = _review_url(poster_id, show_all, None)
    missing_any_url = _review_url(poster_id, show_all, "any")
    missing_venue_url = _review_url(poster_id, show_all, "venue")
    missing_city_url = _review_url(poster_id, show_all, "city")
    missing_province_url = _review_url(poster_id, show_all, "province")
    missing_complete_url = _review_url(poster_id, show_all, "complete")

    event_cards = []
    for row in filtered:
        title = row["event_name"] or row["venue"] or "Untitled event"
        location = _format_location(row["venue"], row["city"], row["province"])
        missing_fields = _missing_fields(row)
        missing_class = " has-missing" if missing_fields else ""
        missing_chips = ""
        if missing_fields:
            chips = "".join(
                f'<span class="chip warn">{_esc(field.title())}</span>'
                for field in missing_fields
            )
            missing_chips = f'<div class="missing-chips">{chips}</div>'
        status = row["review_status"] or "pending"
        status_class = status if status in {"approved", "rejected"} else "pending"
        conf_badge = _confidence_badge(row["confidence"])

        quick_approve = ""
        if row["review_status"] != "approved":
            quick_approve = (
                f"<form method=\"post\" action=\"/event/{row['id']}\">"
                f"<input type=\"hidden\" name=\"poster_id\" value=\"{_esc(poster_id)}\">"
                f"<input type=\"hidden\" name=\"return\" value=\"/review/{poster_id}\">"
                f"<button class=\"button small\" name=\"action\" value=\"approve\">Approve</button>"
                f"</form>"
            )

        event_cards.append(
            f"""
            <div class="event-card{missing_class}" id="event-{_esc(row['id'])}">
              <div class="event-date">{_esc(_format_event_date(row['date']))}</div>
              <div>
                <div class="event-title">{_esc(title)}
                  <span class="badge {status_class}">{_esc(status)}</span>
                  {conf_badge}
                </div>
                <div class="event-meta">{_esc(location or 'Location not set')}</div>
                {missing_chips}
                <div class="event-actions">
                  <a class="button ghost small" href="/event/{row['id']}?return=/review/{poster_id}">Review</a>
                  {quick_approve}
                </div>
              </div>
            </div>
            """
        )

    image_src = _image_src(poster["image_url"])
    image_html = ""
    if image_src:
        image_html = (
            f"<img src=\"{image_src}\" alt=\"poster\" class=\"poster-image\">"
        )
    modal_html = ""
    if image_src:
        modal_html = f"""
        <div class="modal" id="poster-modal">
          <div class="modal-content">
            <div class="modal-header">
              <strong>Poster</strong>
              <button class="button ghost small" type="button" data-modal-close>Close</button>
            </div>
            <img src="{image_src}" alt="poster" class="poster-image full">
          </div>
        </div>
        """

    return _render_page(
        f"""
        <header class="topbar">
          <div class="brand">
            <div class="logo">AC</div>
            <div>
              <div class="brand-title">Artist Calendar</div>
              <div class="brand-sub">Review</div>
            </div>
          </div>
          <div class="actions">
            <a class="button ghost" href="/db">Library</a>
            <a class="button ghost" href="/poster/{poster_id}">Poster view</a>
          </div>
        </header>
        <div class="review-grid">
          <div class="card review-summary">
            <h1>Review events</h1>
            <p>Confirm details before approval.</p>
            <div class="meta-row" style="margin-top: 12px;">
              <span class="pill">pending {pending_count}</span>
              <span class="pill accent">approved {approved_count}</span>
              <span class="pill">rejected {rejected_count}</span>
              <span class="pill {status_class}">{status_label}</span>
              {poster_conf_pill}
            </div>
            <div class="actions">
              <form method="post" action="/poster/{poster_id}/approve-all" onsubmit="return confirm({confirm_message_js})">
                <button class="button" type="submit">Approve all</button>
              </form>
              <a class="button ghost" href="/poster/{poster_id}">Poster details</a>
              <button class="button ghost" type="button" data-modal-open="poster-modal">View poster</button>
            </div>
          </div>
          <div class="card review-poster">
            <h2>{_esc(poster['artist_name'])}</h2>
            <p>{_esc(poster['tour_name'] or 'Untitled tour')}</p>
            <div class="meta-row" style="margin-bottom: 12px;">
              <span class="pill">{_esc(poster['source_month'])}</span>
              <span class="pill accent">{len(events)} events</span>
              <span class="pill {status_class}">{status_label}</span>
              {poster_conf_pill}
            </div>
            {image_html}
          </div>
          <div class="card review-list">
            <div class="section-title">
              <h2>Event list</h2>
              <div class="actions">
                <a class="button ghost small" href="{pending_url}">Pending</a>
                <a class="button ghost small" href="{all_url}">All</a>
              </div>
            </div>
            <div class="filter-row">
              <span class="filter-label">Missing</span>
              <a class="pill soft {'' if missing_filter else 'selected'}" href="{missing_all_url}">All {missing_total}</a>
              <a class="pill { 'selected' if missing_filter == 'any' else '' }" href="{missing_any_url}">Any {missing_counts['any']}</a>
              <a class="pill { 'selected' if missing_filter == 'venue' else '' }" href="{missing_venue_url}">Venue {missing_counts['venue']}</a>
              <a class="pill { 'selected' if missing_filter == 'city' else '' }" href="{missing_city_url}">City {missing_counts['city']}</a>
              <a class="pill { 'selected' if missing_filter == 'province' else '' }" href="{missing_province_url}">Province {missing_counts['province']}</a>
              <a class="pill { 'selected' if missing_filter == 'complete' else '' }" href="{missing_complete_url}">Complete {missing_counts['complete']}</a>
            </div>
            <div class="event-list">
              {''.join(event_cards) if event_cards else '<p>No events to review.</p>'}
            </div>
          </div>
        </div>
        {modal_html}
        """
    )


def _guess_extension(url: str, content_type: str | None) -> str:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix
    if suffix:
        return suffix
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if guessed:
            return guessed
    return ".jpg"


def _save_uploaded_file(file) -> Path:
    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    image_path = UPLOAD_DIR / f"{timestamp}_{filename}"
    file.save(image_path)
    return image_path


def _extract_meta_content(text: str, name: str) -> str | None:
    pattern = rf'<meta[^>]+(?:property|name)=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return html.unescape(match.group(1))
    return None


def _extract_image_url_from_html(text: str) -> str | None:
    patterns = [
        r'<meta[^>]+property=["\']og:image:secure_url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image:src["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return html.unescape(match.group(1))
    return None


def _html_has_video_meta(text: str) -> bool:
    og_type = _extract_meta_content(text, "og:type")
    if og_type and "video" in og_type.lower():
        return True
    if re.search(r'property=["\']og:video', text, re.IGNORECASE):
        return True
    if re.search(r'name=["\']twitter:player', text, re.IGNORECASE):
        return True
    return False


def _instagram_post_info(url: str) -> tuple[str | None, str | None]:
    parsed = urlparse(url)
    host = parsed.netloc.lower().split(":")[0]
    if not host.endswith("instagram.com"):
        return None, None
    parts = [part for part in parsed.path.split("/") if part]
    for idx, part in enumerate(parts[:-1]):
        if part in ("p", "reel", "tv"):
            return part, parts[idx + 1]
    return None, None


def _instagram_media_url(shortcode: str) -> str:
    return f"https://www.instagram.com/p/{shortcode}/media/?size=l"


def _infer_source_type(url: str) -> str:
    host = urlparse(url).netloc.lower().split(":")[0]
    if "instagram" in host:
        return "instagram"
    if "facebook" in host or "fbcdn.net" in host:
        return "facebook"
    return "website"


def _should_store_local_image(source_url: str, resolved_url: str) -> bool:
    source_host = urlparse(source_url).netloc.lower()
    resolved_host = urlparse(resolved_url).netloc.lower()
    if "instagram.com" in source_host:
        return True
    if "fbcdn.net" in resolved_host or "cdninstagram.com" in resolved_host:
        return True
    return False


def _prune_remote_downloads() -> None:
    if REMOTE_CACHE_MAX_FILES <= 0:
        return
    if not UPLOAD_DIR.exists():
        return
    candidates = sorted(
        (path for path in UPLOAD_DIR.iterdir() if path.is_file() and "_remote" in path.name),
        key=lambda path: path.stat().st_mtime,
    )
    excess = len(candidates) - REMOTE_CACHE_MAX_FILES
    for path in candidates[:max(0, excess)]:
        try:
            path.unlink()
        except OSError:
            continue


def _write_image_response(response: requests.Response, url: str) -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    extension = _guess_extension(url, response.headers.get("Content-Type"))
    image_path = UPLOAD_DIR / f"{timestamp}_remote{extension}"
    with open(image_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return image_path


def _fetch_html(url: str, headers: dict, use_jina: bool = False) -> str | None:
    request_url = url
    if use_jina:
        if url.startswith("https://"):
            request_url = f"https://r.jina.ai/https://{url[len('https://'):]}"
        elif url.startswith("http://"):
            request_url = f"https://r.jina.ai/http://{url[len('http://'):]}"
    extra_headers = dict(headers)
    if use_jina:
        jina_key = os.getenv("JINA_API_KEY")
        if jina_key:
            extra_headers["Authorization"] = f"Bearer {jina_key}"
    response = requests.get(request_url, timeout=20, headers=extra_headers)
    if response.status_code >= 400:
        return None
    return response.text


def _resolve_image_url_with_playwright(url: str) -> str | None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(1500)
            meta_image = page.evaluate(
                """
                () => {
                  const meta = (name) => {
                    const el = document.querySelector(`meta[property='${name}']`) ||
                               document.querySelector(`meta[name='${name}']`);
                    return el ? el.getAttribute('content') : null;
                  };
                  return (
                    meta('og:image:secure_url') ||
                    meta('og:image') ||
                    meta('twitter:image:src') ||
                    meta('twitter:image')
                  );
                }
                """
            )
            try:
                page.wait_for_selector("article img", timeout=5000)
            except Exception:
                pass
            images = page.evaluate(
                """
                () => {
                  const nodes = Array.from(document.querySelectorAll('article img'));
                  return nodes.map(img => ({
                    src: img.currentSrc || img.src || null,
                    srcset: img.getAttribute('srcset') || '',
                    width: img.naturalWidth || 0,
                    height: img.naturalHeight || 0
                  }));
                }
                """
            )
            browser.close()
            best_url = None
            best_score = -1
            for item in images or []:
                src = item.get("src")
                srcset = item.get("srcset") or ""
                width = item.get("width") or 0
                height = item.get("height") or 0
                score = width * height
                if srcset:
                    for part in srcset.split(","):
                        chunk = part.strip().split()
                        if len(chunk) < 2:
                            continue
                        candidate = chunk[0]
                        size = chunk[1].strip()
                        if size.endswith("w"):
                            try:
                                w = int(size[:-1])
                            except ValueError:
                                continue
                            if w * w > score:
                                score = w * w
                                src = candidate
                        elif size.endswith("x"):
                            try:
                                scale = float(size[:-1])
                            except ValueError:
                                continue
                            if scale > 1 and score > 0:
                                score = int(score * scale * scale)
                                src = candidate
                if src and score > best_score:
                    best_score = score
                    best_url = src
            return best_url or meta_image
    except Exception:
        return None


def _download_image(url: str) -> tuple[Path, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*;q=0.8,*/*;q=0.7",
    }
    post_type, shortcode = _instagram_post_info(url)
    response = requests.get(url, stream=True, timeout=20, headers=headers)
    if response.status_code >= 400:
        if post_type in ("reel", "tv"):
            raise ValueError("Instagram reels/videos are not supported yet. Please use a static image.")
        if post_type == "p" and shortcode:
            media_url = _instagram_media_url(shortcode)
            media_response = requests.get(media_url, stream=True, timeout=20, headers=headers)
            if media_response.status_code < 400:
                media_type = (media_response.headers.get("Content-Type") or "").lower()
                if media_type.startswith("image/"):
                    resolved_url = media_response.url or media_url
                    return _write_image_response(media_response, resolved_url), resolved_url
        raise ValueError(f"Failed to download image: {response.status_code}")

    content_type = (response.headers.get("Content-Type") or "").lower()
    if content_type.startswith("image/"):
        resolved_url = response.url or url
        return _write_image_response(response, resolved_url), resolved_url

    text = response.text or ""
    if post_type in ("reel", "tv") or (post_type and _html_has_video_meta(text)):
        raise ValueError("Instagram reels/videos are not supported yet. Please use a static image.")

    if post_type == "p" and shortcode:
        media_url = _instagram_media_url(shortcode)
        media_response = requests.get(media_url, stream=True, timeout=20, headers=headers)
        if media_response.status_code < 400:
            media_type = (media_response.headers.get("Content-Type") or "").lower()
            if media_type.startswith("image/"):
                resolved_url = media_response.url or media_url
                return _write_image_response(media_response, resolved_url), resolved_url

    image_url = _extract_image_url_from_html(text)
    if not image_url:
        jina_text = _fetch_html(url, headers, use_jina=True)
        if jina_text:
            image_url = _extract_image_url_from_html(jina_text)
    if not image_url:
        image_url = _resolve_image_url_with_playwright(url)
    if image_url and image_url != url:
        image_response = requests.get(image_url, stream=True, timeout=20, headers=headers)
        if image_response.status_code >= 400:
            raise ValueError(f"Failed to download image from page: {image_response.status_code}")
        image_type = (image_response.headers.get("Content-Type") or "").lower()
        if not image_type.startswith("image/"):
            raise ValueError("Page did not contain a usable image link.")
        return _write_image_response(image_response, image_url), image_url

    raise ValueError("URL did not point to an image. Use a direct image link or a public post URL.")


@app.get("/uploads/<path:filename>")
def uploads(filename: str):
    return send_from_directory(UPLOAD_DIR, filename)


def _image_src(image_url: str | None) -> str:
    if not image_url or not isinstance(image_url, str):
        return ""
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    try:
        path = Path(image_url)
        if path.is_file() and path.parent == UPLOAD_DIR:
            return f"/uploads/{path.name}"
    except OSError:
        return ""
    return ""


def _esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _format_location(venue: str | None, city: str | None, province: str | None) -> str:
    parts = []
    for value in (venue, city, province):
        if not value:
            continue
        if value in parts:
            continue
        parts.append(value)
    return " - ".join(parts)


def _row_value(row: object, key: str) -> object:
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]  # type: ignore[index]
    except Exception:
        return None


def _extract_instagram_shortcode(url: str) -> str | None:
    try:
        parts = [part for part in urlparse(url).path.split("/") if part]
    except Exception:
        return None
    for idx, part in enumerate(parts):
        if part in {"p", "reel", "tv"} and idx + 1 < len(parts):
            return parts[idx + 1]
    return None


def _hash_file(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _find_existing_poster(
    source_post_id: str | None,
    source_url: str | None,
    image_hash: str | None,
):
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        if source_post_id:
            row = conn.execute(
                """
                SELECT p.id, p.created_at, p.tour_name, p.source_month, a.name AS artist_name
                FROM posters p
                JOIN artists a ON a.id = p.artist_id
                WHERE p.source_post_id = ?
                ORDER BY p.created_at DESC
                LIMIT 1
                """,
                (source_post_id,),
            ).fetchone()
            if row:
                return row
        if source_url:
            row = conn.execute(
                """
                SELECT p.id, p.created_at, p.tour_name, p.source_month, a.name AS artist_name
                FROM posters p
                JOIN artists a ON a.id = p.artist_id
                WHERE p.source_url = ?
                ORDER BY p.created_at DESC
                LIMIT 1
                """,
                (source_url,),
            ).fetchone()
            if row:
                return row
        if image_hash:
            row = conn.execute(
                """
                SELECT p.id, p.created_at, p.tour_name, p.source_month, a.name AS artist_name
                FROM posters p
                JOIN artists a ON a.id = p.artist_id
                WHERE p.image_hash = ?
                ORDER BY p.created_at DESC
                LIMIT 1
                """,
                (image_hash,),
            ).fetchone()
            if row:
                return row
    finally:
        conn.close()
    return None


def _poster_dedupe_key(row: dict) -> str:
    return (
        row.get("source_post_id")
        or row.get("source_url")
        or row.get("image_hash")
        or row["id"]
    )


def _dedupe_posters(rows: list[dict]) -> tuple[list[dict], int]:
    buckets: dict[str, dict] = {}
    for row in rows:
        key = _poster_dedupe_key(row)
        entry = buckets.get(key)
        if not entry:
            buckets[key] = {"row": row, "count": 1}
            continue
        entry["count"] += 1
        if (row.get("created_at") or "") > (entry["row"].get("created_at") or ""):
            entry["row"] = row

    deduped = []
    for entry in buckets.values():
        item = dict(entry["row"])
        item["version_count"] = entry["count"]
        deduped.append(item)

    deduped.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    hidden_count = max(len(rows) - len(deduped), 0)
    return deduped, hidden_count


def _missing_fields(row: object) -> list[str]:
    missing = []
    if not _row_value(row, "venue"):
        missing.append("venue")
    if not _row_value(row, "city"):
        missing.append("city")
    if not _row_value(row, "province"):
        missing.append("province")
    return missing


def _review_url(poster_id: str, show_all: bool, missing: str | None) -> str:
    params = []
    if show_all:
        params.append("show=all")
    if missing:
        params.append(f"missing={missing}")
    query = f"?{'&'.join(params)}" if params else ""
    return f"/review/{poster_id}{query}"


def _poster_status(event_count: int, pending_count: int, rejected_count: int) -> tuple[str, str]:
    if event_count <= 0:
        return ("no events", "status-warn")
    if pending_count == 0 and rejected_count == 0:
        return ("validated", "status-good")
    if rejected_count > 0:
        return ("needs fixes", "status-bad")
    return ("in review", "status-warn")


def _format_confidence(score: float) -> str:
    return f"{int(round(score * 100))}%"


def _confidence_class(score: float) -> str:
    if score >= 0.8:
        return "status-good"
    if score >= 0.6:
        return "status-warn"
    return "status-bad"


def _confidence_badge(score: float | None) -> str:
    if score is None:
        return ""
    label = _format_confidence(score)
    klass = _confidence_class(score)
    return f'<span class="badge conf {klass}">{label}</span>'


def _confidence_pill(score: float | None) -> str:
    if score is None:
        return ""
    label = _format_confidence(score)
    klass = _confidence_class(score)
    return f'<span class="pill {klass}">conf {label}</span>'


def _format_datetime(value: str) -> str:
    try:
        cleaned = value.replace("Z", "")
        dt = datetime.fromisoformat(cleaned)
        return dt.strftime("%b %d, %Y %H:%M")
    except Exception:
        return value


def _format_event_date(value: str) -> str:
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.strftime("%b %d")
    except Exception:
        return value


@app.get("/db")
def db_view() -> str:
    show_all = request.args.get("show") == "all"
    posters_rows = _fetch_posters()
    if not posters_rows:
        return _render_page(
            """
            <header class="topbar">
              <div class="brand">
                <div class="logo">AC</div>
                <div>
                  <div class="brand-title">Artist Calendar</div>
                  <div class="brand-sub">Local library</div>
                </div>
              </div>
              <a class="button ghost" href="/">New upload</a>
            </header>
            <div class="card">
              <h2>Local DB</h2>
              <p>No posters found yet.</p>
              <div class="actions">
                <a class="button" href="/">Add your first poster</a>
              </div>
            </div>
            """
        )

    posters_dicts = [dict(row) for row in posters_rows]
    hidden_count = 0
    if show_all:
        posters = posters_dicts
    else:
        posters, hidden_count = _dedupe_posters(posters_dicts)

    cards = []
    for row in posters:
        thumb = ""
        image_src = _image_src(row["image_url"])
        if image_src:
            thumb = f"<img src=\"{image_src}\" alt=\"poster\">"
        else:
            thumb = "Poster"

        event_count = row["event_count"] or 0
        pending_count = row["pending_count"] or 0
        rejected_count = row["rejected_count"] or 0
        status_label, status_class = _poster_status(event_count, pending_count, rejected_count)
        version_count = row.get("version_count", 1)
        version_pill = (
            f'<span class="pill soft">{version_count} versions</span>'
            if version_count > 1
            else ""
        )

        cards.append(
            f"""
            <a class="poster-card" href="/poster/{row['id']}">
              <div class="poster-thumb">{thumb}</div>
              <div class="poster-meta">
                <h3>{_esc(row['artist_name'])}</h3>
                <div class="meta-row">
                  <span>{_esc(row['tour_name'] or 'Untitled tour')}</span>
                </div>
                <div class="meta-row" style="margin-top: 6px;">
                  <span class="pill">{_esc(row['source_month'])}</span>
                  <span class="pill accent">{event_count} events</span>
                  <span class="pill {status_class}">{status_label}</span>
                  {version_pill}
                  <span>{_esc(_format_datetime(row['created_at']))}</span>
                </div>
              </div>
            </a>
            """
        )

    return _render_page(
        f"""
        <header class="topbar">
          <div class="brand">
            <div class="logo">AC</div>
            <div>
              <div class="brand-title">Artist Calendar</div>
              <div class="brand-sub">Local library</div>
            </div>
          </div>
          <a class="button ghost" href="/">New upload</a>
        </header>
        <div class="card">
          <div class="section-title">
            <h2>Posters</h2>
            <span class="pill">library</span>
          </div>
          <div class="filter-row">
            <span class="filter-label">View</span>
            <a class="pill {'' if show_all else 'selected'}" href="/db">Unique</a>
            <a class="pill { 'selected' if show_all else ''}" href="/db?show=all">All imports</a>
            {f'<span class="pill soft">hidden {hidden_count}</span>' if hidden_count and not show_all else ''}
          </div>
          <div class="list">
            {''.join(cards)}
          </div>
        </div>
        """
    )


@app.get("/poster/<poster_id>")
def poster_view(poster_id: str) -> str:
    poster = _fetch_poster(poster_id)
    if not poster:
        return _render_page(
            """
            <header class="topbar">
              <div class="brand">
                <div class="logo">AC</div>
                <div>
                  <div class="brand-title">Artist Calendar</div>
                  <div class="brand-sub">Poster details</div>
                </div>
              </div>
              <a class="button ghost" href="/db">Back to library</a>
            </header>
            <div class="card">
              <h2>Poster not found</h2>
              <p>We could not locate this poster in the local database.</p>
            </div>
            """
        )

    events = _fetch_events(poster_id)
    pending_count = sum(1 for row in events if row["review_status"] == "pending")
    approved_count = sum(1 for row in events if row["review_status"] == "approved")
    rejected_count = sum(1 for row in events if row["review_status"] == "rejected")
    status_label, status_class = _poster_status(len(events), pending_count, rejected_count)
    poster_conf_pill = _confidence_pill(poster["poster_confidence"])
    source_url_value = poster["source_url"]
    source_link = ""
    if source_url_value:
        source_link = (
            f'<a class="button ghost small" href="{_esc(source_url_value)}" '
            'target="_blank" rel="noopener">Source link</a>'
        )
    event_cards = []
    for row in events:
        title = row["event_name"] or row["venue"] or "Untitled event"
        location = _format_location(row["venue"], row["city"], row["province"])
        missing_fields = _missing_fields(row)
        missing_class = " has-missing" if missing_fields else ""
        missing_chips = ""
        if missing_fields:
            chips = "".join(
                f'<span class="chip warn">{_esc(field.title())}</span>'
                for field in missing_fields
            )
            missing_chips = f'<div class="missing-chips">{chips}</div>'
        status = row["review_status"] or "pending"
        event_status_class = status if status in {"approved", "rejected"} else "pending"
        conf_badge = _confidence_badge(row["confidence"])

        event_cards.append(
            f"""
            <div class="event-card{missing_class}">
              <div class="event-date">{_esc(_format_event_date(row['date']))}</div>
              <div>
                <div class="event-title">{_esc(title)}
                  <span class="badge {event_status_class}">{_esc(status)}</span>
                  {conf_badge}
                </div>
                <div class="event-meta">{_esc(location or 'Location not set')}</div>
                {missing_chips}
                <div class="event-actions">
                  <a class="button ghost small" href="/event/{row['id']}?return=/review/{poster_id}">Review</a>
                </div>
              </div>
            </div>
            """
        )

    image_src = _image_src(poster["image_url"])
    image_html = ""
    if image_src:
        image_html = (
            f"<img src=\"{image_src}\" alt=\"poster\" class=\"poster-image\">"
        )

    return _render_page(
        f"""
        <header class="topbar">
          <div class="brand">
            <div class="logo">AC</div>
            <div>
              <div class="brand-title">Artist Calendar</div>
              <div class="brand-sub">Poster details</div>
            </div>
          </div>
          <div class="actions">
            <a class="button ghost" href="/review/{poster_id}">Review poster</a>
            <a class="button ghost" href="/db">Back to library</a>
          </div>
        </header>
        <div class="hero">
          <div class="card">
            <h1>{_esc(poster['artist_name'])}</h1>
            <p>{_esc(poster['tour_name'] or 'Untitled tour')}</p>
            <div class="meta-row" style="margin-bottom: 12px;">
              <span class="pill">{_esc(poster['source_month'])}</span>
              <span class="pill accent">{len(events)} events</span>
              <span class="pill {status_class}">{status_label}</span>
              {poster_conf_pill}
            </div>
            {source_link}
            <p style="font-size: 13px; color: var(--muted);">Poster image</p>
            {image_html}
          </div>
          <div class="card">
            <div class="section-title">
              <h2>Events</h2>
              <span class="pill">pending {pending_count}/{len(events)}</span>
            </div>
            <div class="event-list">
              {''.join(event_cards) if event_cards else '<p>No events found.</p>'}
            </div>
          </div>
        </div>
        """
    )


@app.route("/event/<event_id>", methods=["GET", "POST"])
def update_event(event_id: str):
    if request.method == "POST":
        action = request.form.get("action") or "save_pending"
        poster_id = request.form.get("poster_id")
        return_url = request.form.get("return") or (f"/review/{poster_id}" if poster_id else "/db")
        review_status = None
        if action in {"approve", "approve_next"}:
            review_status = "approved"
        elif action == "reject":
            review_status = "rejected"
        elif action == "save_pending":
            review_status = "pending"

        fields = {}
        for key in (
            "date",
            "event_name",
            "venue",
            "city",
            "province",
            "time",
            "ticket_info",
            "status",
        ):
            if key in request.form:
                fields[key] = request.form.get(key)
        _update_event(event_id, fields, review_status)
        if poster_id and action == "approve_next":
            next_id = _next_pending_event_id(poster_id, event_id)
            if next_id:
                return redirect(f"/event/{next_id}?return=/review/{poster_id}")
            return redirect(return_url)

        if poster_id and action == "approve":
            next_id = _next_pending_event_id(poster_id, event_id)
            if next_id:
                return redirect(f"/review/{poster_id}?focus={next_id}")
        return redirect(return_url)

    event = _fetch_event(event_id)
    if not event:
        return _render_page(
            """
            <header class="topbar">
              <div class="brand">
                <div class="logo">AC</div>
                <div>
                  <div class="brand-title">Artist Calendar</div>
                  <div class="brand-sub">Event review</div>
                </div>
              </div>
              <a class="button ghost" href="/db">Back</a>
            </header>
            <div class="card">
              <h2>Event not found</h2>
              <p>We could not locate this event in the local database.</p>
            </div>
            """
        )

    poster_id = event["poster_id"]
    poster = _fetch_poster(poster_id)
    image_src = _image_src(poster["image_url"]) if poster else ""
    image_html = ""
    modal_html = ""
    if image_src:
        image_html = (
            f"<img src=\"{image_src}\" alt=\"poster\" "
            "style=\"width: 100%; max-width: 420px; border-radius: 16px;\">"
        )
        modal_html = f"""
        <div class="modal" id="poster-modal">
          <div class="modal-content">
            <div class="modal-header">
              <strong>Poster</strong>
              <button class="button ghost small" type="button" data-modal-close>Close</button>
            </div>
            <img src="{image_src}" alt="poster" class="poster-image full">
          </div>
        </div>
        """
    return_url = request.args.get("return") or f"/review/{poster_id}"
    title = event["event_name"] or event["venue"] or "Untitled event"
    conf_pill = _confidence_pill(event["confidence"])
    missing_fields = _missing_fields(event)
    missing_summary = ""
    if missing_fields:
        chips = "".join(
            f'<span class="chip warn">{_esc(field.title())}</span>'
            for field in missing_fields
        )
        missing_summary = f'<div class="missing-summary"><span class="filter-label">Missing</span>{chips}</div>'

    def _required_class(value: str | None) -> str:
        return " required" if not value else ""

    def _required_hint(value: str | None) -> str:
        if value:
            return ""
        return '<div class="field-hint warn">Required for approval.</div>'

    return _render_page(
        f"""
        <header class="topbar">
          <div class="brand">
            <div class="logo">AC</div>
            <div>
              <div class="brand-title">Artist Calendar</div>
              <div class="brand-sub">Event review</div>
            </div>
          </div>
          <div class="actions">
            <a class="button ghost" href="{_esc(return_url)}">Back</a>
            {'<button class="button ghost" type="button" data-modal-open="poster-modal">View poster</button>' if image_src else ''}
          </div>
        </header>
        <div class="card">
          <h1>{_esc(title)}</h1>
          <p>Update fields, then approve or reject.</p>
          {conf_pill}
          {missing_summary}
          <form method="post">
            <input type="hidden" name="poster_id" value="{_esc(poster_id)}">
            <input type="hidden" name="return" value="{_esc(return_url)}">
            <div class="field{_required_class(event['date'])}">
              <label>Date<span class="req">*</span></label>
              <input name="date" value="{_esc(event['date'])}">
              {_required_hint(event['date'])}
            </div>
            <div class="field">
              <label>Event name</label>
              <input name="event_name" value="{_esc(event['event_name'])}">
            </div>
            <div class="field{_required_class(event['venue'])}">
              <label>Venue<span class="req">*</span></label>
              <input name="venue" value="{_esc(event['venue'])}">
              {_required_hint(event['venue'])}
            </div>
            <div class="field{_required_class(event['city'])}">
              <label>City<span class="req">*</span></label>
              <input name="city" value="{_esc(event['city'])}">
              {_required_hint(event['city'])}
            </div>
            <div class="field{_required_class(event['province'])}">
              <label>Province<span class="req">*</span></label>
              <input name="province" value="{_esc(event['province'])}">
              {_required_hint(event['province'])}
            </div>
            <div class="field">
              <label>Time</label>
              <input name="time" value="{_esc(event['time'])}" placeholder="19:00">
            </div>
            <div class="field">
              <label>Ticket info</label>
              <input name="ticket_info" value="{_esc(event['ticket_info'])}">
            </div>
            <div class="field">
              <label>Status</label>
              <select name="status">
                <option value="active" {"selected" if event['status'] == "active" else ""}>active</option>
                <option value="cancelled" {"selected" if event['status'] == "cancelled" else ""}>cancelled</option>
                <option value="postponed" {"selected" if event['status'] == "postponed" else ""}>postponed</option>
              </select>
            </div>
            <div class="edit-actions">
              <button class="button" name="action" value="approve">Approve</button>
              <button class="button ghost" name="action" value="approve_next">Approve &amp; next</button>
              <button class="button ghost" name="action" value="save_pending">Keep pending</button>
              <button class="button secondary" name="action" value="reject">Reject</button>
            </div>
          </form>
        </div>
        {modal_html}
        """
    )


@app.post("/poster/<poster_id>/approve-all")
def approve_all(poster_id: str):
    _approve_all_events(poster_id)
    return redirect(f"/review/{poster_id}")


@app.post("/ingest")
def ingest() -> str:
    file = request.files.get("image")
    image_url_input = (request.form.get("image_url") or "").strip()
    store_local = False
    force_reextract = (request.form.get("force_reextract") or "").strip() == "1"
    source_post_id = None
    image_hash = None

    if file and file.filename:
        image_path = _save_uploaded_file(file)
        image_url_for_db = str(image_path)
        source_url = None
        source_type = "manual"
    elif image_url_input:
        try:
            image_path, resolved_url = _download_image(image_url_input)
            source_url = image_url_input
            source_type = _infer_source_type(image_url_input)
            store_local = _should_store_local_image(image_url_input, resolved_url)
            image_url_for_db = str(image_path) if store_local else resolved_url
            source_post_id = _extract_instagram_shortcode(image_url_input)
        except Exception as exc:
            return _render_page(
                f"""
                <header class="topbar">
                  <div class="brand">
                    <div class="logo">AC</div>
                    <div>
                      <div class="brand-title">Artist Calendar</div>
                      <div class="brand-sub">Download failed</div>
                    </div>
                  </div>
                  <a class="button ghost" href="/">Back</a>
                </header>
                <div class="card">
                  <h2>Download failed</h2>
                  <p>{exc}</p>
                </div>
                """
            )
    else:
        return _render_page(
            """
            <header class="topbar">
              <div class="brand">
                <div class="logo">AC</div>
                <div>
                  <div class="brand-title">Artist Calendar</div>
                  <div class="brand-sub">Upload error</div>
                </div>
              </div>
              <a class="button ghost" href="/">Back</a>
            </header>
            <div class="card">
              <h2>Missing image</h2>
              <p>Provide an image file or a valid image URL.</p>
            </div>
            """
        )

    image_hash = _hash_file(image_path)
    existing = _find_existing_poster(source_post_id, source_url, image_hash)
    if existing and not force_reextract:
        if store_local:
            _prune_remote_downloads()
        if source_url and not KEEP_REMOTE_DOWNLOADS and not store_local:
            try:
                if image_path.exists() and image_path.parent == UPLOAD_DIR:
                    image_path.unlink()
            except OSError:
                pass
        source_label = _esc(existing["source_month"] or "unknown")
        tour_label = _esc(existing["tour_name"] or "Untitled tour")
        created_label = _esc(_format_datetime(existing["created_at"]))
        reextract_action = ""
        if source_url:
            reextract_action = f"""
              <form action="/ingest" method="post" style="display:inline;">
                <input type="hidden" name="image_url" value="{_esc(source_url)}">
                <input type="hidden" name="force_reextract" value="1">
                <button class="button ghost" type="submit">Re-run extraction</button>
              </form>
            """
        return _render_page(
            f"""
            <header class="topbar">
              <div class="brand">
                <div class="logo">AC</div>
                <div>
                  <div class="brand-title">Artist Calendar</div>
                  <div class="brand-sub">Already imported</div>
                </div>
              </div>
              <a class="button ghost" href="/">New upload</a>
            </header>
            <div class="card">
              <h2>This poster is already in your library</h2>
              <p><strong>{_esc(existing["artist_name"])}</strong> · {tour_label} · {source_label}</p>
              <p style="color: var(--muted); font-size: 13px;">Imported {created_label}. Open the existing review to keep approvals consistent.</p>
              <div class="actions">
                <a class="button" href="/review/{existing['id']}">Review existing</a>
                <a class="button ghost" href="/poster/{existing['id']}">View details</a>
                {reextract_action}
              </div>
            </div>
            """
        )

    try:
        data = image_to_structured(str(image_path))
        if source_post_id and not data.get("source_post_id"):
            data["source_post_id"] = source_post_id
        if image_hash and not data.get("image_hash"):
            data["image_hash"] = image_hash
        if source_url:
            data["source_image_url"] = resolved_url
            data["source_image_path"] = str(image_path)
        summary = ingest_structured(
            data,
            db_path=DB_PATH,
            image_url=image_url_for_db,
            source_type=source_type,
            source_url=source_url,
        )
    except Exception as exc:
        return _render_page(
            f"""
            <header class="topbar">
              <div class="brand">
                <div class="logo">AC</div>
                <div>
                  <div class="brand-title">Artist Calendar</div>
                  <div class="brand-sub">Ingest failed</div>
                </div>
              </div>
              <a class="button ghost" href="/">Back</a>
            </header>
            <div class="card">
              <h2>Ingest failed</h2>
              <p>{exc}</p>
            </div>
            """
        )
    finally:
        if store_local:
            _prune_remote_downloads()
        if source_url and not KEEP_REMOTE_DOWNLOADS and not store_local:
            try:
                if image_path.exists() and image_path.parent == UPLOAD_DIR:
                    image_path.unlink()
            except OSError:
                pass

    poster_id = summary.get("poster_id")
    if poster_id:
        return redirect(f"/review/{poster_id}")

    return _render_page(
        """
        <header class="topbar">
          <div class="brand">
            <div class="logo">AC</div>
            <div>
              <div class="brand-title">Artist Calendar</div>
              <div class="brand-sub">Ingest complete</div>
            </div>
          </div>
          <a class="button ghost" href="/">New upload</a>
        </header>
        <div class="card">
          <h2>Ingest complete</h2>
          <p>Poster saved, but no review page is available.</p>
          <div class="actions">
            <a class="button ghost" href="/db">Go to library</a>
          </div>
        </div>
        """
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
