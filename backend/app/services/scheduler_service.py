from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, delete
from datetime import datetime, timedelta
import pytz
import logging

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.models import Job, DailyTask
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
            # Run the job matching agent
            agent = JobMatchingAgent()
            result = await agent.run()

            if result.get("success"):
                logger.info(f"Daily push complete: {result.get('jobs_found')} jobs found")
                # TODO: Send email notification when email service is implemented
            else:
                logger.error(f"Daily push failed: {result.get('error')}")

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
                    delete(Job).where(Job.searched_at < cutoff_date)
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
