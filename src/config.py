import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Base directory is 2 levels up from this file (src/config.py -> project_root)
    BASE_DIR = Path(__file__).resolve().parent.parent

    # Instagram Credentials
    INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME") or os.environ.get("IG_USERNAME")
    INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD") or os.environ.get("IG_PASSWORD")

    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    JINA_API_KEY = os.getenv("JINA_API_KEY")

    # Output Directories
    RAW_CSV_DIR = BASE_DIR / "CSV" / "raw"
    CLASSIFIED_CSV_DIR = BASE_DIR / "CSV" / "classified"
    MARKDOWN_DIR = BASE_DIR / "TourDateMarkdown"
    IMAGE_OUTPUT_DIR = BASE_DIR / "TourDateImage"
    
    # Logging
    LOG_FILE = BASE_DIR / "pipeline.log"

    @classmethod
    def validate(cls):
        """Check for critical configuration errors."""
        if not cls.INSTAGRAM_USERNAME or not cls.INSTAGRAM_PASSWORD:
            raise ValueError("Instagram credentials not set in .env file.")
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in .env file.")

    @classmethod
    def setup_logging(cls):
        """Configure logging to file and console."""
        import logging
        
        # Create handlers
        file_handler = logging.FileHandler(cls.LOG_FILE, encoding='utf-8')
        stream_handler = logging.StreamHandler()
        
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)
        
        # Configure root logger
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # Avoid duplicate handlers
        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(stream_handler)
        else:
            # If handlers exist (e.g. from instaloader), simpler to just add ours if not present?
            # Or force reset? Let's force reset for our app's clarity.
            logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler])
