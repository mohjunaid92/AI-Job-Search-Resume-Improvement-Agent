import hashlib
import json
import os
import smtplib
import time
from dataclasses import dataclass
from email.mime.text import MIMEText
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class JobItem:
    title: str
    company: str
    location: str
    url: str
    source: str

    @property
    def unique_id(self) -> str:
        raw = f"{self.source}|{self.title}|{self.company}|{self.url}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class JobScraperAgent:
    def __init__(self) -> None:
        self.query = os.getenv("JOB_QUERY", "python developer").strip()
        self.interval_minutes = int(os.getenv("CHECK_INTERVAL_MINUTES", "30"))
        self.storage_path = Path(os.getenv("SEEN_JOBS_FILE", "seen_jobs.json"))
        self.timeout = int(os.getenv("HTTP_TIMEOUT_SECONDS", "20"))
        self.max_per_source = int(os.getenv("MAX_JOBS_PER_SOURCE", "20"))
        self.seen = self._load_seen()

    def _load_seen(self) -> set[str]:
        if not self.storage_path.exists():
            return set()
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            return set(data)
        except Exception:
            return set()

    def _save_seen(self) -> None:
        self.storage_path.write_text(
            json.dumps(sorted(self.seen), indent=2),
            encoding="utf-8",
        )

    def _fetch_remoteok(self) -> List[JobItem]:
        url = "https://www.naukri.com/jobs-in-ghaziabad"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        jobs: List[JobItem] = []
        rows = soup.select("tr.job")
        for row in rows[: self.max_per_source]:
            title_el = row.select_one("h2")
            company_el = row.select_one("h3")
            link_el = row.select_one("a.preventLink")
            if not title_el or not company_el or not link_el:
                continue
            href = link_el.get("href", "").strip()
            full_url = f"https://remoteok.com{href}" if href.startswith("/") else href
            jobs.append(
                JobItem(
                    title=title_el.get_text(strip=True),
                    company=company_el.get_text(strip=True),
                    location="Remote",
                    url=full_url,
                    source="RemoteOK",
                )
            )
        return jobs

    def _fetch_weworkremotely(self) -> List[JobItem]:
        url = "https://www.naukri.com/jobs-in-ghaziabad" + requests.utils.quote(
            self.query
        )
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        jobs: List[JobItem] = []
        for article in soup.select("article li")[: self.max_per_source]:
            link = article.select_one("a")
            title = article.select_one(".title")
            company = article.select_one(".company")
            region = article.select_one(".region.company")
            if not link or not title or not company:
                continue
            href = link.get("href", "").strip()
            full_url = f"https://weworkremotely.com{href}" if href.startswith("/") else href
            jobs.append(
                JobItem(
                    title=title.get_text(strip=True),
                    company=company.get_text(strip=True),
                    location=region.get_text(strip=True) if region else "Remote",
                    url=full_url,
                    source="WeWorkRemotely",
                )
            )
        return jobs

    def scrape_jobs(self) -> List[JobItem]:
        all_jobs: List[JobItem] = []
        sources = [
            ("RemoteOK", self._fetch_remoteok),
            ("WeWorkRemotely", self._fetch_weworkremotely),
        ]
        for source_name, source_func in sources:
            try:
                all_jobs.extend(source_func())
            except Exception as exc:
                print(f"[WARN] Failed to fetch {source_name}: {exc}")
        return all_jobs

    def filter_new_jobs(self, jobs: List[JobItem]) -> List[JobItem]:
        new_jobs: List[JobItem] = []
        for job in jobs:
            if self.query.lower() not in (
                f"{job.title} {job.company} {job.location}".lower()
            ):
                continue
            job_id = job.unique_id
            if job_id in self.seen:
                continue
            self.seen.add(job_id)
            new_jobs.append(job)
        return new_jobs

    def _format_message(self, jobs: List[JobItem]) -> str:
        lines = [f"New jobs found for '{self.query}':", ""]
        for idx, job in enumerate(jobs, start=1):
            lines.extend(
                [
                    f"{idx}. {job.title} - {job.company}",
                    f"   Location: {job.location}",
                    f"   Source: {job.source}",
                    f"   Link: {job.url}",
                    "",
                ]
            )
        return "\n".join(lines).strip()

    def send_telegram(self, message: str) -> None:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not token or not chat_id:
            return
        endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        response = requests.post(endpoint, json=payload, timeout=self.timeout)
        response.raise_for_status()
        print("[INFO] Telegram notification sent.")

    def send_email(self, message: str) -> None:
        host = os.getenv("SMTP_HOST", "").strip()
        port = int(os.getenv("SMTP_PORT", "587"))
        username = os.getenv("SMTP_USERNAME", "").strip()
        password = os.getenv("SMTP_PASSWORD", "").strip()
        sender = os.getenv("EMAIL_FROM", "").strip()
        receiver = os.getenv("EMAIL_TO", "").strip()
        if not all([host, username, password, sender, receiver]):
            return

        msg = MIMEText(message, "plain", "utf-8")
        msg["Subject"] = f"Job Alerts: {self.query}"
        msg["From"] = sender
        msg["To"] = receiver

        with smtplib.SMTP(host, port, timeout=self.timeout) as server:
            server.starttls()
            server.login(username, password)
            server.sendmail(sender, [receiver], msg.as_string())
        print("[INFO] Email notification sent.")

    def notify(self, jobs: List[JobItem]) -> None:
        if not jobs:
            print("[INFO] No new jobs found.")
            return
        message = self._format_message(jobs)
        self.send_telegram(message)
        self.send_email(message)
        print(f"[INFO] Sent notifications for {len(jobs)} new job(s).")

    def run_once(self) -> None:
        print(f"[INFO] Scraping jobs for query: {self.query}")
        jobs = self.scrape_jobs()
        new_jobs = self.filter_new_jobs(jobs)
        self.notify(new_jobs)
        self._save_seen()

    def run_forever(self) -> None:
        print(
            f"[INFO] Job agent started. Checking every {self.interval_minutes} minute(s)."
        )
        while True:
            self.run_once()
            time.sleep(self.interval_minutes * 60)


if __name__ == "__main__":
    agent = JobScraperAgent()
    run_mode = os.getenv("RUN_MODE", "once").strip().lower()
    if run_mode == "loop":
        agent.run_forever()
    else:
        agent.run_once()
