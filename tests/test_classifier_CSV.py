from tour_date_csv_utils import classify_images

# Use the function with specified CSV files
from pathlib import Path
base_dir = Path(os.getenv("AC_DATA_ROOT", Path(__file__).resolve().parents[1]))
input_csv = base_dir / "CSV" / "raw" / "retrospect_official_2024-11-01_to_2024-12-01.csv"
output_folder = base_dir / "CSV" / "classified"
classify_images(
    input_csv = input_csv,
    output_folder = output_folder #, output_csv
)