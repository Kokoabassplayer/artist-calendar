# Database Design (vNext)

## Goals
- Store tour dates in a DB-friendly, normalized form with traceable provenance.
- Keep raw extraction output for reprocessing and audit.
- Support review/approval for noisy OCR results.
- Make app queries fast (upcoming events, artist pages, location views).

## Core Entities
- `artists`: canonical artist profile and contact info.
- `posters`: one poster image per month/version, tied to an artist and source.
- `extractions`: model outputs (raw + structured) per poster.
- `events`: normalized tour dates, linked to poster + extraction.
- `locations`: normalized venue/place info (optional, for dedupe).
- `user_preferences`, `user_saved_events`: app personalization.

## Relationships
- `artists` 1→N `posters`
- `posters` 1→N `extractions`
- `posters` 1→N `events`
- `events` N→1 `locations` (optional)
- `events` N→1 `extractions` (optional, for audit)

## Extraction Output Mapping
- `TourData.artist_name` → `artists.name`
- `TourData.instagram_handle` → `artists.instagram_handle`
- `TourData.contact_info` → `artists.contact_info` (or keep on `posters` if poster-specific)
- `TourData.tour_name` → `posters.tour_name`
- `TourData.source_month` → `posters.source_month`
- `TourData.events[]` → `events` rows:
  - `date` → `events.date`
  - `event_name` → `events.event_name`
  - `venue` → `events.venue`
  - `city` → `events.city`
  - `province` → `events.province`
  - `country` → `events.country`
  - `time` → `events.time`
  - `ticket_info` → `events.ticket_info`
  - `status` → `events.status`
  - raw strings → `events.date_text`, `events.time_text`, `events.raw_text`
- Store model output in `extractions.structured_json` and link `events.extraction_id`.

## Review Workflow
- New rows default to `events.review_status = 'pending'`.
- Approved rows are safe for public display.
- Keep reviewer metadata in `events.reviewed_by/reviewed_at/review_notes`.

## Notes
- `extractions` is service-role only by default to protect raw OCR.
- `locations` is optional; populate when geocoding succeeds.
- `posters.image_hash` supports dedupe across sources.
