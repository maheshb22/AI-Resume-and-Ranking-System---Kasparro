from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Screen resume PDFs for Python + AI internship fit.")
    parser.add_argument("--input", default="resumes", help="Folder containing resume files.")
    parser.add_argument("--output", default="output/results.json", help="Path to write the JSON results.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    load_dotenv()

    input_dir = Path(args.input if args.input else os.getenv("RESUMES_DIR", "resumes"))
    output_path = Path(args.output)
    payload = run_pipeline(input_dir, output_path, github_token=os.getenv("GITHUB_TOKEN"))
    print(json.dumps(payload["batch_summary"], indent=2))
    print(f"Wrote results to {output_path.resolve()}")


if __name__ == "__main__":
    main()
