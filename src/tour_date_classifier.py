import os
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

dotenv_path = os.getenv("AC_DOTENV_PATH", Path(__file__).resolve().parents[1] / ".env")
load_dotenv(dotenv_path)

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
            system_instruction="""
                Classify the given image as either a tour date or not. Return only `1` if the image depicts a tour date (a table or poster showing the artist's name, year, month, date of the event, along with the show's name and location). Return `0` if it does not. Do not provide any explanation. **Adapt for challenging images that may contain a mix of Thai and English text, complex designs, or cluttered visual elements.**

                # Steps

                1. **Extract and Analyze Text**
                - Extract all visible text from the image, handling both **Thai and English** text seamlessly.  
                - Focus on identifying key indicators, even if the text is interspersed or presented in a visually busy design.

                2. **Identify Required Indicators**
                - Search for the following elements in **either Thai or English**:
                    - **Artist's name** or name of the music event (e.g., a festival or show).  
                    - **Specific date** (year, month, and day).  
                    - **Event location** (venue or city).  
                - The image should have all these components to classify as a tour date.

                3. **Handle Complex and Multilingual Scenarios**
                - If text alternates between Thai and English, identify and combine related pieces of information across both languages to match the tour date criteria.
                - If the background is cluttered or visually complex:
                    - Prioritize extracting and interpreting the most legible text first.
                    - Ignore purely decorative or irrelevant content.

                4. **Validate Information**
                - Confirm that the extracted text satisfies the context of a tour date (name of artist, year, month, date, location).
                - If any of these required elements are missing, incomplete, or unclear, classify as `0`.

                5. **Classify the Image**
                - If all elements (artist, date, location) are present in the image, return `1`.  
                - Otherwise, return `0`.

                # Output Format

                Return a single value: `1` or `0`. Do not include any additional explanation or commentary.

                # Notes

                - **Step-by-step extraction and validation** are critical for multilingual text, ensuring consistency regardless of language mix (Thai and English).  
                - Ensure the system is robust against:
                - Cluttered or visually busy backgrounds.  
                - Text blending with design elements.  
                - Variations in text placement, font size, or alignment.  
                - Alternating or mixed Thai and English text.  
                - Ignore unrelated or decorative elements that do not match the context of a tour date.  
            """,
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

"""
# Example use
# Path to folder containing images
base_dir = Path(os.getenv("AC_DATA_ROOT", Path(__file__).resolve().parents[1]))
folder_path = base_dir / "image"

# Loop through all image files in the folder
for filename in os.listdir(folder_path):
    file_path = os.path.join(folder_path, filename)
    if os.path.isfile(file_path) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
        result = tour_date_classifier(file_path)
        if result is not None:
            print(f"Image: {filename}, is tour date: {result}")
"""
