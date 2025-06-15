# Artist Calendar

This project provides a set of scripts for scraping Instagram data and
converting it to Markdown. Some scripts require Instagram login
credentials. A small command line application is available under
`src/app.py` to run the full pipeline.

## Environment Variables

Before running `src/app.py`, `src/ig_tour_date_pipeline.py` or `src/a_pipe.py`, set
the following variables in your environment or in a `.env` file:

- `IG_USERNAME` – Instagram username used for authentication
- `IG_PASSWORD` – password for the Instagram account

These scripts load environment variables using `python-dotenv`, so you
may create a `.env` file with these keys or export them in your shell.

## Example usage

To run the full pipeline for one or more artists:

```bash
python src/app.py \
    --artists retrospect_official,another_band \
    --since 2024-01-01 --until 2024-12-31 \
    --output output --env-file .env
```

The generated CSV and Markdown files will be written under the
specified output directory.
