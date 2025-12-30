# Artist Calendar - Dashboard Discovery (Initial)

> Note: This document preserves legacy Tableau/pipeline discovery notes.
> The current app in this repo focuses on local poster ingestion; see `README.md`.

This document summarizes what we can infer from the existing Tableau Public
dashboard and the current data pipeline in this repo. It is intentionally
lightweight and focused on enabling a future web/mobile application.

## Purpose
- Replace the Tableau dashboard with a custom web app (browser-first).
- Keep the door open for a future mobile app (App Store / Play Store).
- Preserve the current features: artist filtering, tour dates, maps, and links.

## What the current dashboard shows (from live page snapshot)
- Filter Step 1: Select artist (list includes "Da Endorphine").
- Filter Step 2: Select province (location filter).
- Filter Step 3: Select show category (event type).
- Calendar-style list of shows with artist name and date.
- Map visualization with location markers and Google Maps links.
- Social links: Facebook, Instagram, Twitter, TikTok, YouTube, Spotify,
  YouTube Music, Apple Music.
- Contact info: mobile, email, LINE.
- Buttons: "Artist near me" view, "Backend" view, feedback form.

## Visual inspection (Playwright)
- Header: artist profile image, artist name, and month/year context.
- Filters live at the top-right; changing artist updates calendar/list/map.
- Calendar grid uses category-specific icons on show dates.
- Event list shows category + venue/province, with a Google Maps pin per row.
- Thailand map includes markers and looks Mapbox-based.
- Footer includes social icons and creator credits.
- Observed data quality issues: some rows show "Null" location entries.
- Observed categories: Pub/Bar, Event, Concert, Festival, Internal.

## Tab: Artist near me (ARTISTCALENDA2)
- Filters are reordered: province, category, artist.
- Defaults show "(None)" and no data until filters are set.
- Focus is on map-based discovery by location/date.
- Navigation includes links back to calendar and to Backend.
- In this session the province filter list returned "No Items" (possibly a
  data-load or permissions issue).
- BootstrapSession field captions captured (Artist near me view):
  - Artist Name, Artist Name Parameter
  - Show Date (Months/Years), Show Date (Month / Year) Parameter
  - Location Name/Note/Province/Country, Location Lat/Long
  - Google Maps URL lat long, GOOGLE_MAP_URL
  - Show Category, Status, Special Note
  - Visual helpers: date label, color legend label

## Tab: Calendar (เล่นวันไหนบ้าง?) - deeper
- Event list rows are clickable and open Google Maps search with the location
  string (e.g., `maps/search?api=1&query=<venue+province+country>`).
- List/Map tooltip fields include: Show Date, Special Note, Location Country,
  Show Category, Location Name/Province/Note, Status.
- Map includes lat/long fields via Google Maps URL and `GOOGLE_MAP_URL`.
- Social/contact sections are driven by per-artist link fields:
  Facebook, Instagram, Twitter, TikTok, YouTube, Spotify, YouTube Music,
  Apple Music, Contact Mobile, Contact Email, Contact Line.
- Filter values observed in this session:
  - Step 1 (Artist): COCKTAIL, Da Endorphine.
  - Step 2 (Province): กรุงเทพมหานคร, นนทบุรี, ร้อยเอ็ด, ราชบุรี.
  - Step 3 (Category): ▲ Concert, ● Pub/Bar, ◼ Event, ⨉ Internal.
- Filters are labeled "Inclusive" which implies multi-select in Tableau.
- BootstrapSession field captions captured (Calendar view):
  - Artist Name, Artist Name Parameter
  - Show Date (Months), Show Date (Years), Show Date (Month / Year) Parameter
  - Day/Month/Year/Weekday derived fields, Year Month, Week-updated
  - Location Name, Location Note, Location Province, Location Country
  - Location Lat, Location Long, Google Maps URL lat long, GOOGLE_MAP_URL
  - Show Category, Status, Special Note
  - Social/contact: Facebook, Instagram, Twitter, Tikktok, Youtube,
    Youtube Music, Spotify, Apple Music, Contact Mobile, Contact Email,
    Contact Line
  - Visual helpers: MAP COLOR, Measure Names, color legend label

## Tab: Backend (Backend)
- Explains data update prioritization using Spotify popularity + followers.
- Quadrant chart splits artists into Superstars / Rising Stars / Hidden Stars.
- Filter: Music Label; Highlight: Artist Name.
- Legend for "Is Updated" (visual status markers).
- Update timestamp displayed (e.g., 2025-03-03).
- Music Label filter supports search and includes values like:
  123records, BEC-TERO, BOXX MUSIC, Gene Lab, Genie Records, GMM Grammy,
  Grammy Gold, LOVEiS ENTERTAINMENT, ME Records, Smallroom, SpicyDisc,
  Tero Music, WARMLIGHT!, What The Duck, White Music, WHOOP Music, plus Null.
- Highlight Artist Name list shows ~149 artists (includes Thai names);
  selecting one enables a "Clear Search" button.
