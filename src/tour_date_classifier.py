import logging
import json
from typing import Optional, TypedDict

from google import genai
from google.genai import types
from config import Config

if not Config.GEMINI_API_KEY:
    logging.error("API key not found.")
    exit(1)

CLIENT = genai.Client(api_key=Config.GEMINI_API_KEY)
MODEL_NAME = "models/gemini-flash-latest"


class ClassifierResult(TypedDict):
    is_tour_date: bool

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


def tour_date_classifier(image_path: str) -> Optional[int]:
    """
    Classify the given image as either a tour date or not.
    Returns 1 if tour date, 0 if not, or None on error.
    """
    try:
        config = types.GenerateContentConfig(
            temperature=0,
            topP=0.95,
            topK=40,
            maxOutputTokens=1024,
            responseMimeType="application/json",
            responseSchema=ClassifierResult,
            systemInstruction=(
                "Classify the image. Return a JSON object with a single field "
                "'is_tour_date' (boolean). True if the image clearly shows a tour "
                "date with artist, date and location. False otherwise."
            ),
        )

        uploaded_file = upload_to_gemini(image_path, mime_type="image/jpeg")

        response = CLIENT.models.generate_content(
            model=MODEL_NAME,
            contents=[uploaded_file, "analyze"],
            config=config,
        )
        result = json.loads(response.text or "{}")
        return 1 if result.get("is_tour_date") else 0

    except Exception as e:
        logging.error(f"Error processing the image: {e}")
        return None
