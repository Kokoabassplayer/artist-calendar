from tour_date_classifier import tour_date_classifier
import os

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