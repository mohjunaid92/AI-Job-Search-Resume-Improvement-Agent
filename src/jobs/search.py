import httpx

from src.config import settings
from src.jobs.india_filter import is_job_eligible_for_india, normalize_india_location

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"


def _format_remotive_job(job: dict) -> dict:
    return {
        "title": job.get("title", ""),
        "company": job.get("company_name", ""),
        "location": job.get("candidate_required_location", "Remote"),
        "description": (job.get("description") or "")[:2000],
        "url": job.get("url", ""),
        "source": "remotive",
        "tags": job.get("tags", []),
    }


def _search_remotive(query: str, limit: int = 10, india_only: bool = True) -> list[dict]:
    """Free job API — no API key required."""
    params = {}
    if query.strip():
        params["search"] = query.strip()

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(REMOTIVE_URL, params=params)
        resp.raise_for_status()
        jobs = resp.json().get("jobs", [])

    results = [_format_remotive_job(job) for job in jobs]

    if india_only:
        results = [j for j in results if is_job_eligible_for_india(j)]

    return results[:limit]


def _search_adzuna(
    query: str,
    location: str = "",
    limit: int = 10,
    country: str | None = None,
) -> list[dict]:
    """Adzuna free tier — requires app id/key from developer.adzuna.com."""
    country_code = (country or settings.adzuna_country).lower()
    url = f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/1"
    params = {
        "app_id": settings.adzuna_app_id,
        "app_key": settings.adzuna_app_key,
        "results_per_page": min(limit * 2, 20),
        "what": query,
    }
    where = location.strip()
    if where:
        params["where"] = where

    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for job in data.get("results", []):
        item = {
            "title": job.get("title", ""),
            "company": job.get("company", {}).get("display_name", ""),
            "location": job.get("location", {}).get("display_name", ""),
            "description": (job.get("description") or "")[:2000],
            "url": job.get("redirect_url", ""),
            "source": "adzuna",
            "tags": [],
        }
        if country_code == "in" and not is_job_eligible_for_india(item):
            # Adzuna India should already be local; keep unless clearly abroad-only
            loc = (item.get("location") or "").lower()
            if any(x in loc for x in ("united states", "usa", "canada", "uk only")):
                continue
        results.append(item)
        if len(results) >= limit:
            break
    return results


def search_jobs(
    query: str,
    location: str = "",
    limit: int = 10,
    prefer_adzuna: bool = True,
    india_only: bool = True,
    country: str | None = None,
) -> list[dict]:
    """
    Search jobs using free APIs.
    Defaults to India-only listings (local Adzuna + India-eligible remote).
    """
    country_code = (country or ("in" if india_only else settings.adzuna_country)).lower()
    search_location = normalize_india_location(location) if india_only else location

    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    def add_batch(batch: list[dict]) -> None:
        for job in batch:
            url = job.get("url", "")
            if url and url in seen_urls:
                continue
            if india_only and not is_job_eligible_for_india(job):
                continue
            if url:
                seen_urls.add(url)
            all_jobs.append(job)

    if prefer_adzuna and settings.has_adzuna:
        try:
            add_batch(
                _search_adzuna(
                    query,
                    search_location,
                    limit=limit * 3,
                    country=country_code,
                )
            )
        except httpx.HTTPError:
            pass

    if len(all_jobs) < limit:
        try:
            remotive_cap = max(limit * 5, 30) if india_only else limit
            remotive = _search_remotive(
                query,
                limit=remotive_cap,
                india_only=india_only,
            )
            add_batch(remotive)
        except httpx.HTTPError:
            pass

    return all_jobs[:limit]
