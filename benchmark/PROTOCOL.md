# Benchmark Protocol

## Purpose
This benchmark evaluates how well models extract structured tour data from Thai poster images for the ArtistCalendar app. The primary objective is **app-ready structured output** with high field accuracy and reliable schema adherence.

## Dataset definition
- **Source**: Instagram poster URLs listed in `docs/test_poster_urls.txt`.
- **Inclusion**: single-poster images that contain tour-date information.
- **Exclusion**: multi-image carousels, non-tour announcements, or posters without dates.
- **Versioning**: dataset identity is the SHA-256 hash of the URL list and manifest, captured in `benchmark/report/meta.json` and `benchmark/published/*/run_metadata.json`.

## Ground truth (gold)
For publishable results, use **human-verified ground truth**:
1. Two annotators independently extract JSON following the schema in `benchmark/prompts/ground_truth.txt`.
2. Resolve disagreements via adjudication and record the final JSON.
3. Track inter-annotator agreement (event count, date match, venue match).

LLM-generated ground truth is acceptable only as **silver data** for rapid iteration and must be labeled as such in reports.

## Evaluation metrics
- **Schema strict rate**: exact schema keys and types; no extra fields.
- **App quality score (0-100)**: weighted composite of structured output, top-level fields, event matching, and event count (weights in `benchmark/benchmark.py`).
- **App core score (0-100)**: same composite score, but event matching uses only date/venue/city/province/country (ignores time, ticket info, event name, status).
- **Event matching**: optimal global assignment (Hungarian) between gold and predicted events.
- **Missing field penalty**: reduces score for missing date/venue/city/province.

## Statistical reliability
- **Bootstrap CIs**: 1,000 resamples, seed 23, alpha 0.05.
- **Pairwise comparison**: bootstrap mean differences + p-values (`benchmark/report/comparisons.md`).

## Reproducibility
- Temperature fixed to 0.1 for all models.
- Fixed random seed (default: 23) for all supported models.
- Prompt hashes and scoring weights recorded in `benchmark/report/meta.json`.
- Use `benchmark/benchmark.py publish` to create a commit-ready run folder.

## Publishing notes
- Do not commit raw poster images.
- Clearly label runs as **gold** or **silver** ground truth.
- Include run metadata, summary tables, and the scatter plot in `benchmark/published/`.
