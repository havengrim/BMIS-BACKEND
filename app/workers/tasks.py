"""Celery task definitions for BMIS background jobs.

All async DB work uses asyncio.run() because Celery workers are sync by default.
For heavy async workloads consider using celery[gevent] or celery-pool-asyncio.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# User / Notifications                                                          #
# --------------------------------------------------------------------------- #


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email(self, user_id: str, email: str, full_name: str):
    """Send a welcome email after user registration.

    TODO: Integrate with AWS SES — replace the placeholder below with:
        from app.services.email_service import send_email
        asyncio.run(send_email(to=email, template="welcome", data={"name": full_name}))
    """
    try:
        logger.info(
            "TASK_WELCOME_EMAIL user_id=%s email=%s name=%r",
            user_id, email, full_name,
        )
        # Placeholder — add email service integration here
    except Exception as exc:
        logger.error("TASK_WELCOME_EMAIL_FAILED user_id=%s error=%s", user_id, exc)
        raise self.retry(exc=exc)


# --------------------------------------------------------------------------- #
# Emergency                                                                     #
# --------------------------------------------------------------------------- #


@celery_app.task(bind=True, max_retries=5, default_retry_delay=30)
def notify_emergency_report(self, report_id: str, incident_type: str, location: str):
    """Notify admins (SMS / push / email) when an emergency report is submitted.
    Runs in the 'priority' queue — ensure a worker subscribes to it:
        celery -A app.workers.celery_app worker -Q priority --loglevel=info
    """
    try:
        logger.warning(
            "TASK_EMERGENCY_NOTIFY report_id=%s type=%s location=%r",
            report_id, incident_type, location,
        )
        # TODO: Integrate push notifications / Twilio SMS / SES
    except Exception as exc:
        logger.error(
            "TASK_EMERGENCY_NOTIFY_FAILED report_id=%s error=%s", report_id, exc
        )
        raise self.retry(exc=exc)


# --------------------------------------------------------------------------- #
# Maintenance                                                                   #
# --------------------------------------------------------------------------- #


@celery_app.task
def cleanup_old_logs(days: int = 90) -> int:
    """Delete system_logs rows older than `days` days.
    Scheduled via Celery Beat every Sunday at 02:00 UTC.
    """

    async def _run() -> int:
        from sqlalchemy import delete

        from app.db.session import AsyncSessionLocal
        from app.modules.system_logs.model import SystemLog

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(SystemLog).where(SystemLog.created_at < cutoff)
            )
            await session.commit()
        count = result.rowcount
        logger.info(
            "TASK_CLEANUP_LOGS deleted=%d days=%d cutoff=%s",
            count, days, cutoff.isoformat(),
        )
        return count

    return asyncio.run(_run())


@celery_app.task(bind=True, max_retries=2)
def generate_blotter_pdf(self, blotter_id: str, requested_by: str):
    """Generate a PDF report for a blotter record and store it in S3.
    TODO: Implement with weasyprint / reportlab + boto3 upload.
    """
    try:
        logger.info(
            "TASK_BLOTTER_PDF blotter_id=%s requested_by=%s",
            blotter_id, requested_by,
        )
        # placeholder: pdf_bytes = render_blotter_pdf(blotter_id)
        # placeholder: upload_to_s3(pdf_bytes, key=f"blotters/{blotter_id}.pdf")
    except Exception as exc:
        logger.error(
            "TASK_BLOTTER_PDF_FAILED blotter_id=%s error=%s", blotter_id, exc
        )
        raise self.retry(exc=exc)
