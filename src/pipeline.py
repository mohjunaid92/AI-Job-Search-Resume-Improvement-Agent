"""End-to-end pipeline used by CLI, Streamlit, and PDF export."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import settings
from src.jobs.search import search_jobs
from src.llm.factory import Provider, get_chat_llm, llm_status
from src.matching.matcher import match_resume_to_jobs
from src.resume.analyzer import extract_skills
from src.resume.parser import load_resume_text


def run_quick_pipeline(
    resume_text: str,
    job_query: str = "",
    location: str = "",
    limit: int = 8,
    provider: Provider = "auto",
    include_recommendations: bool = True,
    india_only: bool = True,
) -> dict[str, Any]:
    """Analyze resume, search jobs, match, and optionally generate LLM recommendations."""
    use_llm = _can_use_llm(provider)
    analysis = extract_skills(resume_text, use_llm=use_llm, provider=provider)
    search_q = (
        job_query.strip()
        or " ".join(analysis.get("job_titles", [])[:2])
        or "software developer"
    )
    jobs = search_jobs(
        query=search_q,
        location=location,
        limit=limit,
        india_only=india_only,
    )
    matched = match_resume_to_jobs(analysis.get("skills", []), jobs)

    result: dict[str, Any] = {
        "llm_status": llm_status(provider),
        "analysis": analysis,
        "search_query": search_q,
        "location": location,
        "india_only": india_only,
        "jobs": matched,
    }

    if include_recommendations and use_llm:
        result["recommendations"] = _generate_recommendations(
            resume_text, analysis, matched[:5], provider=provider
        )
    else:
        result["recommendations"] = None

    return result


def run_quick_pipeline_from_path(
    resume_path: str,
    job_query: str = "",
    location: str = "",
    limit: int = 8,
    provider: Provider = "auto",
    include_recommendations: bool = True,
    india_only: bool = True,
) -> dict[str, Any]:
    text = load_resume_text(resume_path)
    data = run_quick_pipeline(
        text,
        job_query=job_query,
        location=location,
        limit=limit,
        provider=provider,
        include_recommendations=include_recommendations,
        india_only=india_only,
    )
    data["resume_path"] = resume_path
    return data


def _can_use_llm(provider: Provider) -> bool:
    try:
        get_chat_llm(provider)
        return True
    except ValueError:
        return False


def _generate_recommendations(
    resume_text: str,
    analysis: dict,
    top_jobs: list[dict],
    provider: Provider = "auto",
) -> str:
    llm = get_chat_llm(provider, temperature=0.3)
    jobs_blob = json.dumps(
        [
            {
                "title": j.get("title"),
                "company": j.get("company"),
                "match_score": j.get("match_score"),
                "matched_skills": j.get("matched_skills"),
                "missing_for_job": j.get("missing_for_job"),
            }
            for j in top_jobs
        ],
        indent=2,
    )
    system = SystemMessage(
        content="You are an expert career coach. Use clear markdown headings and bullet lists."
    )
    human = HumanMessage(
        content=(
            "Based on this resume analysis and top job matches, provide:\n"
            "## Resume Improvements\n8 specific, actionable bullet rewrites or additions.\n"
            "## Skills to Emphasize\n5 skills to highlight or learn.\n"
            "## Interview Questions\n"
            "4 behavioral, 4 technical, 4 role-specific questions.\n\n"
            f"ANALYSIS:\n{json.dumps(analysis, indent=2)}\n\n"
            f"TOP JOBS:\n{jobs_blob}\n\n"
            f"RESUME EXCERPT:\n{resume_text[:6000]}"
        )
    )
    response = llm.invoke([system, human])
    return response.content.strip()


def format_report_markdown(data: dict[str, Any], crew_report: str | None = None) -> str:
    """Build a single markdown document for display or PDF export."""
    lines: list[str] = ["# Job Search & Resume Report\n"]

    status = data.get("llm_status", {})
    lines.append(f"*LLM: {status.get('active', 'heuristic')}*\n")

    analysis = data.get("analysis", {})
    lines.append("## Resume Analysis\n")
    if analysis.get("summary"):
        lines.append(f"{analysis['summary']}\n")
    if analysis.get("skills"):
        lines.append("**Skills:** " + ", ".join(analysis["skills"]) + "\n")
    if analysis.get("strengths"):
        lines.append("**Strengths:**\n")
        for s in analysis["strengths"]:
            lines.append(f"- {s}\n")
    if analysis.get("gaps"):
        lines.append("**Gaps:**\n")
        for g in analysis["gaps"]:
            lines.append(f"- {g}\n")

    loc_label = data.get("location") or "India"
    if data.get("india_only", True):
        lines.append(f"\n## Job Matches — India ({loc_label}) · query: {data.get('search_query', '')}\n")
    else:
        lines.append(f"\n## Job Matches (query: {data.get('search_query', '')})\n")
    for job in data.get("jobs", [])[:8]:
        score = job.get("match_score", 0)
        lines.append(f"### {job.get('title', 'Role')} — {score}% match\n")
        lines.append(f"- **Company:** {job.get('company', 'N/A')}\n")
        lines.append(f"- **Location:** {job.get('location', 'N/A')}\n")
        if job.get("url"):
            lines.append(f"- **Link:** {job['url']}\n")
        matched = job.get("matched_skills", [])
        if matched:
            lines.append(f"- **Matched skills:** {', '.join(matched[:10])}\n")

    rec = data.get("recommendations") or crew_report
    if rec:
        lines.append("\n## Recommendations & Interview Prep\n\n")
        lines.append(rec if isinstance(rec, str) else str(rec))
        lines.append("\n")

    if crew_report and not data.get("recommendations"):
        lines.append("\n## Full Agent Report\n\n")
        lines.append(crew_report)

    return "".join(lines)
