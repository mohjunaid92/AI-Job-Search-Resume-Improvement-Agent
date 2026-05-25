"""
AI Job Search + Resume Improvement Agent

Commands:
  python job_resume_agent.py search [--query KEYWORDS] [--limit N] [--json]
  python job_resume_agent.py improve --resume PATH [--job PATH] [--out PATH]

Requires OPENAI_API_KEY in .env for the improve command.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

USER_AGENT = "Mozilla/5.0 (compatible; JobResumeAgent/1.0; +https://example.local)"


def _read_text_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Not a file: {path}")
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _read_resume_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return _read_text_file(path)
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise SystemExit(
                "PDF resumes need pypdf. Run: pip install pypdf"
            ) from e
        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages:
            t = page.extract_text() or ""
            parts.append(t)
        return "\n".join(parts).strip()
    raise ValueError(f"Unsupported resume format: {suffix}. Use .txt, .md, or .pdf")


def fetch_remoteok(query: str, limit: int, timeout: int) -> list[dict[str, Any]]:
    """RemoteOK public API: JSON array; skip non-job entries (jobs have position + company)."""
    url = "https://remoteok.com/api"
    r = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        return []
    q = query.lower()
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        position = str(item.get("position") or item.get("title") or "").strip()
        company = str(item.get("company") or "").strip()
        if not position or not company:
            continue
        desc = str(item.get("description") or "")
        blob = f"{position} {company} {desc}".lower()
        if q and q not in blob:
            continue
        slug = str(item.get("slug") or "").strip()
        href = str(item.get("url") or "").strip()
        if not href and slug:
            href = f"https://remoteok.com/remote-jobs/{slug}"
        if not href:
            href = "https://remoteok.com/remote-jobs"
        rows.append(
            {
                "title": position,
                "company": company,
                "location": str(item.get("location") or "Remote"),
                "url": href,
                "source": "RemoteOK",
                "tags": item.get("tags") or [],
            }
        )
        if len(rows) >= limit:
            break
    return rows


def fetch_weworkremotely(query: str, limit: int, timeout: int) -> list[dict[str, Any]]:
    term = requests.utils.quote(query)
    url = f"https://weworkremotely.com/remote-jobs/search?term={term}"
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out: list[dict[str, Any]] = []
    for article in soup.select("article li")[: limit * 2]:
        link = article.select_one("a")
        title_el = article.select_one(".title")
        company_el = article.select_one(".company")
        region_el = article.select_one(".region.company")
        if not link or not title_el or not company_el:
            continue
        href = (link.get("href") or "").strip()
        full = f"https://weworkremotely.com{href}" if href.startswith("/") else href
        out.append(
            {
                "title": title_el.get_text(strip=True),
                "company": company_el.get_text(strip=True),
                "location": region_el.get_text(strip=True) if region_el else "Remote",
                "url": full,
                "source": "WeWorkRemotely",
            }
        )
        if len(out) >= limit:
            break
    return out


def cmd_search(args: argparse.Namespace) -> int:
    timeout = int(os.getenv("HTTP_TIMEOUT_SECONDS", "25"))
    limit = max(1, args.limit)
    query = (args.query or os.getenv("JOB_QUERY", "developer")).strip()
    jobs: list[dict[str, Any]] = []
    try:
        jobs.extend(fetch_remoteok(query, limit, timeout))
    except Exception as e:
        print(f"[WARN] RemoteOK: {e}", file=sys.stderr)
    try:
        wwr = fetch_weworkremotely(query, limit, timeout)
        seen = {j["url"] for j in jobs}
        for j in wwr:
            if j["url"] not in seen:
                jobs.append(j)
                seen.add(j["url"])
            if len(jobs) >= limit * 2:
                break
    except Exception as e:
        print(f"[WARN] WeWorkRemotely: {e}", file=sys.stderr)

    if args.json:
        print(json.dumps({"query": query, "jobs": jobs[: limit * 2]}, indent=2))
        return 0

    if not jobs:
        print(f"No jobs found for query: {query!r}")
        return 1

    print(f"Job search results for: {query!r}\n")
    for i, j in enumerate(jobs[: limit * 2], 1):
        print(f"{i}. {j['title']} — {j['company']}")
        print(f"   {j['location']} | {j['source']}")
        print(f"   {j['url']}\n")
    return 0


IMPROVE_SYSTEM = """You are an expert career coach and technical recruiter.
Analyze the resume against the job description (if provided). Be honest and actionable.

