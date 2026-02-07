"""
Draft Routes Package
====================
Split from single draft.py (999 lines) into focused sub-modules.
"""

from fastapi import APIRouter

from app.api.routes.draft.proposals import router as proposals_router
from app.api.routes.draft.sections import router as sections_router
from app.api.routes.draft.evidence import router as evidence_router
from app.api.routes.draft.submission_packages import router as packages_router
from app.api.routes.draft.generation import router as generation_router

router = APIRouter(prefix="/draft", tags=["Draft Generation"])
router.include_router(proposals_router)
router.include_router(sections_router)
router.include_router(evidence_router)
router.include_router(packages_router)
router.include_router(generation_router)
