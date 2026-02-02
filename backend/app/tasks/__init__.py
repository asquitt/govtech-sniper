"""
RFP Sniper - Celery Tasks
==========================
Async task queue for long-running operations.
"""

from app.tasks.celery_app import celery_app
from app.tasks.ingest_tasks import ingest_sam_opportunities
from app.tasks.analysis_tasks import analyze_rfp, run_killer_filter
from app.tasks.generation_tasks import generate_proposal_section

__all__ = [
    "celery_app",
    "ingest_sam_opportunities",
    "analyze_rfp",
    "run_killer_filter",
    "generate_proposal_section",
]

