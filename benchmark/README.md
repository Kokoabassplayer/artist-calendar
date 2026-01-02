# Benchmarking Tour Poster Extraction

This benchmark measures structured extraction quality on Thai tour-date posters.
It is designed to be reproducible and shareable.

See `benchmark/PROTOCOL.md` for the evaluation methodology and `benchmark/DATASET_CARD.md` for dataset details.

## Prerequisites
- `OPENROUTER_API_KEY` for ground truth, predictions, and judge.
- `GEMINI_API_KEY` only if you choose to run Google Gemini directly (optional).

Optional environment variables:
- `OPENROUTER_REFERER` and `OPENROUTER_TITLE` (for OpenRouter attribution).
- `BENCH_USER_AGENT` (override download user-agent).

## Files and folders
- `docs/test_poster_urls.txt`: source URL list.
- `benchmark/models.txt`: candidate OpenRouter model list (not all are vision-capable).
- `benchmark/models_vl.txt`: vision-capable OpenRouter models for image predictions.
- `benchmark/images/`: downloaded posters (ignored by git).
- `benchmark/ground_truth/`: GPT-5.2 ground truth JSON (ignored by git).
- `benchmark/runs/<run_id>/`: per-run outputs (predictions, judgements, report, logs).
- `benchmark/published/`: shareable reports copied from a run.

## Workflow

Set a run ID to keep outputs grouped:
```bash
RUN_ID=20260101-153411-gemini-gemma-temp02
```

1) Download posters:
```bash
./venv_artist/bin/python benchmark/benchmark.py download \
  --urls docs/test_poster_urls.txt \
  --out benchmark/images \
  --manifest benchmark/manifest.json
```

2) Generate ground truth (OpenRouter GPT-5.2):
```bash
./venv_artist/bin/python benchmark/benchmark.py ground-truth \
  --manifest benchmark/manifest.json \
  --out benchmark/ground_truth \
  --model openai/gpt-5.2
```

If JSON is truncated, rerun only error cases with higher tokens:
```bash
./venv_artist/bin/python benchmark/benchmark.py ground-truth \
  --manifest benchmark/manifest.json \
  --out benchmark/ground_truth \
  --model openai/gpt-5.2 \
  --max-output max \
  --retry-errors
```

3) Run predictions (OpenRouter vision models):
```bash
./venv_artist/bin/python benchmark/benchmark.py predict \
  --manifest benchmark/manifest.json \
  --out benchmark/runs/$RUN_ID/predictions \
  --models $(cat benchmark/models_vl.txt)
```

Optional: run the full candidate list (expect some to fail if not vision-capable):
```bash
./venv_artist/bin/python benchmark/benchmark.py predict \
  --manifest benchmark/manifest.json \
  --out benchmark/runs/$RUN_ID/predictions \
  --models $(cat benchmark/models.txt)
```

Optional: cap prediction output tokens (OpenRouter/Gemini):
```bash
./venv_artist/bin/python benchmark/benchmark.py predict \
  --manifest benchmark/manifest.json \
  --out benchmark/runs/$RUN_ID/predictions \
  --models $(cat benchmark/models_vl.txt) \
  --max-output 4096 \
  --timeout 300
```

4) Judge predictions (OpenRouter free judge example):
```bash
./venv_artist/bin/python benchmark/benchmark.py judge \
  --manifest benchmark/manifest.json \
  --ground-truth benchmark/ground_truth \
  --predictions benchmark/runs/$RUN_ID/predictions \
  --out benchmark/runs/$RUN_ID/judgements \
  --model openai/gpt-oss-120b:free
```

Optional: cap judge output tokens:
```bash
./venv_artist/bin/python benchmark/benchmark.py judge \
  --manifest benchmark/manifest.json \
  --ground-truth benchmark/ground_truth \
  --predictions benchmark/runs/$RUN_ID/predictions \
  --out benchmark/runs/$RUN_ID/judgements \
  --model openai/gpt-oss-120b:free \
  --max-output 2048 \
  --timeout 300
```

5) Build report:
```bash
./venv_artist/bin/python benchmark/benchmark.py report \
  --manifest benchmark/manifest.json \
  --ground-truth benchmark/ground_truth \
  --predictions benchmark/runs/$RUN_ID/predictions \
  --judgements benchmark/runs/$RUN_ID/judgements \
  --out benchmark/runs/$RUN_ID/report
```

6) Generate cost/performance scatter plot:
```bash
./venv_artist/bin/python benchmark/benchmark.py plot \
  --report benchmark/runs/$RUN_ID/report/summary.json \
  --out benchmark/runs/$RUN_ID/report
```

7) Generate a comprehensive narrative report:
```bash
./venv_artist/bin/python benchmark/benchmark.py interpret \
  --report-dir benchmark/runs/$RUN_ID/report \
  --out benchmark/runs/$RUN_ID/report/final_report.md \
  --model openai/gpt-oss-120b:free \
  --max-output 4096 \
  --ground-truth-quality silver
```

8) Publish a run (commit-ready):
```bash
./venv_artist/bin/python benchmark/benchmark.py publish \
  --report-dir benchmark/runs/$RUN_ID/report \
  --out benchmark/published \
  --label $RUN_ID
```

## Notes
- Add `--limit N` to any step to cap cost during iteration.
- The benchmark uses prompts from `benchmark/prompts/`.
- Cost is computed from OpenRouter usage + pricing metadata when available.
- `schema_valid_rate` checks required keys + basic formats; `schema_strict_rate` also forbids extra keys.
- All model calls use temperature 0.2 (see `DEFAULT_TEMPERATURE` in `benchmark/benchmark.py`).
- For OpenRouter steps, `--max-output max` uses the model's advertised max completion limit.
- For OpenRouter predictions, `--max-output max` uses the model's advertised completion limit.
- Use `--timeout` to raise OpenRouter request timeout.
- Use `--seed` to fix randomness (default: 23).
- Report outputs include `comparisons.md` with bootstrap CIs for pairwise model deltas.
- Structured outputs are enabled when a model supports `response_format` or `structured_outputs`.
- Only models that accept image inputs will produce predictions; use `benchmark/models_vl.txt` to avoid text-only models.
- `mistralai/mistral-small-3.1-24b-instruct:free` is disabled in `benchmark/models.txt` because the free tier has no image endpoints.

## Scoring
`app_quality_score` (0-100) is the primary performance axis for the scatter plot. It is a weighted mix:
- Structured output score (40%): strict schema + JSON parse.
- Event match score (35%): weighted date/location/venue match per event.
- Top-level field score (15%): artist, handle, tour, contact, source month.
- Event count score (10%): penalizes extra/missing events.

Missing essential fields in predicted events apply up to a 10-point penalty.
