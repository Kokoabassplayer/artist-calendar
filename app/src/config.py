import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-flash-latest")

    @classmethod
    def validate(cls) -> None:
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in .env or environment.")
