import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("/Users/kokoabassplayer/Desktop/python/.env")

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

if not os.environ.get("GEMINI_API_KEY"):
    print("Error: API key not found.")
    exit()


def summarize_markdown(file_path):
    """Summarizes the content of a Markdown file using Gemini."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-002",
            generation_config={
                "temperature": 0,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            },
        )

        test_prompt = f"""

Analyze the following Markdown content and produce a JSON summary
suitable for database storage. The JSON should have this structure:

```json
{{
  "artists": [
    {{
      "name": "Artist Name",
      "contact": "Contact Info if available",
      "events": [
        {{
          "date": {{
            "year": YYYY,
            "month_name": "MonthName",
            "month_number": MM,
            "day": DD
          }},
          "location": "Name of venue or event location if available",
          "city": "City if available",
          "country": "Country if available",
          "event_name": "Event/Festival name if applicable"
        }}
      ]
    }}
  ]
}}

Requirements:
    • Include all artists mentioned in the Markdown.
    • Parse all events, extracting the year, month, and day.
    • The year can be assumed from the content (e.g., 2024 or 2025).
    • Use “December” and month_number: 12 if no month name is explicitly stated but implied.
    • For each event, if location or city is mentioned, include them.
    • If contact information (phone number, email, social handle) is found for
      an artist, include it in the “contact” field.
    • Omit fields if the information is not available.
    • Return only valid JSON that follows the given structure.

Markdown content:
{content}

            """

        response = model.generate_content(test_prompt)
        return response.text
    except Exception as e:
        print(f"Error summarizing file {file_path}: {e}")
        return None


def process_markdown_folder(folder_path):
    """Processes all Markdown files in the given folder."""
    for filename in os.listdir(folder_path):
        if filename.endswith(".md"):
            file_path = os.path.join(folder_path, filename)
            print(f"Summarizing {filename}:")
            summary = summarize_markdown(file_path)
            if summary:
                print(summary)
                print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    folder_path = (
        "/Users/kokoabassplayer/Desktop/python/ArtistCalendar/CombinedMarkdown"
    )
    process_markdown_folder(folder_path)
