from typing import List, Optional
import logging
import httpx
import uuid
import asyncio

logger = logging.getLogger(__name__)


class LinkedInService:
    """Service for searching jobs using free public APIs."""

    def __init__(self):
        # Free APIs - no key required
        self._remotive_url = "https://remotive.com/api/remote-jobs"
        self._arbeitnow_url = "https://arbeitnow.com/api/job-board-api"

    async def search_jobs(
        self,
        keywords: str,
        location: Optional[str] = None,
        limit: int = 20,
        is_intern: bool = False,
        remote: Optional[str] = None
    ) -> List[dict]:
        """
        Search for jobs using free public APIs.

        Uses Remotive API and Arbeitnow API (both free, no API key required).
        """
        all_jobs = []

        # Fetch from multiple free APIs in parallel
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [
                self._fetch_remotive(client, keywords),
                self._fetch_arbeitnow(client, keywords),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    all_jobs.extend(result)
                elif isinstance(result, Exception):
                    logger.warning(f"API fetch error: {result}")

        # Filter by keywords
        keywords_lower = keywords.lower().split()
        filtered_jobs = []
        for job in all_jobs:
            title_lower = job["title"].lower()
            desc_lower = job.get("description", "").lower()
            # Check if any keyword matches title or description
            if any(kw in title_lower or kw in desc_lower for kw in keywords_lower):
                # Filter for internships if requested
                if is_intern:
                    if "intern" not in title_lower and "internship" not in title_lower:
                        continue
                filtered_jobs.append(job)

        # If no matches, return all jobs (user might have specific keywords)
        if not filtered_jobs and all_jobs:
            filtered_jobs = all_jobs

        logger.info(f"Free APIs returned {len(filtered_jobs)} matching jobs")
        return filtered_jobs[:limit]

    async def _fetch_remotive(self, client: httpx.AsyncClient, keywords: str) -> List[dict]:
        """Fetch jobs from Remotive API (free, remote jobs)."""
        try:
            # Remotive has category-based search
            response = await client.get(self._remotive_url)
            response.raise_for_status()
            data = response.json()

            jobs = data.get("jobs", [])
            processed = []

            for job in jobs[:30]:  # Limit initial fetch
                processed.append({
                    "linkedin_job_id": f"remotive-{job.get('id', uuid.uuid4().hex[:8])}",
                    "title": job.get("title", "Unknown"),
                    "company": job.get("company_name", "Unknown"),
                    "location": job.get("candidate_required_location", "Remote"),
                    "salary": job.get("salary", ""),
                    "url": job.get("url", ""),
                    "description": job.get("description", "")[:2000],
                    "posted_at": job.get("publication_date", "")
                })

            logger.info(f"Remotive returned {len(processed)} jobs")
            return processed

        except Exception as e:
            logger.error(f"Remotive API error: {e}")
            return []

    async def _fetch_arbeitnow(self, client: httpx.AsyncClient, keywords: str) -> List[dict]:
        """Fetch jobs from Arbeitnow API (free, various jobs)."""
        try:
            response = await client.get(self._arbeitnow_url)
            response.raise_for_status()
            data = response.json()

            jobs = data.get("data", [])
            processed = []

            for job in jobs[:30]:  # Limit initial fetch
                processed.append({
                    "linkedin_job_id": f"arbeitnow-{job.get('slug', uuid.uuid4().hex[:8])}",
                    "title": job.get("title", "Unknown"),
                    "company": job.get("company_name", "Unknown"),
                    "location": job.get("location", ""),
                    "salary": "",  # Arbeitnow doesn't provide salary
                    "url": job.get("url", ""),
                    "description": job.get("description", "")[:2000],
                    "posted_at": job.get("created_at", "")
                })

            logger.info(f"Arbeitnow returned {len(processed)} jobs")
            return processed

        except Exception as e:
            logger.error(f"Arbeitnow API error: {e}")
            return []

    def _process_job(self, job: dict) -> dict:
        """Process raw job data from LinkedIn API."""
        # Extract job details
        job_id = job.get("entityUrn", "").split(":")[-1] if job.get("entityUrn") else None

        # Build job URL
        url = f"https://www.linkedin.com/jobs/view/{job_id}" if job_id else None

        return {
            "linkedin_job_id": job_id,
            "title": job.get("title", "Unknown Title"),
            "company": job.get("companyName", "Unknown Company"),
            "location": job.get("formattedLocation", ""),
            "salary": job.get("salaryInsights", {}).get("formattedSalary", ""),
            "url": url,
            "description": job.get("description", {}).get("text", "") if isinstance(job.get("description"), dict) else str(job.get("description", "")),
            "posted_at": job.get("listedAt", "")
        }

    async def get_job_details(self, job_id: str) -> Optional[dict]:
        """Get detailed information about a specific job."""
        try:
            api = self._get_api()
            job = api.get_job(job_id)
            return self._process_job(job) if job else None
        except Exception as e:
            logger.error(f"Error getting job details: {e}")
            return None
