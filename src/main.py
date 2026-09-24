from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import warnings
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

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    warnings.filterwarnings("ignore", message="Ignoring wrong pointing object*")
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    logging.getLogger("pypdf._reader").setLevel(logging.ERROR)

    input_dir = Path(args.input if args.input else os.getenv("RESUMES_DIR", "resumes"))
    output_path = Path(args.output)
    payload = run_pipeline(input_dir, output_path, github_token=os.getenv("GITHUB_TOKEN"))

    print(json.dumps(payload["batch_summary"], indent=2, ensure_ascii=False))
    print("\nRejected candidates:\n")

    rejected_records = [record for record in payload["results"] if not record.get("eligible")]
    if not rejected_records:
        print("No rejected candidates were recorded.")
    else:
        for record in rejected_records:
            display_record = {
                "candidate": record.get("candidate") or record.get("candidate_name"),
                "eligible": record.get("eligible"),
                "rejection_reasons": record.get("rejection_reasons", []),
                "matched_skills": record.get("matched_skills", []),
                "file_name": record.get("file_name"),
            }
            print(json.dumps(display_record, indent=2, ensure_ascii=False))
            print()

    print("Eligible candidate details are available in the PDF and output/results.json.")
    print(f"Wrote results to {output_path.resolve()}")


if __name__ == "__main__":
    main()
