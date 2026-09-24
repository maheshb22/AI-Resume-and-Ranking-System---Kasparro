from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
RESULTS_JSON = ROOT / "output" / "results.json"
RESULTS_PDF = ROOT / "output" / "results_summary.pdf"


def clean_text(value: object) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", " ")
        .strip()
    )


def make_bullets(items: list[str], styles, *, left_indent: int = 14) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(clean_text(item), styles["SmallBody"])) for item in items],
        bulletType="bullet",
        leftIndent=left_indent,
    )


def build_pdf() -> None:
    data = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    summary = data["batch_summary"]
    results = data["results"]

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            spaceAfter=10,
            textColor=colors.HexColor("#1f2937"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#111827"),
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            alignment=TA_LEFT,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=10.5,
            alignment=TA_LEFT,
            spaceAfter=2,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CodeBlock",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=7.8,
            leading=9.2,
            spaceBefore=4,
            spaceAfter=6,
        )
    )

    doc = SimpleDocTemplate(
        str(RESULTS_PDF),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="AI Resume Screening Report",
        author="GitHub Copilot",
    )

    story = []
    story.append(Paragraph("AI Resume Screening Report", styles["ReportTitle"]))
    story.append(Paragraph("Generated from the current resume screening run.", styles["ReportBody"]))
    story.append(Spacer(1, 6))

    summary_table_data = [
        ["Metric", "Count"],
        ["Total resumes", summary["total_resumes"]],
        ["Successfully parsed", summary["successfully_parsed"]],
        ["Eligible", summary["eligible"]],
        ["Rejected", summary["rejected"]],
        ["Failed / unreadable", summary["failed_unreadable"]],
    ]
    summary_table = Table(summary_table_data, colWidths=[78 * mm, 42 * mm], repeatRows=1)
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Candidate Records", styles["ReportHeading"]))
    story.append(Paragraph("The blocks below are written in a readable format with the same key information as the JSON output.", styles["ReportBody"]))

    for item in results:
        candidate_label = clean_text(item.get('candidate') or item.get('candidate_name'))
        eligible = bool(item.get("eligible"))
        if item.get("eligible"):
            story.append(Paragraph(f"Rank {item.get('rank', '-')}: {candidate_label}", styles["ReportHeading"]))
        else:
            story.append(Paragraph(candidate_label, styles["ReportHeading"]))
        story.append(Paragraph(f"Eligibility: {'Eligible' if eligible else 'Rejected'}", styles["ReportBody"]))

        matched_skills = ", ".join(item.get("matched_skills", [])[:12])
        if matched_skills:
            story.append(Paragraph(f"Matched skills: {clean_text(matched_skills)}", styles["SmallBody"]))

        if eligible:
            score_breakdown = item.get("score_breakdown", {})
            story.append(
                Paragraph(
                    f"Total score: <b>{item.get('total_score', 0)}</b>  |  AI depth: {score_breakdown.get('ai_project_depth', 0)}  |  Python backend: {score_breakdown.get('python_backend', 0)}  |  Cloud/full-stack: {score_breakdown.get('cloud_fullstack', 0)}  |  GitHub: {score_breakdown.get('github', 0)}  |  Engineering depth: {score_breakdown.get('engineering_depth', 0)}",
                    styles["SmallBody"],
                )
            )
            project_summary = item.get("project_summary")
            if project_summary:
                story.append(Paragraph(f"Project summary: {clean_text(project_summary)}", styles["SmallBody"]))
            github_summary = item.get("github_summary")
            if github_summary:
                story.append(Paragraph(f"GitHub summary: {clean_text(github_summary)}", styles["SmallBody"]))
            strengths = item.get("strengths", [])
            if strengths:
                story.append(Paragraph("Strengths:", styles["SmallBody"]))
                story.append(make_bullets(strengths, styles))
            concerns = item.get("concerns", [])
            if concerns:
                story.append(Paragraph("Concerns:", styles["SmallBody"]))
                story.append(make_bullets(concerns, styles))
        else:
            reasons = item.get("rejection_reasons", [])
            file_name = item.get("file_name")
            if file_name:
                story.append(Paragraph(f"File: {clean_text(file_name)}", styles["SmallBody"]))
            if reasons:
                story.append(Paragraph("Rejection reasons:", styles["SmallBody"]))
                story.append(make_bullets(reasons, styles))
        story.append(Spacer(1, 6))

    story.append(Paragraph("Rejected Candidates", styles["ReportHeading"]))
    rejected = [item for item in results if not item["eligible"]]
    if rejected:
        for item in rejected[:10]:
            reasons = "; ".join(item.get("rejection_reasons", []) or ["No reasons provided"])
            story.append(
                Paragraph(
                    f"<b>{clean_text(item.get('candidate') or item['candidate_name'])}</b> ({clean_text(item['file_name'])}): {clean_text(reasons)}",
                    styles["SmallBody"],
                )
            )
    else:
        story.append(Paragraph("No rejected candidates were recorded.", styles["SmallBody"]))

    story.append(PageBreak())
    story.append(Paragraph("Scoring Notes", styles["ReportHeading"]))
    story.append(
        Paragraph(
            "GitHub enrichment is best-effort and may be rate-limited. The machine-readable source of truth remains the JSON output.",
            styles["ReportBody"],
        )
    )

    doc.build(story)


if __name__ == "__main__":
    build_pdf()