"""
RFP Sniper - Admin Routes
==========================
Organization admin dashboard: user management, org settings, usage analytics.
"""

from fastapi import APIRouter

from .analytics import router as analytics_router
from .integrations import router as integrations_router
from .members import router as members_router
from .organization import router as organization_router

router = APIRouter(prefix="/admin", tags=["Admin"])
router.include_router(organization_router)
router.include_router(members_router)
router.include_router(analytics_router)
router.include_router(integrations_router)
