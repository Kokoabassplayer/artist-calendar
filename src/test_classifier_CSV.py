from tour_date_csv_utils import classify_images
import os

BASE_DATA_DIR = os.environ.get("BASE_DATA_DIR", os.path.join(os.getcwd(), "data"))

# Use the function with specified CSV files
input_csv = os.path.join(BASE_DATA_DIR, "CSV", "raw", "retrospect_official_2024-11-01_to_2024-12-01.csv")
output_folder = os.path.join(BASE_DATA_DIR, "CSV", "classified")
classify_images(
    input_csv = input_csv,
    output_folder = output_folder #, output_csv
)
