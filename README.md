# KasparroSDEAssessment

AI resume screening and ranking pipeline for the SDE intern assignment.

## Structure

- `resumes/` stores the candidate PDF resumes.
- `src/main.py` is the CLI entry point.
- `src/pipeline.py` orchestrates parsing, scoring, and output generation.
- `src/resume_parser.py` extracts text and candidate signals from PDFs, TXT, and DOCX files.
- `src/scoring.py` applies the hard filter and scoring rules.
- `src/github_enrichment.py` enriches public GitHub profiles and scores activity.
- `src/schemas.py` defines the shared data models.

## Setup

1. Create a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Copy `.env.example` to `.env` and set `GITHUB_TOKEN` if you want authenticated GitHub requests.

## Run

```bash
python main.py
```

If you prefer to call the module directly, this also works:

```bash
python src/main.py --input resumes --output output/results.json
```

## Design Decisions

The pipeline uses deterministic parsing and rule-based eligibility checks so the hard filter stays explainable and testable. Python evidence is accepted from genuine resume context such as skills, projects, or experience, while AI eligibility requires a meaningful project or implementation signal, not just a keyword in a skills list. Scoring is weighted toward AI project depth and Python/backend evidence, with smaller bonuses for deployment, engineering depth, and public GitHub activity. GitHub enrichment is best-effort and never blocks screening.

## If I Had More Time

1. Add stronger DOCX parsing and resume section normalization.
2. Improve AI/project quality detection with a small LLM-backed structured extractor.
3. Add a richer test corpus with more synthetic resumes and edge cases.
4. Produce a CSV companion report alongside the JSON output.
