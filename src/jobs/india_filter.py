"""Filter and normalize job listings for India-based candidates."""

from __future__ import annotations

import re

INDIAN_CITIES = (
    "india",
    "indian",
    "bangalore",
    "bengaluru",
    "mumbai",
    "delhi",
    "new delhi",
    "noida",
    "ghaziabad",
    "gurugram",
    "gurgaon",
    "hyderabad",
    "pune",
    "chennai",
    "kolkata",
    "ahmedabad",
    "jaipur",
    "lucknow",
    "kochi",
    "chandigarh",
    "indore",
    "bhopal",
    "remote india",
)

GLOBAL_REMOTE = (
    "worldwide",
    "anywhere",
    "any location",
    "global",
    "international",
    "no location restriction",
    "work from anywhere",
    "all locations",
    "any country",
    "emea apac",
    "apac",
    "asia pacific",
)

US_CANADA_ONLY = (
    "usa only",
    "us only",
    "u.s. only",
    "united states only",
    "canada only",
    "north america only",
    "usa timezones",
    "us timezones",
    "u.s. timezones",
    "must be in the us",
    "must be located in the us",
    "must be in the united states",
    "us-based only",
    "usa-based only",
)


def _blob(job: dict) -> str:
    parts = [
        job.get("location", ""),
        job.get("title", ""),
        (job.get("description") or "")[:600],
    ]
    return " ".join(str(p) for p in parts).lower()


def is_job_eligible_for_india(job: dict) -> bool:
    """
    True if the role is in India or open to India-based / worldwide remote candidates.
    Excludes US/Canada-only timezone restrictions.
    """
    loc = (job.get("location") or "").lower().strip()
    blob = _blob(job)

    if any(city in blob for city in INDIAN_CITIES):
        return True

    if any(term in blob for term in GLOBAL_REMOTE):
        return True

    if any(term in loc for term in US_CANADA_ONLY):
        return False

    us_canada_in_loc = re.search(
        r"\b(usa|u\.s\.|united states|canada)\b",
        loc,
    )
    if us_canada_in_loc and "timezone" in loc:
        return False

    if us_canada_in_loc and not any(term in blob for term in GLOBAL_REMOTE + INDIAN_CITIES):
        return False

    # Plain "Remote" with no geo restriction mentioned
    if loc in {"remote", ""} and not us_canada_in_loc:
        return True

    return False


def normalize_india_location(location: str) -> str:
    """Default empty location to India; keep city names for Adzuna `where`."""
    loc = location.strip()
    if loc:
        return loc
    return "India"
