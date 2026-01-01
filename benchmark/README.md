# Benchmarking Tour Poster Extraction

This benchmark measures structured extraction quality on Thai tour-date posters.
It is designed to be reproducible and shareable.

See `benchmark/PROTOCOL.md` for the evaluation methodology and `benchmark/DATASET_CARD.md` for dataset details.

## Prerequisites
- `OPENROUTER_API_KEY` for ground truth + judge.
- `GEMINI_API_KEY` for Gemma predictions (optional).
- Ollama running locally for Qwen (`ollama serve`).

Optional environment variables:
- `OPENROUTER_REFERER` and `OPENROUTER_TITLE` (for OpenRouter attribution).
- `BENCH_USER_AGENT` (override download user-agent).

## Files and folders
- `docs/test_poster_urls.txt`: source URL list.
- `benchmark/models.txt`: default model list for predictions.
- `benchmark/images/`: downloaded posters (ignored by git).
- `benchmark/ground_truth/`: GPT-5.2 ground truth JSON (ignored by git).
- `benchmark/predictions/`: model outputs (ignored by git).
- `benchmark/judgements/`: judge scores (ignored by git).
- `benchmark/report/`: aggregated report (ignored by git).
- `benchmark/report/scatter.svg`: performance vs cost quadrant chart.

## Workflow

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

3) Run predictions:
```bash
./venv_artist/bin/python benchmark/benchmark.py predict \
  --manifest benchmark/manifest.json \
  --out benchmark/predictions \
  --models ollama:qwen2.5vl:3b gemini:gemma-3-27b-it
```

Use the default model list file:
```bash
./venv_artist/bin/python benchmark/benchmark.py predict \
  --manifest benchmark/manifest.json \
  --out benchmark/predictions \
  --models $(cat benchmark/models.txt)
```

Optional: cap prediction output tokens (Gemini/Ollama):
```bash
./venv_artist/bin/python benchmark/benchmark.py predict \
  --manifest benchmark/manifest.json \
  --out benchmark/predictions \
  --models ollama:qwen2.5vl:3b gemini:gemma-3-27b-it \
  --max-output 4096 \
  --ollama-timeout 600 \
  --ollama-context 16384
```

4) Judge predictions (OpenRouter Claude Sonnet 4.5):
```bash
./venv_artist/bin/python benchmark/benchmark.py judge \
  --manifest benchmark/manifest.json \
  --ground-truth benchmark/ground_truth \
  --predictions benchmark/predictions \
  --out benchmark/judgements \
  --model anthropic/claude-sonnet-4.5
```

Optional: cap judge output tokens:
```bash
./venv_artist/bin/python benchmark/benchmark.py judge \
  --manifest benchmark/manifest.json \
  --ground-truth benchmark/ground_truth \
  --predictions benchmark/predictions \
  --out benchmark/judgements \
  --model anthropic/claude-sonnet-4.5 \
  --max-output 2048 \
  --timeout 300
```

5) Build report:
```bash
./venv_artist/bin/python benchmark/benchmark.py report \
  --manifest benchmark/manifest.json \
  --ground-truth benchmark/ground_truth \
  --predictions benchmark/predictions \
  --judgements benchmark/judgements \
  --out benchmark/report
```

6) Generate cost/performance scatter plot:
```bash
./venv_artist/bin/python benchmark/benchmark.py plot \
  --report benchmark/report/summary.json \
  --out benchmark/report
```

7) Generate a comprehensive narrative report:
```bash
./venv_artist/bin/python benchmark/benchmark.py interpret \
  --report-dir benchmark/report \
  --out benchmark/report/final_report.md \
  --model openai/gpt-5.2 \
  --max-output 4096 \
  --ground-truth-quality silver
```

8) Publish a run (commit-ready):
```bash
./venv_artist/bin/python benchmark/benchmark.py publish \
  --report-dir benchmark/report \
  --out benchmark/published \
  --label baseline
```

## Notes
- Add `--limit N` to any step to cap cost during iteration.
- The benchmark uses prompts from `benchmark/prompts/`.
- Cost is computed from OpenRouter usage + pricing metadata when available.
- `schema_valid_rate` checks required keys + basic formats; `schema_strict_rate` also forbids extra keys.
- All model calls use temperature 0.1 (see `DEFAULT_TEMPERATURE` in `benchmark/benchmark.py`).
- For OpenRouter steps, `--max-output max` uses the model's advertised max completion limit.
- For Ollama predictions, default `--max-output half` uses half the model context length.
- Use `--timeout` to raise OpenRouter request timeout; use `--ollama-timeout` for local Ollama requests.
- Use `--ollama-context` to cap Ollama context length for speed; 8192–16384 is a good starting range.
- Use `--seed` to fix randomness (default: 23).
- Report outputs include `comparisons.md` with bootstrap CIs for pairwise model deltas.

## Scoring
`app_quality_score` (0-100) is the primary performance axis for the scatter plot. It is a weighted mix:
- Structured output score (40%): strict schema + JSON parse.
- Event match score (35%): weighted date/location/venue match per event.
- Top-level field score (15%): artist, handle, tour, contact, source month.
- Event count score (10%): penalizes extra/missing events.

Missing essential fields in predicted events apply up to a 10-point penalty.
