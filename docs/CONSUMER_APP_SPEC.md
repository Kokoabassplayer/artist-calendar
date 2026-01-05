# Consumer App Spec (Zero-Cost MVP)

## Goal
Ship a consumer-facing web app with a liquid-glass interface that lets users ingest tour posters by URL, extract structured events, and review/approve them. The MVP must run at $0 on free tiers.

## Non-Goals (MVP)
- Native app store release (Apple/Google fees).
- File uploads or long-term image storage.
- Complex analytics or admin tooling.

## Product Experience
- Mobile-first PWA that feels native.
- Liquid-glass UI: layered translucency, blur, soft edge highlights, gradient depth.
- Fast intake: paste a URL, get events, review inline.
- Review feels like a focused editor: one primary action, clear next step.

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

## Data Model (MVP)
Tables (D1):
- users (id, email, created_at)
- posters (id, user_id, image_url, source_url, source_month, tour_name, status, created_at)
- events (id, poster_id, date, event_name, venue, city, province, time, status, location_type, review_status)

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

Next:
- File uploads and storage
- Better model routing + caching
- Native app builds

## Open Questions
- Preferred magic-link email provider?
- Which free LLM source should be primary fallback?
- Should we require users to confirm poster ownership?
