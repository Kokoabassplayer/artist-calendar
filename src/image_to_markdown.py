import os
from pathlib import Path
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
import google.generativeai as genai
import requests

# Load environment variables
dotenv_path = os.getenv("AC_DOTENV_PATH", Path(__file__).resolve().parents[1] / ".env")
load_dotenv(dotenv_path)

# Base directory for output files
BASE_DIR = Path(os.getenv("AC_DATA_ROOT", Path(__file__).resolve().parents[1]))
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

if not os.environ.get("GEMINI_API_KEY"):
    print("Error: API key not found.")
    exit()


def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini."""
    try:
        file = genai.upload_file(path, mime_type=mime_type)
        print(f"Uploaded file '{file.display_name}' as: {file.uri}")
        return file
    except Exception as e:
        print(f"Error uploading file: {e}")
        exit()


def image_to_markdown(image_path):
    """Converts the provided image into Markdown format."""
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-002",
            generation_config={
                "temperature": 0,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
                "response_mime_type": "text/plain",
            },
            #system_instruction="Convert the provided image into Markdown format. Ensure that all content from the page is included, such as headers, footers, subtexts, images (with alt text if possible), tables, and any other elements.\n\n  Requirements:\n\n  - Output Only Markdown: Return solely the Markdown content without any additional explanations or comments.\n  - No Delimiters: Do not use code fences or delimiters like ```markdown.\n  - Complete Content: Do not omit any part of the page, including headers, footers, and subtext.",
            system_instruction="""
                Convert the provided image into Markdown format, ensuring that all content from the page is included, such as headers, footers, subtexts, images (with alt text if possible), tables, and any other elements.

                Requirements:
                    •	No Header Symbols: Do not use any Markdown header symbols (#, ##, ###, etc.) under any circumstances. Structure the content using plain text, line breaks, or other formatting elements like bold, italics, or lists to indicate sections and subsections, but not header symbols.
                    •	Output Only Markdown: Return solely the Markdown content without any additional explanations or comments.
                    •	No Delimiters: Do not use code fences or delimiters like  ```markdown.
                    •	Complete Content: Include all content from the page without omitting any part, such as headers, footers, subtexts, tables, and images with appropriate alt text (if available).

                Output Format

                The output must be formatted entirely in valid Markdown without any header symbols. Use other Markdown formatting options (e.g., bold, italics, lists) to organize the content. Ensure that all page elements, including text, images, and tables, are represented correctly.

                RULES

                    1.	DO NOT USE ANY HEADER SYMBOLS (#, ##, ###, ETC.) UNDER ANY CIRCUMSTANCES. STRUCTURE CONTENT USING OTHER FORMATTING OPTIONS SUCH AS BOLD, ITALICS, OR LISTS.
                    2.	DO NOT OMIT ANY PART OF THE CONTENT, INCLUDING HEADERS, FOOTERS, AND SUBTEXTS.
                    3.	RETURN ONLY MARKDOWN CONTENT WITHOUT ANY EXPLANATIONS OR COMMENTS.
                    4.	DO NOT USE CODE FENCES OR DELIMITERS LIKE  ```markdown.
                """
        )

        uploaded_file = upload_to_gemini(image_path, mime_type="image/jpeg")

        chat_session = model.start_chat(
            history=[{
                "role": "user",
                "parts": [uploaded_file],
            }]
        )

        response = chat_session.send_message("proceed")
        return response.text
    except Exception as e:
        print(f"Error processing the image: {e}")
        return None


def download_image(image_url, save_path):
    """
    Downloads an image from a URL and saves it locally.

    Args:
        image_url (str): The URL of the image to download.
        save_path (str): The local path to save the image.

    Returns:
        bool: True if the image was successfully downloaded, False otherwise.
    """
    try:
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Downloaded image: {image_url} -> {save_path}")
        return True
    except Exception as e:
        print(f"Failed to download image from {image_url}: {e}")
        return False


def csv_to_markdown_with_extracted_data(csv_file):
    """
    Processes a CSV file, downloads images flagged with is_tour_date == 1,
    extracts data from the images, and generates Markdown content.

    Args:
        csv_file (str): Path to the CSV file.
    """
    # Generate output paths based on the input CSV file name
    base_name = os.path.splitext(os.path.basename(csv_file))[0]

    # Load the CSV file
    data = pd.read_csv(csv_file)

    # Check required columns
    required_columns = ['Profile', 'Image URL', 'URL', 'is_tour_date', 'Date']
    if not all(col in data.columns for col in required_columns):
        raise ValueError(f"The CSV file must contain the following columns: {required_columns}")

    # Filter rows with is_tour_date == 1
    tour_date_images = data[data['is_tour_date'] == 1]

    # Extract year and month from the first valid date
    if not tour_date_images.empty:
        first_date = pd.to_datetime(tour_date_images.iloc[0]['Date'])
        year_month = first_date.strftime("%Y_%m")
    else:
        year_month = "unknown"

    output_markdown_file = str(BASE_DIR / "TourDateMarkdown" / f"{base_name}_{year_month}.md")
    image_folder = str(BASE_DIR / "TourDateImage" / base_name)

    print(f"Markdown will be saved to: {output_markdown_file}")
    print(f"Images will be stored in: {image_folder}")

    # Ensure the image folder exists
    os.makedirs(image_folder, exist_ok=True)

    # Generate Markdown content
    markdown_lines = []
    for _, row in tqdm(tour_date_images.iterrows(), total=len(tour_date_images), desc="Processing images"):
        profile_id = row['Profile']
        date = row['Date']
        image_url = row['Image URL']
        post_link = row['URL']

        # Determine the local image path
        sanitized_date = date.replace(":", "").replace(" ", "_")
        image_filename = f"{profile_id}_{sanitized_date}.jpg"
        image_path = os.path.join(image_folder, image_filename)

        print(f"Processing image: {image_path}")
        if not os.path.exists(image_path):
            print(f"Downloading image: {image_url}")
            success = download_image(image_url, image_path)
            if not success:
                extracted_markdown = "Markdown extraction failed due to download error."
            else:
                extracted_markdown = image_to_markdown(image_path)
        else:
            print(f"Using existing image: {image_path}")
            extracted_markdown = image_to_markdown(image_path)

        # Create final Markdown content
        markdown_content = (
            f"## Instagram Profile: {profile_id}\n"
            f"- Post Date: {date}\n"
            f"- Tour Date Image URL: {image_url}\n"
            f"- Post Link: {post_link}\n\n"
            f"Extracted Tour Date Content:\n\n{extracted_markdown}\n\n"
        )
        markdown_lines.append(markdown_content)

    # Write Markdown content to file
    with open(output_markdown_file, 'w', encoding='utf-8') as f:
        f.writelines(markdown_lines)

    print(f"Markdown content saved to {output_markdown_file}")

"""
# Example usage
if __name__ == "__main__":
    csv_file = os.getenv("AC_SAMPLE_CSV", str(BASE_DIR / "palmy_classified.csv"))
    csv_to_markdown_with_extracted_data(csv_file)
"""

import json
import os
from dotenv import load_dotenv
import google.generativeai as genai


def summarize_markdown_to_json_gemini(content):
    prompt = f"""
    You are given the following Markdown content that includes artist tour dates and possibly contact info.

    Your task:
    1. Identify the artist's name.
    2. Identify any contact information if available.
    3. Extract events. Each event should have:
    - original_date_text: the exact date text as found (e.g. "5/12" or "3.12.2024")
    - parsed_date: a date in YYYYMMDD if you can infer the year and convert it; otherwise null.
    - event_name: name of the event or festival (if identifiable).
    - location: venue or place name (can be the same as event_name if not distinguishable).
    - country: "Thailand" by default unless a known foreign location like "ปอยเปต" indicates Cambodia, etc.

    If you are unsure, provide your best guess. If parsing fails, leave fields null as appropriate.

    Return only valid JSON in the following structure:

    ```json
    {{
    "artists": [
        {{
        "name": "Artist Name",
        "contact": "Contact Info if available",
        "events": [
            {{
            "original_date_text": "Date Text",
            "parsed_date": "YYYYMMDD or null",
            "event_name": "Event Name or null",
            "location": "Location or null",
            "country": "Country or null"
            }}
        ]
        }}
    ]
    }}

    Markdown content:
    {content}
    """

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-002",
        generation_config={
            "temperature": 0,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        },
    )

    response = model.generate_content(prompt)

    try:
        json_data = json.loads(response.text)
        return json_data
    except json.JSONDecodeError:
        return response.text

