from tour_date_classifier import tour_date_classifier
import os

# Example image path
image_path = (
    "/Users/kokoabassplayer/Desktop/python/ArtistCalendar/image/palmy202412.png"
)
# image_path = "https://www.facebook.com/photo.php?fbid=1121851509302448&set=pb.100044328284924.-2207520000&type=3"

# Extract the file name from the image path
filename = os.path.basename(image_path)

# Classify the image
output = tour_date_classifier(image_path)

if output:
    print(f"file name {filename}: ", output)
