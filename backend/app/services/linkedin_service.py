from typing import List, Optional
import logging
import httpx
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)


class LinkedInService:
    """Service for searching jobs using JSearch API (RapidAPI)."""

    def __init__(self):
        self._rapidapi_key = settings.RAPIDAPI_KEY
        self._base_url = "https://jsearch.p.rapidapi.com/search"

    async def search_jobs(
        self,
        keywords: str,
        location: Optional[str] = None,
        limit: int = 20,
        is_intern: bool = False,
        remote: Optional[str] = None
    ) -> List[dict]:
        """
        Search for jobs using JSearch API.

        Args:
            keywords: Search keywords (e.g., "React Frontend Developer")
            location: Location filter (e.g., "Boston, MA")
            limit: Maximum number of results
            is_intern: Filter for internship positions
            remote: Remote preference ("remote", "hybrid", "onsite")

        Returns:
            List of job dictionaries
        """
        # If no API key, use mock data for testing
        if not self._rapidapi_key:
            logger.warning("No RAPIDAPI_KEY configured, using mock data")
            return self._get_mock_jobs(keywords, location, is_intern, limit)

        try:
            # Build query
            query = keywords
            if location:
                query += f" in {location}"
            if is_intern:
                query += " intern"

            headers = {
                "X-RapidAPI-Key": self._rapidapi_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
            }

            params = {
                "query": query,
                "page": "1",
                "num_pages": "1"
            }

            if remote == "remote":
                params["remote_jobs_only"] = "true"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self._base_url,
                    headers=headers,
                    params=params,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

            jobs = data.get("data", [])
            processed_jobs = []

            for job in jobs[:limit]:
                try:
                    processed_jobs.append(self._process_job(job))
                except Exception as e:
                    logger.warning(f"Error processing job: {e}")
                    continue

            logger.info(f"JSearch API returned {len(processed_jobs)} jobs")
            return processed_jobs

        except Exception as e:
            logger.error(f"JSearch API error: {e}")
            # Fallback to mock data
            logger.info("Falling back to mock data")
            return self._get_mock_jobs(keywords, location, is_intern, limit)

    def _process_job(self, job: dict) -> dict:
        """Process raw job data from JSearch API."""
        return {
            "linkedin_job_id": job.get("job_id", str(uuid.uuid4())),
            "title": job.get("job_title", "Unknown Title"),
            "company": job.get("employer_name", "Unknown Company"),
            "location": job.get("job_city", "") + (", " + job.get("job_state", "") if job.get("job_state") else ""),
            "salary": self._format_salary(job),
            "url": job.get("job_apply_link", ""),
            "description": job.get("job_description", "")[:2000],
            "posted_at": job.get("job_posted_at_datetime_utc", "")
        }

    def _format_salary(self, job: dict) -> str:
        """Format salary information."""
        min_sal = job.get("job_min_salary")
        max_sal = job.get("job_max_salary")
        if min_sal and max_sal:
            return f"${int(min_sal):,} - ${int(max_sal):,}"
        elif min_sal:
            return f"${int(min_sal):,}+"
        elif max_sal:
            return f"Up to ${int(max_sal):,}"
        return ""

    def _get_mock_jobs(self, keywords: str, location: Optional[str], is_intern: bool, limit: int) -> List[dict]:
        """Return mock job data for testing."""
        base_jobs = [
            {
                "linkedin_job_id": f"mock-{uuid.uuid4().hex[:8]}",
                "title": f"Senior {keywords} Developer" if not is_intern else f"{keywords} Intern",
                "company": "TechCorp Inc.",
                "location": location or "San Francisco, CA",
                "salary": "$120,000 - $180,000" if not is_intern else "$25/hour",
                "url": "https://example.com/job/1",
                "description": f"We are looking for a talented {keywords} professional to join our team. Requirements: 3+ years experience, strong problem-solving skills, excellent communication. Benefits include health insurance, 401k, remote work options.",
                "posted_at": "2024-01-15"
            },
            {
                "linkedin_job_id": f"mock-{uuid.uuid4().hex[:8]}",
                "title": f"{keywords} Engineer" if not is_intern else f"{keywords} Summer Intern",
                "company": "StartupXYZ",
                "location": location or "New York, NY",
                "salary": "$100,000 - $150,000" if not is_intern else "$30/hour",
                "url": "https://example.com/job/2",
                "description": f"Exciting opportunity for a {keywords} specialist! Join our fast-growing startup. We value innovation, teamwork, and continuous learning. Full benefits package included.",
                "posted_at": "2024-01-14"
            },
            {
                "linkedin_job_id": f"mock-{uuid.uuid4().hex[:8]}",
                "title": f"Full Stack {keywords} Developer" if not is_intern else f"Junior {keywords} Intern",
                "company": "BigTech Global",
                "location": location or "Seattle, WA",
                "salary": "$130,000 - $200,000" if not is_intern else "$28/hour",
                "url": "https://example.com/job/3",
                "description": f"BigTech Global is hiring! We need a skilled {keywords} developer with experience in modern technologies. Remote-friendly, excellent work-life balance, competitive compensation.",
                "posted_at": "2024-01-13"
            },
            {
                "linkedin_job_id": f"mock-{uuid.uuid4().hex[:8]}",
                "title": f"{keywords} Lead" if not is_intern else f"{keywords} Co-op",
                "company": "Innovation Labs",
                "location": location or "Boston, MA",
                "salary": "$150,000 - $220,000" if not is_intern else "$32/hour",
                "url": "https://example.com/job/4",
                "description": f"Lead our {keywords} team! Looking for experienced professionals who can mentor junior developers and drive technical decisions. Equity options available.",
                "posted_at": "2024-01-12"
            },
            {
                "linkedin_job_id": f"mock-{uuid.uuid4().hex[:8]}",
                "title": f"Remote {keywords} Specialist" if not is_intern else f"Part-time {keywords} Intern",
                "company": "RemoteFirst Co.",
                "location": "Remote",
                "salary": "$110,000 - $160,000" if not is_intern else "$22/hour",
                "url": "https://example.com/job/5",
                "description": f"100% remote position for {keywords} experts. Flexible hours, async communication, global team. Must be self-motivated and have excellent written communication skills.",
                "posted_at": "2024-01-11"
            }
        ]
        return base_jobs[:limit]

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
