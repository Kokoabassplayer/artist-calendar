from image_to_markdown import image_to_markdown

# Example image path
# image_path = "/Users/kokoabassplayer/Desktop/python/ArtistCalendar/image/sweetmullet202412.png"
# image_path = "/Users/kokoabassplayer/Desktop/python/ArtistCalendar/image/palmy202412.png"
image_path = "/Users/kokoabassplayer/Desktop/python/ArtistCalendar/image/retrospect.jpg"
# image_path = "/Users/kokoabassplayer/Desktop/python/ArtistCalendar/image/parkinson.jpg"


# Convert the image to Markdown
markdown_output = image_to_markdown(image_path)
if markdown_output:
    print("Markdown Conversion:\n", markdown_output)
