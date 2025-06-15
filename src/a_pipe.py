# Import necessary modules
from a_ig_scraper_backup import GetInstagramProfile
from tour_date_csv_utils import classify_images
from image_to_markdown import csv_to_markdown_with_extracted_data
import os
import instaloader

BASE_DATA_DIR = os.environ.get("BASE_DATA_DIR", os.path.join(os.getcwd(), "data"))

if __name__ == "__main__":
    # Initialize Instaloader
    loader = instaloader.Instaloader()
    username = "kenalabama"  # Replace with your Instagram username
    password = "test1test1"  # Replace with your Instagram password

    try:
        # Attempt to login
        loader.login(username, password)
        print(f"Logged in as {username}")
    except instaloader.exceptions.TwoFactorAuthRequiredException:
        # Handle 2FA
        print("Two-factor authentication required.")
        two_factor_code = input("Enter the 2FA code: ")
        try:
            loader.two_factor_login(two_factor_code)
            print(f"Logged in as {username} with 2FA.")
        except instaloader.exceptions.BadCredentialsException:
            print("Invalid 2FA code. Exiting.")
            exit(1)
    except instaloader.exceptions.BadCredentialsException:
        print("Invalid username or password. Exiting.")
        exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        exit(1)

    # List of artist profiles to process
    #artist_profiles = ["retrospect_official", "bowkylion", "sweetmullet", "palmy.ig"]
    #artist_profiles = ["artistland"]
    #artist_profiles = ["zealrockband"]
    #artist_profiles = ["loveis_ent"]
    artist_profiles = ["retrospect_official"]

    # Date range for scraping
    since = "2024-09-01"
    until = "2024-12-31"

    # Base folders for outputs
    base_raw_folder = os.path.join(BASE_DATA_DIR, "CSV", "raw")
    base_classified_folder = os.path.join(BASE_DATA_DIR, "CSV", "classified")
    base_markdown_folder = os.path.join(BASE_DATA_DIR, "TourDateMarkdown")

    # Ensure all base folders exist
    os.makedirs(base_raw_folder, exist_ok=True)
    os.makedirs(base_classified_folder, exist_ok=True)
    os.makedirs(base_markdown_folder, exist_ok=True)

    cls = GetInstagramProfile(loader)  # Pass the authenticated loader to the scraper class

    for artist_username in artist_profiles:
        try:
            print(f"Processing artist: {artist_username}")

            # Step 1: Scrape Instagram posts
            print(f"Step 1: Scraping Instagram posts for {artist_username}...")
            raw_output_folder = os.path.join(base_raw_folder, artist_username)
            os.makedirs(raw_output_folder, exist_ok=True)

            # Output CSV for raw data
            raw_csv_file = os.path.join(raw_output_folder, f"{artist_username}_{since}_to_{until}.csv")
            cls.get_post_info_csv(
                username=artist_username,
                since=since,
                until=until,
                output_folder=raw_output_folder,
            )
            print(f"Raw data saved to: {raw_csv_file}")

            # Step 2: Classify images as tour dates
            print(f"Step 2: Classifying images for {artist_username}...")
            classified_output_folder = os.path.join(base_classified_folder, artist_username)
            os.makedirs(classified_output_folder, exist_ok=True)

            # Output CSV for classified data
            classified_csv_file = os.path.join(classified_output_folder, f"{artist_username}_{since}_to_{until}_classified.csv")
            classify_images(
                input_csv=raw_csv_file,
                output_csv=classified_csv_file,
                output_folder=classified_output_folder,
            )
            print(f"Classified data saved to: {classified_csv_file}")

            # Step 3: Extract tour dates and generate Markdown
            print(f"Step 3: Extracting tour dates to Markdown for {artist_username}...")
            markdown_output_file = os.path.join(base_markdown_folder, f"{artist_username}_{since}_to_{until}.md")
            csv_to_markdown_with_extracted_data(classified_csv_file)
            print(f"Markdown file saved to: {markdown_output_file}")

        except Exception as e:
            print(f"Failed to process {artist_username}: {e}")
            continue  # Skip to the next artist

    print("Pipeline completed for all profiles.")
