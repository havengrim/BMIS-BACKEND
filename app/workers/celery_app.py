"""Celery application factory.

Start workers with:
    celery -A app.workers.celery_app worker --loglevel=info --pool=solo
    celery -A app.workers.celery_app beat   --loglevel=info   # scheduled tasks

Broker/backend both default to REDIS_URL (already required by the app).
Override via env vars CELERY_BROKER_URL / CELERY_RESULT_BACKEND if needed.
"""
import sys
import asyncio
import logging

# psycopg3 async requires SelectorEventLoop on Windows (ProactorEventLoop is not supported)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

logger = logging.getLogger(__name__)

_broker = settings.CELERY_BROKER_URL or settings.REDIS_URL
_backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

celery_app = Celery(
    "bmis",
    broker=_broker,
    backend=_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Reliability
    task_track_started=True,
    task_acks_late=True,          # re-queue if worker dies before ACK
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # one task at a time per worker thread
    # Result TTL
    result_expires=3600,
    # Routing: high-priority tasks go to a separate queue
    task_routes={
        "app.workers.tasks.notify_emergency_report": {"queue": "priority"},
        "app.workers.tasks.*": {"queue": "default"},
    },
    # Scheduled tasks (Celery Beat)
    beat_schedule={
        "cleanup-old-logs-weekly": {
            "task": "app.workers.tasks.cleanup_old_logs",
            "schedule": crontab(hour=2, minute=0, day_of_week=0),  # Sunday 02:00 UTC
            "args": (90,),
        },
    },
)

logger.info("Celery configured: broker=%s", _broker)
