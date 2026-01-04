#!/usr/bin/env python3
import argparse
import os
import sys

try:
    from google import genai
    from google.genai import errors, types
except ImportError as exc:
    print(
        "Missing google-genai. Run this script with the project venv:\n"
        "  ./venv_artist/bin/python app/scripts/test_llm_api.py\n"
        "Or install dependencies:\n"
        "  pip install -r requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Simple Gemini API test (text-only)."
    )
    parser.add_argument(
        "--text",
        default="Say hello in one short sentence.",
        help="Prompt text to send.",
    )
    parser.add_argument(
        "--model",
        default="models/gemini-flash-latest",
        help="Gemini model name.",
    )
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set.", file=sys.stderr)
        return 1

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(temperature=0)

    try:
        response = client.models.generate_content(
            model=args.model,
            contents=args.text,
            config=config,
        )
    except errors.ClientError as exc:
        print(f"Gemini API error: {exc}", file=sys.stderr)
        return 2

    output = response.text or ""
    print(output.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
