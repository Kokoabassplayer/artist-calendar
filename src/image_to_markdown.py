import json
import os
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from google import genai
from google.genai import types
import requests

# Load environment variables
import logging
from typing import Optional, Dict, Any, Union, List
from typing_extensions import TypedDict
from config import Config


# Define strict JSON schema for tour data extraction (database-ready)
class TourEvent(TypedDict):
    date: str  # YYYY-MM-DD format (required)
    event_name: Optional[str]  # Festival name, special show, etc.
    venue: Optional[str]  # Bar, restaurant, club name
    city: Optional[str]  # City in English
    province: Optional[str]  # Thai province in English (e.g., "Chiang Mai")
    country: str  # Default: "Thailand"
    time: Optional[str]  # Show time if available (e.g., "21:00")
    ticket_info: Optional[str]  # Price or ticket details
    status: str  # "active" or "cancelled"


class TourData(TypedDict):
    artist_name: str  # Band/artist name
    instagram_handle: Optional[str]  # For artist identification (e.g., "scrubb_official")
    tour_name: Optional[str]  # e.g., "December Tour 2024"
    contact_info: Optional[str]  # Booking contact if visible
    source_month: str  # YYYY-MM for versioning (e.g., "2024-12")
    events: List[TourEvent]

if not Config.GEMINI_API_KEY:
    logging.error("API key not found.")
    exit(1)

CLIENT = genai.Client(api_key=Config.GEMINI_API_KEY)
MODEL_NAME = "models/gemini-flash-latest"


def upload_to_gemini(path: str, mime_type: Optional[str] = None):
    """Uploads the given file to Gemini."""
    try:
        config = types.UploadFileConfig(mimeType=mime_type) if mime_type else None
        file = CLIENT.files.upload(file=path, config=config)
        logging.info(f"Uploaded file '{file.display_name}' as: {file.uri}")
        return file
    except Exception as e:
        logging.error(f"Error uploading file: {e}")
        exit(1)


def image_to_markdown(image_path: str) -> Optional[str]:
    """Converts the provided image into Markdown format."""
    try:
        config = types.GenerateContentConfig(
            temperature=0,
            topP=0.95,
            topK=40,
            maxOutputTokens=8192,
            responseMimeType="text/plain",
            systemInstruction=(
                "Convert the image to Markdown including headers, footers and subtexts. "
                "Return only Markdown without header symbols or code fences."
            ),
        )

        uploaded_file = upload_to_gemini(image_path, mime_type="image/jpeg")
        response = CLIENT.models.generate_content(
            model=MODEL_NAME,
            contents=[uploaded_file, "proceed"],
            config=config,
        )
        return response.text
    except Exception as e:
        logging.error(f"Error processing the image: {e}")
        return None


def download_image(image_url: str, save_path: str) -> bool:
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
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        logging.info(f"Downloaded image: {image_url} -> {save_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to download image from {image_url}: {e}")
        return False


def csv_to_markdown_with_extracted_data(
    csv_file, output_markdown_file=None, image_folder=None
):
    """Convert a classified CSV file into a Markdown file.

    The function downloads images flagged with ``is_tour_date == 1`` and uses
    :func:`image_to_markdown` to extract text from those images. The extracted
    content is written to a Markdown file alongside basic metadata from the CSV.

    Parameters
    ----------
    csv_file : str
        Path to the classified CSV file.
    output_markdown_file : str, optional
        Path of the Markdown file to write. If not provided, a file named
        ``<csv_file_basename>_<YYYY_MM>.md`` will be created in the current
        directory.
    image_folder : str, optional
        Directory used to store downloaded images. If not provided, a folder
        named ``<csv_file_basename>`` inside ``image_output`` in the current
        directory will be used.
    """
    base_name = os.path.splitext(os.path.basename(csv_file))[0]

    data = pd.read_csv(csv_file)

    required_columns = ["Profile", "Image URL", "URL", "is_tour_date", "Date"]
    if not all(col in data.columns for col in required_columns):
        raise ValueError(
            f"The CSV file must contain the following columns: {required_columns}"
        )

    tour_date_images = data[data["is_tour_date"] == 1]

    if not tour_date_images.empty:
        first_date = pd.to_datetime(tour_date_images.iloc[0]["Date"])
        year_month = first_date.strftime("%Y_%m")
    else:
        year_month = "unknown"

    if output_markdown_file is None:
        filename = f"{base_name}_{year_month}.md"
        output_markdown_file = Config.MARKDOWN_DIR / filename
        
    if image_folder is None:
        image_folder = Config.IMAGE_OUTPUT_DIR / base_name

    print(f"Markdown will be saved to: {output_markdown_file}")
    print(f"Images will be stored in: {image_folder}")

    # Ensure the image folder exists
    os.makedirs(image_folder, exist_ok=True)

    # Generate Markdown content
    markdown_lines = []
    for _, row in tqdm(
        tour_date_images.iterrows(),
        total=len(tour_date_images),
        desc="Processing images",
    ):
        profile_id = row["Profile"]
        date = row["Date"]
        image_url = row["Image URL"]
        post_link = row["URL"]

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
    full_markdown_content = "".join(markdown_lines)
    with open(output_markdown_file, "w", encoding="utf-8") as f:
        f.write(full_markdown_content)

    logging.info(f"Markdown content saved to {output_markdown_file}")
    
    # Summarize to JSON
    logging.info("Summarizing extracted content to JSON...")
    json_data = summarize_markdown_to_json_gemini(full_markdown_content)
    
    if isinstance(json_data, dict):
        json_output_file = output_markdown_file.with_suffix(".json")
        with open(json_output_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        logging.info(f"JSON summary saved to {json_output_file}")
    else:
        logging.error("Failed to generate valid JSON summary.")


"""
# Example usage
if __name__ == "__main__":
    csv_file = "/Users/kokoabassplayer/Desktop/python/palmy_classified.csv"  # Input CSV file
    csv_to_markdown_with_extracted_data(csv_file)
"""


def summarize_markdown_to_json_gemini(content: str) -> Union[TourData, str]:
    """
    Summarizes the extracted markdown content into a structured JSON object.
    Uses Gemini's response_schema to guarantee consistent output structure.
    
    Returns:
        A TourData dictionary, or an empty dict string on error.
    """
    prompt = f"""
    Extract tour data from this content:
    - artist_name: Band/artist name
    - tour_name: Tour title if visible (e.g., "December Tour 2024")
    - contact_info: Booking contact if visible
    - events: List of events with:
      - date: YYYY-MM-DD format
      - event_name: Festival or special event name
      - venue: Bar, restaurant, club name
      - city: City name in English
      - province: Thai province in English
      - country: Default "Thailand" unless foreign
      - time: Show time if visible (e.g., "21:00")
      - ticket_info: Price or ticket details if visible

    Content:
    {content}
    """

    config = types.GenerateContentConfig(
        temperature=0,
        responseMimeType="application/json",
        responseSchema=TourData,
    )

    try:
        response = CLIENT.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=config,
        )
        logging.info(f"Gemini Raw Response: {response.text}")
        json_data = json.loads(response.text or "{}")
        return json_data
    except Exception as e:
        logging.error(f"Error parsing JSON from Gemini response: {e}")
        return "{}"
