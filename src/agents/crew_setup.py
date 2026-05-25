import json

from crewai import Agent, Crew, Process, Task
from langchain_core.language_models.chat_models import BaseChatModel

from src.jobs.search import search_jobs
from src.llm.factory import Provider, get_chat_llm
from src.matching.matcher import match_resume_to_jobs
from src.resume.analyzer import extract_skills
from src.resume.parser import load_resume_text
from src.tools.job_tool import JobSearchTool
from src.tools.resume_tool import ResumeAnalysisTool


def _get_llm(provider: Provider = "auto") -> BaseChatModel:
    try:
        return get_chat_llm(provider, temperature=0.2)
    except ValueError as exc:
        raise ValueError(
            f"{exc} Configure GROQ_API_KEY or start Ollama (ollama pull llama3.2)."
        ) from exc


def _prefetch_context(
    resume_path: str,
    job_query: str,
    location: str,
    provider: Provider = "auto",
    india_only: bool = True,
) -> dict:
    text = load_resume_text(resume_path)
    analysis = extract_skills(text, provider=provider)
    skills = analysis.get("skills", [])
    search_q = job_query or " ".join(analysis.get("job_titles", [])[:2]) or "software developer"
    jobs = search_jobs(
        query=search_q,
        location=location,
        limit=10,
        india_only=india_only,
    )
    matched = match_resume_to_jobs(skills, jobs)
    return {
        "resume_text": text,
        "analysis": analysis,
        "search_query": search_q,
        "jobs": matched,
    }


def run_job_search_crew(
    resume_path: str,
    job_query: str = "",
    location: str = "",
    provider: Provider = "auto",
    india_only: bool = True,
) -> str:
    """Orchestrate Resume Analyzer, Job Finder, and Recommendation agents via CrewAI."""
    llm = _get_llm(provider)
    ctx = _prefetch_context(
        resume_path, job_query, location, provider=provider, india_only=india_only
    )

    resume_tool = ResumeAnalysisTool()
    job_tool = JobSearchTool()

    resume_analyzer = Agent(
        role="Resume Analyzer",
        goal="Analyze resumes, extract skills, and identify strengths and gaps.",
        backstory=(
            "You are an expert career coach and technical recruiter. "
            "You read resumes carefully and produce structured, actionable insights."
        ),
        llm=llm,
        tools=[resume_tool],
        verbose=True,
        allow_delegation=False,
    )

    job_finder = Agent(
        role="Job Finder",
        goal="Find relevant job openings and explain how well they match the candidate.",
        backstory=(
            "You specialize in sourcing roles from job boards and mapping requirements "
            "to candidate profiles with clear match scores."
        ),
        llm=llm,
        tools=[job_tool],
        verbose=True,
        allow_delegation=False,
    )

    recommendation_agent = Agent(
        role="Recommendation Agent",
        goal=(
            "Suggest concrete resume improvements and generate tailored interview questions "
            "based on top job matches."
        ),
        backstory=(
            "You help candidates land interviews by improving bullet points, keywords, "
            "and interview preparation aligned to target roles."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    analysis_blob = json.dumps(ctx["analysis"], indent=2)
    jobs_blob = json.dumps(ctx["jobs"][:8], indent=2)

    analyze_task = Task(
        description=(
            f"Analyze the resume at path: {resume_path}\n\n"
            "Use the resume_analyzer tool with that path. "
            "Also use this pre-extracted context as reference:\n"
            f"{analysis_blob}\n\n"
            "Deliver: skills list, years of experience estimate, top 3 strengths, "
            "top 5 skill gaps, and a 3-sentence professional summary."
        ),
        expected_output=(
            "Structured resume analysis with skills, strengths, gaps, and summary."
        ),
        agent=resume_analyzer,
    )

    search_task = Task(
        description=(
            f"Find jobs for query: '{ctx['search_query']}' "
            f"location: '{location or 'any'}'.\n\n"
            f"Pass resume skills as JSON: {json.dumps(ctx['analysis'].get('skills', []))}\n\n"
            "Use the job_finder tool. Reference pre-fetched matches:\n"
            f"{jobs_blob}\n\n"
            "Deliver: top 5 jobs with match scores, matched skills, and missing skills per role."
        ),
        expected_output="Ranked job list with match scores and skill gap notes.",
        agent=job_finder,
        context=[analyze_task],
    )

    recommend_task = Task(
        description=(
            "Using the resume analysis and job matches from prior tasks:\n"
            "1. Suggest 8 specific resume improvements (rewrite weak bullets, add keywords, quantify impact).\n"
            "2. List 5 skills the candidate should emphasize or learn for the best-matching roles.\n"
            "3. Generate 12 interview questions: 4 behavioral, 4 technical, 4 role-specific.\n"
            "Format with clear headings and bullet points."
        ),
        expected_output=(
            "Resume improvement suggestions, skill priorities, and interview question bank."
        ),
        agent=recommendation_agent,
        context=[analyze_task, search_task],
    )

    crew = Crew(
        agents=[resume_analyzer, job_finder, recommendation_agent],
        tasks=[analyze_task, search_task, recommend_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return str(result)
