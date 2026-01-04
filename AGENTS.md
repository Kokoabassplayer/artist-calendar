# Repository Guidelines

## Project Structure & Module Organization
`app/src/` contains the core extraction and storage logic: `image_to_structured.py` (Gemini extraction) and `local_db.py` (SQLite writes). `app/scripts/` provides runnable entry points such as the Flask ingest UI (`local_ingest_ui.py`) and a JSON ingest helper (`ingest_local.py`). `app/database/` holds `schema_local.sql` for the local database schema. `docs/` captures product notes and design context. Runtime outputs live under `app/output/` (uploads, SQLite DB) and are ignored by git.

## Build, Test, and Development Commands
- `python -m venv venv_artist && source venv_artist/bin/activate` (optional venv)
- `pip install -r requirements.txt` installs dependencies
- `python app/scripts/local_ingest_ui.py` runs the local ingestion UI
- `python -m playwright install chromium` installs browser support for complex URLs (optional)
- `python app/src/image_to_structured.py path/to/poster.jpg --output app/output/poster.json` extracts JSON from a poster
- `python app/scripts/ingest_local.py app/output/poster.json --db app/output/local.db` stores structured JSON in SQLite
- `python app/scripts/test_llm_api.py` verifies Gemini connectivity

## Coding Style & Naming Conventions
Python, 4-space indentation. `.flake8` sets `max-line-length = 120`. Use `snake_case` for functions/modules and `PascalCase` for classes. Prefer `pathlib.Path` for filesystem paths in new code.

## Testing Guidelines
There is no automated test suite yet. Use a quick manual smoke check: run the UI, upload a poster, and verify new rows appear in `app/output/local.db`.

## Commit & Pull Request Guidelines
Commit messages are short, imperative, sentence case (e.g., “Refine extraction confidence and outputs”). PRs should include a brief summary, verification steps, and screenshots for UI changes.

## Configuration & Secrets
Set credentials via `.env` or environment: `GEMINI_API_KEY` (required), `GEMINI_MODEL` and `JINA_API_KEY` (optional), plus runtime knobs like `LOCAL_DB_PATH`, `KEEP_REMOTE_DOWNLOADS`, and `REMOTE_CACHE_MAX_FILES`. Never commit `.env` or generated output directories.
