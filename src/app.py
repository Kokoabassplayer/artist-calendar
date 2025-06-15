import argparse
import os
from dotenv import load_dotenv
import instaloader

from ig_scraper import GetInstagramProfile
from tour_date_csv_utils import classify_images
from image_to_markdown import csv_to_markdown_with_extracted_data


def run_pipeline(artists, since, until, output_base):
    loader = instaloader.Instaloader()
    username = os.environ.get("IG_USERNAME")
    password = os.environ.get("IG_PASSWORD")
    if not username or not password:
        raise SystemExit("IG_USERNAME or IG_PASSWORD not set")

    loader.login(username, password)

    base_raw = os.path.join(output_base, "raw")
    base_classified = os.path.join(output_base, "classified")
    base_markdown = os.path.join(output_base, "markdown")

    os.makedirs(base_raw, exist_ok=True)
    os.makedirs(base_classified, exist_ok=True)
    os.makedirs(base_markdown, exist_ok=True)

    scraper = GetInstagramProfile(loader)

    for artist in artists:
        raw_folder = os.path.join(base_raw, artist)
        os.makedirs(raw_folder, exist_ok=True)
        raw_csv = os.path.join(raw_folder, f"{artist}_{since}_to_{until}.csv")
        scraper.get_post_info_csv(
            username=artist,
            since=since,
            until=until,
            output_folder=raw_folder,
        )

        classified_folder = os.path.join(base_classified, artist)
        os.makedirs(classified_folder, exist_ok=True)
        classified_csv = os.path.join(
            classified_folder,
            f"{artist}_{since}_to_{until}_classified.csv",
        )
        classify_images(
            input_csv=raw_csv,
            output_csv=classified_csv,
            output_folder=classified_folder,
        )

        markdown_file = os.path.join(
            base_markdown, f"{artist}_{since}_to_{until}.md"
        )
        image_folder = os.path.join(base_markdown, "images", artist)
        csv_to_markdown_with_extracted_data(
            classified_csv,
            output_markdown_file=markdown_file,
            image_folder=image_folder,
        )

    print("Pipeline completed.")


def main():
    parser = argparse.ArgumentParser(description="Run the Artist Calendar pipeline")
    parser.add_argument("--artists", required=True, help="Comma separated Instagram usernames")
    parser.add_argument("--since", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--until", required=True, help="End date YYYY-MM-DD")
    parser.add_argument(
        "--output",
        default="output",
        help="Base directory for generated files",
    )
    parser.add_argument(
        "--env-file",
        help="Optional path to .env file containing IG_USERNAME and IG_PASSWORD",
    )
    args = parser.parse_args()

    if args.env_file:
        load_dotenv(args.env_file)
    else:
        load_dotenv()

    artists = [a.strip() for a in args.artists.split(",") if a.strip()]
    run_pipeline(artists, args.since, args.until, args.output)


if __name__ == "__main__":
    main()
