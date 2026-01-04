#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from local_db import ingest_structured


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest structured tour JSON into a local SQLite database."
    )
    parser.add_argument("input", help="Path to structured JSON file.")
    parser.add_argument(
        "--db",
        default=str(PROJECT_ROOT / "output" / "local.db"),
        help="Path to local SQLite database file.",
    )
    parser.add_argument(
        "--image-url",
        help="Poster image URL or local path.",
    )
    parser.add_argument(
        "--source-type",
        default="manual",
        choices=["manual", "instagram", "facebook", "website"],
        help="Source type for the poster.",
    )
    parser.add_argument(
        "--source-url",
        help="Original source URL (Instagram post, etc.).",
    )
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    summary = ingest_structured(
        data,
        db_path=Path(args.db),
        image_url=args.image_url,
        source_type=args.source_type,
        source_url=args.source_url,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