- Clicking an artist in the list opens a Facebook search and shows
  Keep Only / Exclude actions (indicates Facebook link field per artist).
- Update-group filter (สีเขียวหมดแล้ว?) options: All, Null, Hidden Stars,
  Rising Stars, Superstars.
- Chart fields referenced: Followers, Popularity, Music Label, Insert date,
  Is Updated, Artist Name, Facebook (Artist Profile1).
- BootstrapSession field captions captured (Backend view):
  - AVG(Followers), AVG(Popularity)
  - Artist Name1, Music Label (Artist Profile1), Insert date
  - Is Updated (Artist Profile1), rank spotify, quadrant color
  - Circle Image Url (Artist Profile1), Facebook (Artist Profile1)

## Share / Embed (Tableau Public)
- Share dialog exposes a Tableau embed code with shared view ID `PF8Y3DSHK`.
- Share link format:
  `https://public.tableau.com/shared/PF8Y3DSHK?:display_count=n&:origin=viz_share_link&:embed=y`
- Static image URL pattern (from embed code):
  `https://public.tableau.com/static/images/PF/PF8Y3DSHK/1.png`

## Download options (Tableau)
- Available: Image, PDF, PowerPoint.
- Data/Crosstab download options are not exposed in this view.

## Operational notes (from console + behavior)
- Repeated 403 responses from Tableau resources during filter interactions.
- Map layer warnings in console (likely Mapbox style expressions).
- Some filter lists appear scoped to current artist/month context.


## Artifacts captured
- `docs/dashboard-initial.png` (initial view)
- `docs/dashboard-filter-cocktail.png` (artist switched to COCKTAIL)
- `docs/dashboard-artist-near-me.png` (Artist near me tab)
- `docs/dashboard-backend.png` (Backend tab)

## Legacy pipeline (removed)
These modules were part of the old Instagram/CSV pipeline and are no longer
present in the repo:
- `src/ig_scraper.py`: Scraped Instagram posts to CSV.
- `src/tour_date_classifier.py`: Classified images as tour-date or not.
- `src/image_to_markdown.py`: Extracted poster text to Markdown/JSON.
- Outputs used to live in `CSV/raw`, `CSV/classified`, `TourDateMarkdown`,
  and `TourDateImage`.

## Image variability (TourDateImage samples)
- Posters vary widely: dense text, neon/glow, heavy backgrounds, and photos.
- Layouts include single column, multi-column, and stacked date lists.
- Mixed Thai/English with abbreviations; dates appear as D/M, DD/MM, and
  month-name formats; some include time ranges and contact lines.
- Text size is often small; some images are low-contrast or stylized fonts.

## Extraction implications
- OCR needs layout-aware parsing (columns/rows) and language mix support.
- Pre-processing helps (contrast, sharpening, background suppression).
- Store raw OCR + confidence per field, and allow human correction.

## Inferred data fields (required for app parity)
- Artist: name, Instagram handle.
- Show date: date, day, month, year.
- Location: venue, city, province, country.
- Category: show type (e.g., pub/bar, concert, event, internal).
- Coordinates: latitude, longitude (for map pins).
- Status: active/cancelled.
- Notes: special note, ticket info, time.
- Links: Google Maps URL, post URL.
- Social/Contact: Facebook, Instagram, Twitter, TikTok, YouTube, Spotify,
  YouTube Music, Apple Music, phone, email, LINE.

## Gaps / Unknowns
- Tableau data source schema and storage (not visible from public view).
- Canonical show categories and statuses.
- Geocoding rules (how lat/long are derived).
- Data refresh cadence and change history.
- Data quality and cleanup rules (duplicate posts, multi-day tours, etc.).

## Risks and constraints
- Instagram scraping is fragile and may violate ToS; access limits and 2FA are
  operational risks.
- Gemini-based classification and extraction are probabilistic and need QA
  checks and retries.
- Map performance and rate limits require caching and pagination.

## Suggested target architecture (web-first, mobile-ready)
- Ingestion service (Python) runs on schedule, writes to a database.
- Database: Postgres (Supabase is a strong fit for auth + REST + storage).
- API layer: REST/GraphQL, with read-optimized endpoints for filtering.
- Frontend: React/Next.js with a map provider (Mapbox/Google Maps).
- Observability: logs, error tracking, ingestion metrics, data health checks.

## Opportunities to make it better (web app)
- True global search across artists/venues/notes, not limited to month view.
- Location-aware discovery (near-me) with clustering and radius filters.
- Data QA tooling: manual corrections, duplicate detection, cancel/reschedule.
- Faster maps and lists via cached tiles + paginated results.
- Subscriptions/alerts for artist or location changes.
- Backend queue view that ties Spotify priority to ingestion status.

## Next investigation tasks
- Export or inspect Tableau data schema (as owner).
- Define canonical data model and normalization rules.
- Decide source of truth: Instagram + manual overrides + verified submissions.
- Build a prototype API with filter params and map-friendly responses.
