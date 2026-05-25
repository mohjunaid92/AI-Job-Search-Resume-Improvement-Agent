import json
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from src.resume.analyzer import extract_skills
from src.resume.parser import load_resume_text


class ResumeToolInput(BaseModel):
    resume_path: str = Field(..., description="Absolute or relative path to resume file (pdf, docx, txt)")


class ResumeAnalysisTool(BaseTool):
    name: str = "resume_analyzer"
    description: str = (
        "Loads a resume file, extracts skills, strengths, gaps, and a professional summary. "
        "Input must be the resume file path as a string."
    )
    args_schema: Type[BaseModel] = ResumeToolInput

    def _run(self, resume_path: str) -> str:
        text = load_resume_text(resume_path)
        analysis = extract_skills(text)
        return json.dumps({"resume_excerpt": text[:1500], "analysis": analysis}, indent=2)