Respond with ONLY valid JSON (no markdown) with this shape:
{
  "fit_summary": "2-4 sentences on overall fit",
  "strengths_for_role": ["bullet", "..."],
  "gaps_or_risks": ["bullet", "..."],
  "keyword_alignment": ["suggested keywords or phrases to weave in naturally"],
  "bullet_rewrites": [
    { "original_snippet": "short quote from resume", "improved": "stronger bullet with metrics if plausible" }
  ],
  "ats_tips": ["short tip", "..."],
  "revised_professional_summary": "optional 2-3 sentence summary; empty string if not applicable",
  "interview_talking_points": ["point", "..."]
}

If no job description is given, still improve the resume for clarity, impact, and ATS; set fit_summary accordingly."""


def cmd_improve(args: argparse.Namespace) -> int:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("Set OPENAI_API_KEY in .env or environment.", file=sys.stderr)
        return 1

    try:
        from openai import OpenAI
    except ImportError as e:
        print("Install openai: pip install openai", file=sys.stderr)
        return 1

    resume_path = Path(args.resume).expanduser().resolve()
    resume_text = _read_resume_text(resume_path)
    if len(resume_text) < 50:
        print("Resume text is very short. Check file encoding or PDF extractability.", file=sys.stderr)

    jd_text = ""
    if args.job:
        jd_path = Path(args.job).expanduser().resolve()
        jd_text = _read_text_file(jd_path)

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)

    user_content = (
        "Here is the resume text:\n\n"
        + resume_text[:120_000]
        + ("\n\n--- JOB DESCRIPTION ---\n\n" + jd_text[:80_000] if jd_text else "")
    )

    try:
        completion = client.chat.completions.create(
            model=model,
            temperature=0.4,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": IMPROVE_SYSTEM},
                {"role": "user", "content": user_content},
            ],
        )
    except Exception as e:
        print(f"OpenAI request failed: {e}", file=sys.stderr)
        return 1

    raw = (completion.choices[0].message.content or "").strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        print("Model did not return valid JSON. Raw output:\n", raw[:2000])
        return 1

    text_report = _format_improvement_report(parsed)

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.write_text(text_report + "\n\n--- JSON ---\n" + json.dumps(parsed, indent=2), encoding="utf-8")
        print(f"Wrote report to {out_path}")
    else:
        print(text_report)

    return 0


def _format_improvement_report(data: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("=== Resume improvement report ===\n")
    lines.append(data.get("fit_summary", "") + "\n")

    def section(title: str, key: str) -> None:
        items = data.get(key)
        if not isinstance(items, list) or not items:
            return
        lines.append(f"\n## {title}\n")
        for x in items:
            if isinstance(x, str):
                lines.append(f"- {x}")
            elif isinstance(x, dict):
                lines.append(f"- {json.dumps(x)}")

    section("Strengths for this role", "strengths_for_role")
    section("Gaps or risks", "gaps_or_risks")
    section("Keyword alignment", "keyword_alignment")
    section("ATS tips", "ats_tips")
    section("Interview talking points", "interview_talking_points")

    br = data.get("bullet_rewrites")
    if isinstance(br, list) and br:
        lines.append("\n## Suggested bullet rewrites\n")
        for item in br:
            if not isinstance(item, dict):
                continue
            orig = item.get("original_snippet", "")
            imp = item.get("improved", "")
            lines.append(f"\nFrom: {orig}\nTo:   {imp}\n")

    summary = data.get("revised_professional_summary")
    if isinstance(summary, str) and summary.strip():
        lines.append("\n## Revised professional summary\n")
        lines.append(summary.strip())

    return "\n".join(lines).strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI job search + resume improvement agent",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Search remote job boards")
    p_search.add_argument("--query", "-q", help="Keywords (default: JOB_QUERY env or 'developer')")
    p_search.add_argument("--limit", "-n", type=int, default=15, help="Max jobs per source (default 15)")
    p_search.add_argument("--json", action="store_true", help="Print JSON instead of text")
    p_search.set_defaults(func=cmd_search)

    p_imp = sub.add_parser("improve", help="AI resume review / improvement")
    p_imp.add_argument("--resume", "-r", required=True, help="Path to resume (.txt, .md, or .pdf)")
    p_imp.add_argument("--job", "-j", help="Path to job description text file")
    p_imp.add_argument("--out", "-o", help="Write full report + JSON to this file")
    p_imp.set_defaults(func=cmd_improve)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
