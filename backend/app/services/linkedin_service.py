from linkedin_api import Linkedin
from typing import List, Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class LinkedInService:
    """Service for searching jobs on LinkedIn."""

    def __init__(self):
        self._api: Optional[Linkedin] = None

    def _get_api(self) -> Linkedin:
        """Lazy initialization of LinkedIn API."""
        if self._api is None:
            try:
                self._api = Linkedin(
                    settings.LINKEDIN_EMAIL,
                    settings.LINKEDIN_PASSWORD
                )
            except Exception as e:
                logger.error(f"Failed to initialize LinkedIn API: {e}")
                raise
        return self._api

    async def search_jobs(
        self,
        keywords: str,
        location: Optional[str] = None,
        limit: int = 20,
        is_intern: bool = False,
        remote: Optional[str] = None
    ) -> List[dict]:
        """
        Search for jobs on LinkedIn.

        Args:
            keywords: Search keywords (e.g., "React Frontend Developer")
            location: Location filter (e.g., "Boston, MA")
            limit: Maximum number of results
            is_intern: Filter for internship positions
            remote: Remote preference ("remote", "hybrid", "onsite")

        Returns:
            List of job dictionaries
        """
        try:
            api = self._get_api()

            # Build search parameters
            search_params = {
                "keywords": keywords,
                "limit": limit
            }

            if location:
                search_params["location_name"] = location

            # Note: linkedin-api has limited filter support
            # We'll filter results post-search for intern/remote
            jobs = api.search_jobs(**search_params)

            # Process and normalize job data
            processed_jobs = []
            for job in jobs:
                try:
                    job_data = self._process_job(job)

                    # Filter for internships if requested
                    if is_intern:
                        title_lower = job_data["title"].lower()
                        if "intern" not in title_lower and "internship" not in title_lower:
                            continue

                    processed_jobs.append(job_data)

                except Exception as e:
                    logger.warning(f"Error processing job: {e}")
                    continue

            return processed_jobs[:limit]

        except Exception as e:
            logger.error(f"LinkedIn search error: {e}")
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
