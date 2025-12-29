# Artist Calendar - Persistent Context

## Context (what exists now)
- Repo pipeline: scrape Instagram posts -> CSV -> classify tour posters -> OCR to
  Markdown/JSON. Outputs: `CSV/raw`, `CSV/classified`, `TourDateMarkdown`,
  `TourDateImage`.
- Tableau dashboard has 3 views: Calendar, Artist near me, Backend.
- Calendar fields (from Tableau bootstrapSession):
  - Artist, show date (day/month/year/weekday, year-month), location
    name/province/country/note, category, status, special note, map URLs,
    lat/long, social/contact links.
- Artist near me fields:
  - Artist, show date (months/years), location name/province/country/note,
    category, status, map URLs, lat/long.
- Backend fields:
  - Spotify popularity/followers, quadrant color, rank spotify, is_updated,
    music label, insert date, artist name, Facebook link, artist image.
- Images are highly variable (dense text, neon/glow, multi-column, mixed
  Thai/English, small fonts), so extraction must be layout-aware with QA.
- Existing `database/schema.sql` is a good starting point (artists, posters,
  events, user prefs, saved events) but needs production extensions.

## Future production (what we will build)
- Product: mobile-first web app (later native) that replaces Tableau.
- Inputs: (1) automated crawl from social/web, (2) user-uploaded tour posters.
- Processing: classify poster -> OCR + layout parse -> structured events -> QA
  review -> write to database.
- Database: Supabase/Postgres v1 (free tier), with schema upgrades:
  - Raw OCR text + confidence, extraction model/version, review status,
    reviewer, provenance (source platform/post ID/job ID), normalized locations.
- Core features:
  - Calendar view, map/near-me discovery, filters (artist/province/category),
    event list with maps, artist profiles with socials/contacts.
  - Backend ops view for update prioritization and ingestion status.
  - Search, saved events, notifications/alerts.
- Non-functional:
  - Observability (logs, metrics), retries and QA pipeline, caching for maps,
    data normalization + dedupe, clear audit trail.
