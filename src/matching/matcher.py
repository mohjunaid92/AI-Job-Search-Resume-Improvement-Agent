import re
from typing import Any


def _normalize_tokens(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9+#.]+", text.lower())
    return {t for t in tokens if len(t) > 2}


def match_resume_to_jobs(
    resume_skills: list[str],
    jobs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Score each job by overlap between resume skills and job description."""
    skill_set = _normalize_tokens(" ".join(resume_skills))

    scored: list[dict[str, Any]] = []
    for job in jobs:
        blob = " ".join(
            [
                job.get("title", ""),
                job.get("description", ""),
                " ".join(job.get("tags", [])),
            ]
        )
        job_tokens = _normalize_tokens(blob)
        if not skill_set:
            overlap = set()
            score = 0.0
        else:
            overlap = skill_set & job_tokens
            score = round(len(overlap) / max(len(skill_set), 1) * 100, 1)

        missing = sorted(skill_set - job_tokens)[:15]
        matched = sorted(overlap)

        scored.append(
            {
                **job,
                "match_score": score,
                "matched_skills": matched,
                "missing_for_job": missing,
            }
        )

    scored.sort(key=lambda j: j["match_score"], reverse=True)
    return scored
