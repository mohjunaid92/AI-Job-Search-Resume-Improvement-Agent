"""
AI Job Search & Resume Improvement Agent
Uses LangChain (Groq), CrewAI (multi-agent), and free job APIs.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from src.agents.crew_setup import run_job_search_crew
from src.config import settings
from src.jobs.search import search_jobs
from src.llm.factory import llm_status
from src.matching.matcher import match_resume_to_jobs
from src.pipeline import format_report_markdown, run_quick_pipeline_from_path
from src.report.pdf_export import export_report_pdf
from src.resume.analyzer import extract_skills
from src.resume.parser import load_resume_text

app = typer.Typer(help="Job search and resume improvement agent")
console = Console()

ProviderOpt = typer.Option("auto", "--provider", "-p", help="LLM: auto, groq, or ollama")


@app.command()
def ui():
    """Launch Streamlit web UI."""
    import subprocess

    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(_ROOT / "streamlit_app.py")],
        check=True,
    )


@app.command()
def analyze(
    resume: Path = typer.Argument(..., help="Path to resume (.pdf, .docx, .txt)"),
    provider: str = ProviderOpt,
):
    """Extract skills and profile summary from a resume (LangChain)."""
    text = load_resume_text(resume)
    data = extract_skills(text, provider=provider)  # type: ignore[arg-type]
    console.print(Panel.fit("Resume analysis", style="bold cyan"))
    console.print_json(data=data)


@app.command()
def jobs(
    query: str = typer.Argument(..., help="Job search keywords"),
    location: str = typer.Option("India", help="City or region (e.g. Ghaziabad, Bangalore)"),
    limit: int = typer.Option(8, help="Max jobs"),
    resume: Path | None = typer.Option(None, help="Resume for skill matching"),
    india_only: bool = typer.Option(True, help="Filter to India / India-eligible roles"),
):
    """Search jobs via free APIs and optionally score against a resume."""
    skill_list: list[str] = []
    if resume:
        text = load_resume_text(resume)
        skill_list = extract_skills(text).get("skills", [])

    results = search_jobs(
        query=query,
        location=location,
        limit=limit,
        india_only=india_only,
    )
    if skill_list:
        results = match_resume_to_jobs(skill_list, results)

    table = Table(title=f"Jobs: {query}")
    table.add_column("Score", style="green")
    table.add_column("Title")
    table.add_column("Company")
    table.add_column("Source")

    for job in results:
        score = f"{job.get('match_score', '-')}%" if skill_list else "-"
        table.add_row(score, job.get("title", ""), job.get("company", ""), job.get("source", ""))

    console.print(table)
    console.print_json(data=results)


@app.command()
def run(
    resume: Path = typer.Argument(..., help="Path to resume"),
    query: str = typer.Option("", help="Job search query"),
    location: str = typer.Option("India", help="City or region"),
    output: Path | None = typer.Option(None, help="Save markdown report"),
    pdf: Path | None = typer.Option(None, help="Save PDF report"),
    provider: str = ProviderOpt,
    india_only: bool = typer.Option(True, help="India-only job filter"),
):
    """Run full CrewAI pipeline: analyze, search, recommend, interview prep."""
    try:
        llm_status(provider)  # type: ignore[arg-type]
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc

    console.print(Panel.fit("Starting multi-agent crew...", style="bold magenta"))
    crew_report = run_job_search_crew(
        str(resume),
        job_query=query,
        location=location,
        provider=provider,  # type: ignore[arg-type]
        india_only=india_only,
    )
    data = run_quick_pipeline_from_path(
        str(resume),
        job_query=query,
        location=location,
        provider=provider,  # type: ignore[arg-type]
        include_recommendations=False,
        india_only=india_only,
    )
    report_md = format_report_markdown(data, crew_report=crew_report)
    console.print(Markdown(report_md))

    if output:
        output.write_text(report_md, encoding="utf-8")
        console.print(f"\n[green]Saved markdown to {output}[/green]")
    if pdf:
        export_report_pdf(report_md, pdf)
        console.print(f"[green]Saved PDF to {pdf}[/green]")


@app.command()
def quick(
    resume: Path = typer.Argument(..., help="Path to resume"),
    query: str = typer.Option("", help="Job search query"),
    location: str = typer.Option("India", help="City or region"),
    output: Path | None = typer.Option(None, help="Save markdown report"),
    pdf: Path | None = typer.Option(None, help="Save PDF report"),
    provider: str = ProviderOpt,
    india_only: bool = typer.Option(True, help="India-only job filter"),
):
    """Fast pipeline: analyze + search + match + LLM recommendations."""
    data = run_quick_pipeline_from_path(
        str(resume),
        job_query=query,
        location=location,
        provider=provider,  # type: ignore[arg-type]
        include_recommendations=True,
        india_only=india_only,
    )
    report_md = format_report_markdown(data)
    console.print(Markdown(report_md))

    if output:
        output.write_text(report_md, encoding="utf-8")
        console.print(f"\n[green]Saved markdown to {output}[/green]")
    if pdf:
        export_report_pdf(report_md, pdf)
        console.print(f"[green]Saved PDF to {pdf}[/green]")


@app.command()
def status():
    """Show which LLM providers are available."""
    for name in ("auto", "groq", "ollama"):
        try:
            info = llm_status(name)  # type: ignore[arg-type]
            console.print(f"[bold]{name}[/bold]: active={info['active']}")
        except ValueError as exc:
            console.print(f"[bold]{name}[/bold]: [red]{exc}[/red]")


if __name__ == "__main__":
    app()
