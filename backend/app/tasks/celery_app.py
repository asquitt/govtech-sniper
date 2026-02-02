"""
RFP Sniper - Celery Application Configuration
==============================================
"""

from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from app.config import settings

# Create Celery app
celery_app = Celery(
    "rfp_sniper",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.ingest_tasks",
        "app.tasks.analysis_tasks",
        "app.tasks.generation_tasks",
        "app.tasks.document_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    
    # Result expiration (24 hours)
    result_expires=86400,
    
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,       # 10 minutes hard limit
    
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Queues
    task_queues=(
        Queue("celery"),
        Queue("ingest"),
        Queue("analysis"),
        Queue("generation"),
        Queue("documents"),
        Queue("periodic"),
        Queue("maintenance"),
    ),

    # Beat schedule for periodic tasks
    beat_schedule={
        # Scan SAM.gov every 6 hours for new opportunities
        "scan-sam-gov-periodic": {
            "task": "app.tasks.ingest_tasks.periodic_sam_scan",
            "schedule": crontab(minute=0, hour="*/6"),
            "options": {"queue": "periodic"},
        },
        # Clean up expired context caches daily
        "cleanup-caches": {
            "task": "app.tasks.analysis_tasks.cleanup_expired_caches",
            "schedule": crontab(minute=0, hour=2),  # 2 AM UTC
            "options": {"queue": "maintenance"},
        },
    },
    
    # Task routing
    task_routes={
        "app.tasks.ingest_tasks.*": {"queue": "ingest"},
        "app.tasks.analysis_tasks.*": {"queue": "analysis"},
        "app.tasks.generation_tasks.*": {"queue": "generation"},
        "app.tasks.document_tasks.*": {"queue": "documents"},
    },
)
