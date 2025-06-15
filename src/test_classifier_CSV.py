from tour_date_csv_utils import classify_images

# Use the function with specified CSV files
input_csv = "/Users/kokoabassplayer/Desktop/python/ArtistCalendar/CSV/raw/retrospect_official_2024-11-01_to_2024-12-01.csv"
output_folder = "/Users/kokoabassplayer/Desktop/python/ArtistCalendar/CSV/classified"
classify_images(
    input_csv = input_csv,
    output_folder = output_folder #, output_csv
)