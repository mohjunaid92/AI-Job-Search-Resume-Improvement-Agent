import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from src.llm.factory import Provider, get_chat_llm

_SKILL_FALLBACK = re.compile(
    r"\b(python|java|javascript|typescript|react|node\.?js|sql|aws|azure|"
    r"docker|kubernetes|git|agile|scrum|machine learning|data analysis|"
    r"excel|power bi|tableau|rest api|fastapi|django|flask|spring|"
    r"langchain|crewai|llm|nlp|ci/cd|terraform|linux|html|css|mongodb|"
    r"postgresql|redis|graphql|microservices|leadership|communication)\b",
    re.IGNORECASE,
)


def _heuristic_skills(resume_text: str) -> list[str]:
    found = {m.group(0).lower() for m in _SKILL_FALLBACK.finditer(resume_text)}
    return sorted(found)


def extract_skills(
    resume_text: str,
    use_llm: bool = True,
    provider: Provider = "auto",
) -> dict:
    """
    Extract structured skills from resume text.
    Uses Groq or Ollama when available; falls back to keyword heuristics.
    """
    if use_llm:
        try:
            llm = get_chat_llm(provider, temperature=0.1)
            system = SystemMessage(
                content=(
                    "You extract structured information from resumes. "
                    "Respond with valid JSON only, no markdown."
                )
            )
            human = HumanMessage(
                content=(
                    "Analyze this resume and return JSON with keys:\n"
                    '- "skills": list of technical and soft skills (strings)\n'
                    '- "job_titles": likely target roles (strings)\n'
                    '- "years_experience": number or null\n'
                    '- "summary": one paragraph professional summary\n'
                    '- "strengths": list of strengths\n'
                    '- "gaps": list of likely skill gaps for modern roles\n\n'
                    f"RESUME:\n{resume_text[:12000]}"
                )
            )
            response = llm.invoke([system, human])
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            data = json.loads(raw)
            data["skills"] = list(dict.fromkeys(s.lower() for s in data.get("skills", [])))
            return data
        except (ValueError, json.JSONDecodeError):
            pass

    skills = _heuristic_skills(resume_text)
    return {
        "skills": skills,
        "job_titles": [],
        "years_experience": None,
        "summary": resume_text[:500],
        "strengths": skills[:5],
        "gaps": [],
    }
