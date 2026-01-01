# Published Benchmark Runs

Store commit-ready results here. Each run should live in a timestamped folder created by:

```bash
./venv_artist/bin/python benchmark/benchmark.py publish --report-dir benchmark/report --out benchmark/published --label <label>
```

Each run folder should include:
- `summary.md` and `summary.json`
- `scatter.svg`
- `comparisons.md` and `comparisons.json`
- `meta.json`
- `final_report.md` (narrative interpretation)
- `run_metadata.json`

Do not add raw poster images to this folder.
