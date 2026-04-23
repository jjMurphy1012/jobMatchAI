from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import exists, select, delete
from datetime import datetime, timedelta
import pytz
import logging

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.models import (
    Application,
    DailyTask,
    Job,
    JobPreference,
    Opportunity,
    Resume,
    User,
    UserJobMatch,
)
from app.services.agent_service import JobMatchingAgent

logger = logging.getLogger(__name__)

eastern = pytz.timezone(settings.TIMEZONE)


class SchedulerService:
    """Service for managing scheduled tasks."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False

    def start(self):
        """Start the scheduler with all jobs."""
        if self._is_running:
            return

        # Daily job push at 7:00 AM EST
        self.scheduler.add_job(
            self.daily_job_push,
            CronTrigger(
                hour=settings.PUSH_HOUR,
                minute=settings.PUSH_MINUTE,
                timezone=eastern
            ),
            id='daily_push',
            name='Daily Job Push',
            replace_existing=True
        )

        # Daily cleanup at 3:00 AM EST
        self.scheduler.add_job(
            self.cleanup_old_data,
            CronTrigger(
                hour=3,
                minute=0,
                timezone=eastern
            ),
            id='daily_cleanup',
            name='Daily Cleanup',
            replace_existing=True
        )

        self.scheduler.start()
        self._is_running = True
        logger.info("Scheduler started with daily jobs")

    def stop(self):
        """Stop the scheduler."""
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
            logger.info("Scheduler stopped")

    async def daily_job_push(self):
        """
        Daily job search and notification.
        Runs at 7:00 AM EST.
        """
        logger.info("Starting daily job push...")

        try:
            async with async_session_maker() as db:
                user_result = await db.execute(
                    select(User.id)
                    .join(Resume, Resume.user_id == User.id)
                    .join(JobPreference, JobPreference.user_id == User.id)
                    .where(User.is_disabled.is_(False))
                    .distinct()
                )
                user_ids = user_result.scalars().all()

            for user_id in user_ids:
                agent = JobMatchingAgent(user_id=user_id)
                result = await agent.run()
                if result.get("success"):
                    logger.info(f"Daily push complete for user {user_id}: {result.get('jobs_found')} jobs found")
                else:
                    logger.error(f"Daily push failed for user {user_id}: {result.get('error')}")

        except Exception as e:
            logger.error(f"Daily job push error: {e}")

    async def cleanup_old_data(self):
        """
        Clean up data older than DATA_RETENTION_DAYS.
        Runs at 3:00 AM EST.
        """
        logger.info("Starting daily cleanup...")

        cutoff_date = datetime.now(eastern) - timedelta(days=settings.DATA_RETENTION_DAYS)

        try:
            async with async_session_maker() as db:
                # Delete old daily tasks first (foreign key constraint)
                await db.execute(
                    delete(DailyTask).where(DailyTask.date < cutoff_date)
                )

                # Delete old jobs
                await db.execute(
                    delete(Job).where(
                        Job.searched_at < cutoff_date,
                        Job.is_applied.is_(False),
                        Job.cover_letter.is_(None),
                    )
                )

                await db.execute(
                    delete(UserJobMatch).where(
                        UserJobMatch.last_scored_at < cutoff_date,
                        UserJobMatch.cover_letter.is_(None),
                        ~exists(
                            select(Application.id).where(
                                Application.user_job_match_id == UserJobMatch.id
                            )
                        ),
                    )
                )

                await db.execute(
                    delete(Opportunity).where(
                        Opportunity.last_seen_at < cutoff_date,
                        ~exists(
                            select(UserJobMatch.id).where(
                                UserJobMatch.opportunity_id == Opportunity.id
                            )
                        ),
                        ~exists(
                            select(Application.id).where(
                                Application.opportunity_id == Opportunity.id
                            )
                        ),
                    )
                )

                await db.commit()
                logger.info(f"Cleaned up data older than {cutoff_date.date()}")

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    async def trigger_manual_push(self):
        """Manually trigger a job push (for testing/API)."""
        await self.daily_job_push()


# Global scheduler instance
scheduler_service = SchedulerService()
