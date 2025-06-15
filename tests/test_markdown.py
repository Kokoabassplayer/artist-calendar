
from image_to_markdown import image_to_markdown
from pathlib import Path
# Example image path
#image_path = base_dir / "image" / "sweetmullet202412.png"
#image_path = base_dir / "image" / "palmy202412.png"
base_dir = Path(os.getenv("AC_DATA_ROOT", Path(__file__).resolve().parents[1]))
image_path = base_dir / "image" / "retrospect.jpg"
#image_path = base_dir / "image" / "parkinson.jpg"


# Convert the image to Markdown
markdown_output = image_to_markdown(image_path)
if markdown_output:
    print("Markdown Conversion:\n", markdown_output)