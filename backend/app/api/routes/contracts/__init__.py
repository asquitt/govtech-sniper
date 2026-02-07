"""
RFP Sniper - Contract Routes Package
====================================
Split from monolithic contracts.py for maintainability.
"""

from fastapi import APIRouter

from app.api.routes.contracts.core import router as core_router
from app.api.routes.contracts.deliverables import router as deliverables_router
from app.api.routes.contracts.tasks import router as tasks_router
from app.api.routes.contracts.cpars import router as cpars_router
from app.api.routes.contracts.status_reports import router as status_reports_router

router = APIRouter(prefix="/contracts", tags=["Contracts"])
router.include_router(core_router)
router.include_router(deliverables_router)
router.include_router(tasks_router)
router.include_router(cpars_router)
router.include_router(status_reports_router)
