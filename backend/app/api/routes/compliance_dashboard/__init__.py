"""
Compliance Dashboard Routes Package
====================================
Split from single compliance_dashboard.py (1413 lines) into focused sub-modules.
"""

from fastapi import APIRouter

from app.api.routes.compliance_dashboard.readiness import router as readiness_router
from app.api.routes.compliance_dashboard.trust_and_overview import (
    router as trust_and_overview_router,
)

router = APIRouter(prefix="/compliance", tags=["Compliance"])
router.include_router(readiness_router)
router.include_router(trust_and_overview_router)
