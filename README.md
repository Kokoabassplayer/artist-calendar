# Artist Calendar

This repository contains scripts for scraping Instagram posts, classifying tour date images, and generating Markdown summaries. Paths for data and configuration can be customized using environment variables.

## Configuration

- `BASE_DATA_DIR` – Base directory for generated CSV files, images, and Markdown files. Defaults to `data` in the current working directory.
- `ENV_PATH` – Path to a `.env` file containing API keys such as `GEMINI_API_KEY`. Defaults to `.env`.

Create the directories or override these variables before running the scripts. The `.env` file should define `GEMINI_API_KEY` used by the AI features.
