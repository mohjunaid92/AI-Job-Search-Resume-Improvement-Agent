"""
Streamlit UI for the Job Search & Resume Improvement Agent.
Run: streamlit run streamlit_app.py
"""

import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from src.agents.crew_setup import run_job_search_crew
from src.llm.factory import llm_status
from src.pipeline import format_report_markdown, run_quick_pipeline
from src.report.pdf_export import export_report_pdf_to_buffer
from src.resume.parser import load_resume_text

st.set_page_config(
    page_title="Job Search & Resume Agent",
    page_icon="briefcase",
    layout="wide",
)

st.title("AI Job Search & Resume Improvement Agent")
st.caption("LangChain + CrewAI · Groq or Ollama.")


@st.cache_data(ttl=60)
def _cached_llm_status(provider: str) -> dict:
    try:
        return llm_status(provider)  # type: ignore[arg-type]
    except Exception:
        return {"active": "none", "groq_configured": False, "ollama_reachable": False}


with st.sidebar:
    st.header("Settings")
    provider = st.selectbox(
        "LLM provider",
        options=["auto", "groq", "ollama"],
        format_func=lambda x: {
            "auto": "Auto (Groq → Ollama)",
            "groq": "Groq (cloud, free tier)",
            "ollama": "Ollama (local, free)",
        }[x],
    )
    status = _cached_llm_status(provider)
    st.markdown("**LLM status**")
    st.write(f"Active: `{status.get('active', 'none')}`")
    st.write(f"Groq configured: {status.get('groq_configured')}")
    st.write(f"Ollama reachable: {status.get('ollama_reachable')}")

    job_query = st.text_input("Job search query", placeholder="e.g. Junior Python developer")
    india_only = st.checkbox("India only (nearby / remote for India)", value=True)
    location = st.text_input(
        "City or region",
        value="India",
        placeholder="e.g. Ghaziabad, Bangalore, Mumbai",
        help="Used for Adzuna India search. Pick your city for nearby on-site/hybrid roles.",
    )
    run_mode = st.radio(
        "Run mode",
        ["Quick (faster)", "Full crew (3 agents, slower)"],
    )
    st.divider()
    st.markdown(
       " This Agent can work on Both local llm or groq."
       "Created By MOH JUNAID"
    )

uploaded = st.file_uploader(
    "Upload resume",
    type=["pdf", "docx", "txt"],
    help="Or use the sample resume below",
)

use_sample = st.checkbox("Use sample resume", value=uploaded is None)
col_run, col_clear = st.columns(2)

with col_run:
    start = st.button("Run analysis", type="primary", use_container_width=True)
with col_clear:
    if st.button("Clear results", use_container_width=True):
        st.session_state.pop("report_data", None)
        st.session_state.pop("report_md", None)
        st.rerun()


def _load_resume_bytes() -> str:
    if use_sample:
        return load_resume_text(_ROOT / "sample_resume.txt")
    if not uploaded:
        raise ValueError("Upload a resume or enable the sample resume.")
    suffix = Path(uploaded.name).suffix or ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name
    return load_resume_text(tmp_path)


if start:
    try:
        resume_text = _load_resume_bytes()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    provider_arg = provider  # type: ignore[assignment]

    with st.spinner("Running pipeline…"):
        try:
            if run_mode.startswith("Full"):
                if use_sample:
                    resume_path = str(_ROOT / "sample_resume.txt")
                else:
                    suffix = Path(uploaded.name).suffix or ".txt"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded.getvalue())
                        resume_path = tmp.name
                crew_report = run_job_search_crew(
                    resume_path,
                    job_query=job_query,
                    location=location,
                    provider=provider_arg,
                    india_only=india_only,
                )
                data = run_quick_pipeline(
                    resume_text,
                    job_query=job_query,
                    location=location,
                    provider=provider_arg,
                    include_recommendations=False,
                    india_only=india_only,
                )
                report_md = format_report_markdown(data, crew_report=crew_report)
            else:
                data = run_quick_pipeline(
                    resume_text,
                    job_query=job_query,
                    location=location,
                    provider=provider_arg,
                    include_recommendations=True,
                    india_only=india_only,
                )
                report_md = format_report_markdown(data)

            st.session_state["report_data"] = data
            st.session_state["report_md"] = report_md
        except ValueError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.exception(exc)

if "report_data" in st.session_state:
    data = st.session_state["report_data"]
    report_md = st.session_state["report_md"]

    tab_analysis, tab_jobs, tab_report = st.tabs(["Analysis", "Jobs", "Full report"])

    with tab_analysis:
        analysis = data.get("analysis", {})
        st.subheader("Professional summary")
        st.write(analysis.get("summary", "—"))
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Skills")
            for skill in analysis.get("skills", []):
                st.markdown(f"`{skill}` ")
        with c2:
            st.subheader("Strengths & gaps")
            st.write("**Strengths**")
            for s in analysis.get("strengths", []):
                st.markdown(f"- {s}")
            st.write("**Gaps**")
            for g in analysis.get("gaps", []):
                st.markdown(f"- {g}")

    with tab_jobs:
        st.subheader(
            f"Matches in {data.get('location', 'India')}: {data.get('search_query', '')}"
            if data.get("india_only", True)
            else f"Matches for: {data.get('search_query', '')}"
        )
        if not data.get("jobs"):
            st.warning(
                "No India-eligible jobs found for this query. "
                "Try another keyword, set your city (e.g. Ghaziabad), "
                "or add Adzuna keys in `.env` for more local listings."
            )
        for job in data.get("jobs", []):
            with st.expander(
                f"{job.get('title')} @ {job.get('company')} — {job.get('match_score', 0)}% match"
            ):
                st.write(job.get("location", ""))
                if job.get("url"):
                    st.link_button("View job", job["url"])
                st.progress(min(job.get("match_score", 0) / 100, 1.0))
                st.write("**Matched:**", ", ".join(job.get("matched_skills", [])[:12]) or "—")
                st.caption((job.get("description") or "")[:800])

    with tab_report:
        st.markdown(report_md)
        st.download_button(
            "Download Markdown",
            data=report_md,
            file_name="job_search_report.md",
            mime="text/markdown",
        )
        try:
            pdf_buf = export_report_pdf_to_buffer(report_md)
            st.download_button(
                "Download PDF",
                data=pdf_buf,
                file_name="job_search_report.pdf",
                mime="application/pdf",
            )
        except Exception as exc:
            st.warning(f"PDF export failed: {exc}. Use Markdown download instead.")

    if data.get("recommendations"):
        st.divider()
        st.subheader("Recommendations & interview prep")
        st.markdown(data["recommendations"])

else:
    st.info("Upload a resume (or use the sample) and click **Run analysis**.")






footer = """
<style>
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #0E1117;
    color: white;
    text-align: center;
    padding: 10px;
}
</style>

<div class="footer">
    Made with ❤️ by Junaid
</div>
"""

st.markdown(footer, unsafe_allow_html=True)