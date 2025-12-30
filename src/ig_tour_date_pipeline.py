import os
import logging
from typing import List, Optional
import instaloader
from dotenv import load_dotenv

from config import Config
from ig_scraper import GetInstagramProfile
from tour_date_csv_utils import classify_images
from image_to_markdown import csv_to_markdown_with_extracted_data


class TourDatePipeline:
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """Initialize the pipeline with Instagram credentials."""
        Config.setup_logging()
        Config.validate()
        
        self.username = username or Config.INSTAGRAM_USERNAME
        self.password = password or Config.INSTAGRAM_PASSWORD
        self.loader = instaloader.Instaloader()
        
        self._login()

    def _login(self):
        """Authenticate with Instagram."""
        try:
            self.loader.login(self.username, self.password)
            logging.info(f"Logged in as {self.username}")
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            logging.warning("Two-factor authentication required.")
            two_factor_code = input("Enter the 2FA code: ")
            try:
                self.loader.two_factor_login(two_factor_code)
                logging.info(f"Logged in as {self.username} with 2FA.")
            except instaloader.exceptions.BadCredentialsException:
                logging.error("Invalid 2FA code. Exiting.")
                exit(1)
        except instaloader.exceptions.BadCredentialsException:
            logging.error("Invalid username or password. Exiting.")
            exit(1)
        except Exception as e:
            logging.error(f"An unexpected error occurred during login: {e}")
            exit(1)

    def run(self, artist_profiles: List[str], since: str, until: str):
        """Run the full extraction pipeline for a list of artists."""
        
        # Ensure base directories exist
        for directory in [Config.RAW_CSV_DIR, Config.CLASSIFIED_CSV_DIR, Config.MARKDOWN_DIR]:
            os.makedirs(directory, exist_ok=True)

        scraper = GetInstagramProfile(self.loader)

        for artist in artist_profiles:
            try:
                logging.info(f"Processing artist: {artist}")
                self._process_artist(scraper, artist, since, until)
            except Exception as e:
                logging.error(f"Failed to process {artist}: {e}")
                continue

        logging.info("Pipeline completed for all profiles.")

    def _process_artist(self, scraper: GetInstagramProfile, artist: str, since: str, until: str):
        """Process a single artist: Scrape -> Classify -> Extract."""
        
        # Step 1: Scrape
        logging.info(f"Step 1: Scraping Instagram posts for {artist}...")
        raw_output_folder = Config.RAW_CSV_DIR / artist
        os.makedirs(raw_output_folder, exist_ok=True)
        
        raw_csv_file = raw_output_folder / f"{artist}_{since}_to_{until}.csv"
        
        scraper.get_post_info_csv(
            username=artist,
            since=since,
            until=until,
            output_folder=str(raw_output_folder),
        )
        logging.info(f"Raw data saved to: {raw_csv_file}")

        # Step 2: Classify
        logging.info(f"Step 2: Classifying images for {artist}...")
        classified_output_folder = Config.CLASSIFIED_CSV_DIR / artist
        os.makedirs(classified_output_folder, exist_ok=True)
        
        classified_csv_file = classified_output_folder / f"{artist}_{since}_to_{until}_classified.csv"
        
        classify_images(
            input_csv=str(raw_csv_file),
            output_csv=str(classified_csv_file),
            output_folder=str(classified_output_folder),
        )
        logging.info(f"Classified data saved to: {classified_csv_file}")

        # Step 3: Extract Markdown
        logging.info(f"Step 3: Extracting tour dates to Markdown for {artist}...")
        markdown_output_file = Config.MARKDOWN_DIR / f"{artist}_{since}_to_{until}.md"
        
        csv_to_markdown_with_extracted_data(str(classified_csv_file))
        logging.info(f"Markdown file saved to: {markdown_output_file}")


if __name__ == "__main__":
    # Example usage
    pipeline = TourDatePipeline()
    
    # Configuration
    artist_profiles = ["zealrockband"]
    since_date = "2024-11-20"
    until_date = "2024-12-31"

    pipeline.run(artist_profiles, since=since_date, until=until_date)
