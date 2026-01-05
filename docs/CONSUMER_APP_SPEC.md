# Consumer App Spec (Zero-Cost MVP)

## Goal
Ship an AI-first consumer web app with a liquid-glass interface that turns tour posters into clean event listings, map links, and calendar-ready plans. The MVP must run at $0 on free tiers.

## Problem Statement
Fans waste time hunting posters, manually reading dates, typing events into calendars, and searching map locations for shows. The app removes that friction so people can discover shows and plan nights out in minutes.

## Non-Goals (MVP)
- Native app store release (Apple/Google fees).
- File uploads or long-term image storage.
- Complex analytics or admin tooling.

## Product Experience
- Mobile-first PWA that feels native.
- Liquid-glass UI: layered translucency, blur, soft edge highlights, gradient depth.
- Fast intake: paste a URL, get events, review inline.
- Consumption-first: users should see dates, locations, and "add to calendar" immediately.
- Review feels like a focused editor: one primary action, clear next step.
- AI-first: extraction, normalization, and suggestions are the default experience.

## Design Philosophy (Jony-Ive Style)
- Clarity over cleverness. Every interaction should feel inevitable.
- Reduce to the essential. Remove any UI that doesn't earn its place.
- Tactile calm. Depth and glass are cues for focus, not decoration.
- Continuity. The poster, data, and actions stay in one place.
- Craft. Micro-details (spacing, weight, motion) are the product.

## Visual Design Checklist (Liquid Glass)
- Layout: 8/12/16 spacing system, generous vertical rhythm, no cramped stacks.
- Typography: display serif for headings, clean grotesk for body; avoid text clutter.
- Glass surfaces: 8-16px blur, 6-12% opacity fill, subtle 1px highlight.
- Depth: 2-3 layers max; use shadow sparingly with soft edges.
- Color: warm neutral base, one cool accent; avoid neon.
- Motion: 150-250ms ease, gentle spring on sheet reveal, never bounce.
- Focus: one primary action per screen; secondary actions are soft buttons.
- Imagery: poster always visible near the editor; tap-to-zoom standard.

## UI Component Spec (Liquid Glass)
- Glass Card: 16px radius, 1px highlight, blur background, soft shadow; use for content blocks.
- Glass Sheet (mobile): bottom sheet with 20px top radius, backdrop dim 50%.
- Primary Button: solid accent, 12px radius, full-width on mobile.
- Secondary Button: translucent fill with 1px border, same height as primary.
- Pill/Badge: 999px radius, small text, soft tint; avoid more than 3 per row.
- Input Field: 12px radius, subtle border; required state uses warm tint only.
- Poster Preview: tap-to-zoom, max-height 180px inside editor.
## User-Facing Flows
1. Discover upcoming shows (by location, date, or artist).
2. Follow favorite artists and get a personalized feed.
3. Open an event for map + calendar actions.
4. Add to calendar with one tap (ICS export link).
5. Share with friends (link with poster + event summary).

## AI-First Principles
- AI performs the heavy lifting; humans confirm, not retype.
- Provide confidence and provenance so users can trust outputs.
- Offer a fast correction loop (edit inline, re-run on demand).
- Degrade gracefully when AI quotas are hit (manual entry with smart defaults).

## AI UX (Concrete Behaviors)
- Show confidence per event and highlight missing fields only when needed.
- Always show the poster alongside the editor to reconcile details quickly.
- One-tap retry for a single event if extraction looks wrong.
- Auto-normalize times, dates, and city/province formatting before review.
- Keep a transparent audit trail: source URL, extraction time, model used.

## Key Screens
- Home feed (upcoming shows + followed artists)
- Discover (search + filters, including table view for power users)
- Event detail (map, calendar, share)
- Artist page (tour list + follow)
- Poster intake + review (internal tool)

## Architecture (Free-Tier)
- Frontend: Expo + React Native Web (single codebase for web + mobile feel).
- Hosting: Cloudflare Pages (web).
- API: Cloudflare Workers (Hono).
- Database: Cloudflare D1 (SQLite).
- Auth: Magic-link email (Workers). Keep it simple.
- Inference: Free-tier LLMs only; throttle and show manual fallback when quotas hit.

## Constraints
- URL-only ingest. If the source image disappears, the poster preview disappears.
- LLM calls must stay under free quotas (rate-limit in API).
- No paid storage or background queues in MVP.

## Core Flows
1. Sign in (magic link).
2. Paste poster URL.
3. LLM extracts structured events.
4. Review in glass UI (inline editor).
5. Approve or edit and approve.
6. Event appears in the user-facing feed with map + calendar actions.

## Data Model (MVP)
Tables (D1):
- users (id, email, created_at)
- user_profiles (user_id, display_name, home_city, home_province)
- user_follows (user_id, artist_name, created_at)
- posters (id, user_id, image_url, source_url, source_month, tour_name, status, created_at)
- events (id, poster_id, date, event_name, venue, city, province, time, status, location_type, review_status)
- user_events (user_id, event_id, saved_at, calendar_added_at)

## UI Design System (Liquid Glass)
- Base surface: semi-transparent cards with backdrop blur.
- Layering: subtle depth with gradient backdrops and soft highlights.
- Motion: 150-250ms easing on open/close and focus changes.
- Typography: display serif + clean grotesk body.

## Error Handling
- If LLM fails or quota exceeded: show manual entry UI with clear messaging.
- If URL is not an image: show "unsupported link" with retry guidance.

## Roadmap
MVP (free):
- Liquid-glass PWA
- URL ingest only
- Basic auth
- Manual fallback
- User feed (upcoming events + follow list)
- Map + calendar actions (ICS download link)

Next:
- File uploads and storage
- Better model routing + caching
- Native app builds
- Push notifications for followed artists

## Market Reference
Comparable products for inspiration and gap analysis:
- Bandsintown (artist follow + show alerts)
- Songkick (tour discovery + tracking)
- Setlist.fm (show history, not planning-focused)
- Ticketing platforms (Ticketmaster/Live Nation/SeatGeek)
- Local ticketing (varies by region)

## Differentiation
- Poster-first ingestion: convert the primary real-world source into structured data.
- Calendar-first planning: one tap to map + calendar, no manual typing.
- Local focus: works for regions where poster images are the dominant format.
- Lightweight and respectful: fast, simple, and avoids heavy ticketing friction.

## Monetization (Post-MVP)
- Affiliate ticket links (where available).
- Premium features: calendar sync, smart reminders, follow limits, saved searches.
- Organizer tools: upload posters + verify events, analytics dashboard.
- Venue/artist pages: promoted placements with clear labels.
- API access for partners (media, venues, agencies).

## Open Questions
- Preferred magic-link email provider?
- Which free LLM source should be primary fallback?
- Should we require users to confirm poster ownership?
