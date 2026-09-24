from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import List

from github_enrichment import GitHubEnricher
from resume_parser import parse_resume
from scoring import build_result
from schemas import BatchSummary, ScreeningResult


def run_pipeline(input_dir: Path, output_path: Path, github_token: str | None = None) -> dict:
    input_dir = input_dir.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    resumes = sorted([path for path in input_dir.iterdir() if path.suffix.lower() in {".pdf", ".txt", ".md", ".docx"}])
    enricher = GitHubEnricher(token=github_token)
    results: List[ScreeningResult] = []
    failed_unreadable = 0

    for resume_path in resumes:
        try:
            parsed = parse_resume(resume_path)
            github = enricher.enrich(parsed.github_username)
            result = build_result(parsed, github)
        except Exception as exc:  # noqa: BLE001 - per-resume failure must not stop the batch
            failed_unreadable += 1
            result = ScreeningResult(
                rank=None,
                candidate_name=resume_path.stem,
                file_name=resume_path.name,
                eligible=False,
                total_score=0,
                score_breakdown=__import__("schemas").ScoreBreakdown(),
                matched_skills=[],
                project_summary="",
                github_summary="",
                strengths=[],
                concerns=["Unreadable or malformed resume"],
                rejection_reasons=[f"Unreadable or malformed resume: {exc}"],
                evidence={"python": [], "ai": []},
                parse_status="failed",
                error=str(exc),
            )
        results.append(result)

    eligible_results = sorted((result for result in results if result.eligible), key=lambda item: (-item.total_score, item.candidate_name.lower(), item.file_name.lower()))
    for rank, result in enumerate(eligible_results, start=1):
        result.rank = rank

    batch_summary = BatchSummary(
        total_resumes=len(resumes),
        successfully_parsed=len(results) - failed_unreadable,
        eligible=len(eligible_results),
        rejected=(len(results) - failed_unreadable) - len(eligible_results),
        failed_unreadable=failed_unreadable,
    )

    payload = {
        "batch_summary": asdict(batch_summary),
        "results": [asdict(result) for result in eligible_results] + [asdict(result) for result in results if not result.eligible],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload