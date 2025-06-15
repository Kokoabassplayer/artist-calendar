import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("/Users/kokoabassplayer/Desktop/python/.env")

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


def tour_date_classifier(image_path):
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
            system_instruction=(
                "Return '1' if the image clearly shows a tour date with artist,"
                " date and location. Otherwise return '0' with no explanation."
            ),
        )

        uploaded_file = upload_to_gemini(image_path, mime_type="image/jpeg")

        chat_session = model.start_chat(
            history=[
                {
                    "role": "user",
                    "parts": [uploaded_file],
                }
            ]
        )

        response = chat_session.send_message("proceed")
        return response.text
    except Exception as e:
        print(f"Error processing the image: {e}")
        return None


"""
# Example use
# Path to folder containing images
folder_path = "/Users/kokoabassplayer/Desktop/python/ArtistCalendar/image"

# Loop through all image files in the folder
for filename in os.listdir(folder_path):
    file_path = os.path.join(folder_path, filename)
    if os.path.isfile(file_path) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
        result = tour_date_classifier(file_path)
        if result is not None:
            print(f"Image: {filename}, is tour date: {result}")
"""
