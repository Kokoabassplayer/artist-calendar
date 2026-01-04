# Artist Calendar

Local ingestion UI for tour posters. Upload an image or paste a URL, extract
structured event data with Gemini, and store results in a local SQLite database
for review.

## Setup

Python 3.10+ is recommended.

```bash
python -m venv venv_artist
source venv_artist/bin/activate
pip install -r requirements.txt
```

## Environment variables

- `GEMINI_API_KEY` (required)
- `GEMINI_MODEL` (optional, default: `models/gemma-3-27b-it`)
- `LOCAL_DB_PATH` (optional, default: `app/output/local.db`)
- `REPAIR_MISSING_CORE` (optional, `1` triggers a second-pass fill for missing date/venue/city/province)
- `KEEP_REMOTE_DOWNLOADS` (optional, `1` keeps remote images on disk)
- `REMOTE_CACHE_MAX_FILES` (optional, default: `200`)
- `JINA_API_KEY` (optional, improves URL image scraping fallback)

Create a `.env` file or export variables before running.

## Repository layout
- `app/`: local ingestion app (CLI + Flask UI + SQLite schema).
- `benchmark/`: poster extraction benchmark tooling and reports.

## Run the app

```bash
python app/scripts/local_ingest_ui.py
```

Open `http://127.0.0.1:5001` in your browser.

If you plan to ingest tricky URLs, install Playwright browsers once:

```bash
python -m playwright install chromium
```

## CLI helpers

- Extract structured data:

```bash
python app/src/image_to_structured.py path/to/poster.jpg --output app/output/poster.json
```

- Ingest structured JSON into SQLite:

```bash
python app/scripts/ingest_local.py app/output/poster.json --db app/output/local.db
```

- Test Gemini connectivity:

```bash
python app/scripts/test_llm_api.py
```

## Data locations

- SQLite DB: `app/output/local.db`
- Uploaded/remote cache images: `app/output/uploads`
