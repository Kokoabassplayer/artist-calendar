import pandas as pd
import requests
import os
from io import BytesIO
from PIL import Image
import logging
from tqdm import tqdm
from tour_date_classifier import tour_date_classifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def classify_image_from_url(image_url, index):
    """Classify an image from a URL."""
    try:
        logging.info(f"Processing row {index}: {image_url}")

        # Validate URL
        if not image_url.startswith("http"):
            logging.warning(f"Skipping invalid URL at row {index}: {image_url}")
            return None

        # Download the image
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()

        # Open the image
        img = Image.open(BytesIO(response.content))

        # Save to a unique temporary file
        temp_file = f"temp_image_{index}.jpg"
        img.save(temp_file)

        # Classify the image
        result = tour_date_classifier(temp_file)

        # Clean up
        os.remove(temp_file)

        return result
    except Exception as e:
        logging.error(f"Error processing row {index}, URL: {image_url}: {e}")
        return None

def classify_images(input_csv, output_csv=None, output_folder=None):
    """
    Main function to classify images from a CSV file.

    Args:
        input_csv (str): Path to the input CSV file.
        output_csv (str, optional): Name of the output CSV file. Defaults to None.
        output_folder (str, optional): Directory where the output CSV file will be saved. Defaults to the same directory as the input CSV.
    """
    # Load the CSV file
    data = pd.read_csv(input_csv)

    # Ensure the column containing image links exists
    if 'Image URL' not in data.columns:
        raise ValueError("The CSV file must have a column named 'Image URL' containing the image paths or URLs.")

    # Classify each image
    results = []
    for idx, image_url in enumerate(tqdm(data['Image URL'], desc="Classifying images")):
        results.append(classify_image_from_url(image_url, idx))

    # Add results to the dataframe
    data['is_tour_date'] = results

    # Determine the output CSV file path
    if not output_csv:
        base_name, ext = os.path.splitext(os.path.basename(input_csv))
        output_csv = f"{base_name}_classified{ext}"

    # If an output folder is specified, ensure it exists and construct the full path
    if output_folder:
        os.makedirs(output_folder, exist_ok=True)
        output_csv = os.path.join(output_folder, os.path.basename(output_csv))

    # Save the classified data to the output CSV file
    data.to_csv(output_csv, index=False)
    logging.info(f"Classification completed. Results saved to {output_csv}")