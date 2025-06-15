# Artist Calendar

This project provides a set of scripts for scraping Instagram data and
converting it to Markdown. Some scripts require Instagram login
credentials.

## Environment Variables

Before running `src/ig_tour_date_pipeline.py` or `src/a_pipe.py`, set
the following variables in your environment or in a `.env` file:

- `IG_USERNAME` – Instagram username used for authentication
- `IG_PASSWORD` – password for the Instagram account

These scripts load environment variables using `python-dotenv`, so you
may create a `.env` file with these keys or export them in your shell.
