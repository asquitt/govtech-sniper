"""
RFP Routes Package
==================
Split from single rfps.py (935 lines) into focused sub-modules.
"""

from fastapi import APIRouter

from app.api.routes.rfps.crud import router as crud_router
from app.api.routes.rfps.snapshots import router as snapshots_router

router = APIRouter(prefix="/rfps", tags=["RFPs"])
router.include_router(crud_router)
router.include_router(snapshots_router)
