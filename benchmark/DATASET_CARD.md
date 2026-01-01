# Dataset Card: Thai Tour Poster Benchmark

## Summary
A curated set of Thai tour-date poster images used to evaluate structured extraction quality for the ArtistCalendar app.

## Data sources
- Instagram posts listed in `docs/test_poster_urls.txt`.
- Each URL corresponds to a single poster image.

## Collection process
- URLs are collected manually from public artist pages.
- Images are downloaded at evaluation time via `benchmark/benchmark.py download`.

## Languages and regions
- Primary language: Thai (with occasional English).
- Primary geography: Thailand.

## Intended use
- Benchmarking model accuracy for poster-to-JSON extraction.
- Comparing model quality vs cost for production selection.

## Out-of-scope use
- Training or fine-tuning models.
- Redistribution of the raw images.

## Annotations
- Ground truth is stored as JSON following the schema in `benchmark/prompts/ground_truth.txt`.
- Publishable runs require two independent human annotators plus adjudication.

## Quality control
- Inter-annotator agreement is measured on event counts and key fields.
- Structured output is validated with strict schema checks.

## Privacy and licensing
- Posters are sourced from public Instagram pages.
- Rights remain with original creators; do not republish images in this repo.
- This dataset is provided as URL references only.

## Limitations
- Poster styles and typography vary; OCR difficulty is uneven.
- Geographic bias toward Thailand and Thai-language content.
- Dataset size is limited and may not represent all poster designs.

## Maintenance
- Update URL list by appending new links to `docs/test_poster_urls.txt`.
- Record dataset hash and run metadata in `benchmark/published/` for traceability.
