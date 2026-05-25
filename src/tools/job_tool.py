import json
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from src.jobs.search import search_jobs
from src.matching.matcher import match_resume_to_jobs


class JobSearchInput(BaseModel):
    query: str = Field(..., description="Job search keywords, e.g. 'Python developer'")
    location: str = Field(default="", description="City or region (used by Adzuna)")
    limit: int = Field(default=8, description="Max number of jobs to return")
    resume_skills_json: str = Field(
        default="[]",
        description='JSON array of resume skills for matching, e.g. ["python","sql"]',
    )


class JobSearchTool(BaseTool):
    name: str = "job_finder"
    description: str = (
        "Searches free job APIs (Remotive, Adzuna) and scores listings against resume skills. "
        "Provide query, optional location, limit, and resume_skills_json."
    )
    args_schema: Type[BaseModel] = JobSearchInput

    def _run(
        self,
        query: str,
        location: str = "",
        limit: int = 8,
        resume_skills_json: str = "[]",
    ) -> str:
        try:
            skills = json.loads(resume_skills_json)
            if not isinstance(skills, list):
                skills = []
        except json.JSONDecodeError:
            skills = []

        jobs = search_jobs(query=query, location=location, limit=limit, india_only=True)
        matched = match_resume_to_jobs(skills, jobs)
        return json.dumps(matched, indent=2)
