import os
from pathlib import Path
import glob

def append_to_single_markdown():
    # Specify the directory containing the input markdown files

    base_dir = Path(os.getenv("AC_DATA_ROOT", Path(__file__).resolve().parents[1]))
    input_directory = base_dir / "TourDateMarkdown"
    
    # Specify the output directory
    output_directory = base_dir / "CombinedMarkdown"

    # Specify the output file name
    output_file = "combined_tour_dates.md"

    # Get all markdown files in the input directory
    markdown_files = glob.glob(str(input_directory / '*.md'))

    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)

    # Full path for the output file
    output_path = output_directory / output_file

    with open(output_path, 'w', encoding='utf-8') as outfile:
        for md_file in markdown_files:
            with open(md_file, 'r', encoding='utf-8') as infile:
                outfile.write(infile.read())
                outfile.write('\n\n')  # Add some spacing between content from different files

    print(f"All markdown files have been appended to {output_path}")

# You can now call the function without any arguments
append_to_single_markdown()
