# Artist Calendar Scraper

This repository contains a collection of scripts for scraping Instagram posts for specific artists, classifying images that depict tour dates using the Gemini API, and generating Markdown summaries of the extracted data.

## Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   The core scripts rely on `instaloader`, `google-generativeai`, `pandas`, `tqdm`, `python-dotenv`, and `Pillow`.
3. **Create a `.env` file**
   Place a `.env` file in the project root containing your Gemini API key:
   ```ini
   GEMINI_API_KEY=your_api_key_here
   ```
4. **(Optional) Configure Instagram credentials**
   The pipeline scripts prompt for login credentials when required. You can also modify the scripts to read `INSTAGRAM_USER` and `INSTAGRAM_PASS` environment variables if preferred.

## Environment Variables

- `GEMINI_API_KEY` – API key for the Google Gemini service used to classify images and convert them to Markdown. Loaded from the `.env` file.
- `INSTAGRAM_USER` and `INSTAGRAM_PASS` (optional) – credentials for Instaloader if you prefer not to hardcode them.

## Usage

### 1. Scrape and Classify
Run the full pipeline to scrape posts, classify tour date images, and generate Markdown:
```bash
python src/ig_tour_date_pipeline.py
```
Adjust the artist usernames and date range inside the script to suit your needs.

### 2. Classify an Existing CSV
If you already have a CSV produced by the scraper, you can classify the images separately:
```bash
python src/test_classifier_CSV.py
```
This script loads an input CSV, determines which images depict tour dates, and writes a new file with a `is_tour_date` column.

### 3. Convert Classified Images to Markdown
Once you have a classified CSV, extract the tour dates and produce Markdown files:
```bash
python src/test_extract_csv
```
The `image_to_markdown` module will download each image, analyze it with Gemini, and write the result to a Markdown file.

### 4. Summarize Markdown Files
To generate a summarized JSON of all Markdown files in a directory:
```bash
python src/summarize_markdown.py
```

## Notes
- Output folders such as `CSV/`, `TourDateImage/`, and `TourDateMarkdown/` are listed in `.gitignore` and will be created automatically by the pipeline if they do not exist.
- The pipeline scripts are provided as examples and may need adjustments (file paths, usernames, or date ranges) to match your environment.
