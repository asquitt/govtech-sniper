"""
Integrations Routes Package
============================
Split from single integrations.py (811 lines) into focused sub-modules.
"""

from fastapi import APIRouter

from app.api.routes.integrations.crud import router as crud_router
from app.api.routes.integrations.sso_and_sync import router as sso_and_sync_router

router = APIRouter(prefix="/integrations", tags=["Integrations"])
router.include_router(crud_router)
router.include_router(sso_and_sync_router)
