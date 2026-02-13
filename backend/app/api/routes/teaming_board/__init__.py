"""Teaming Board routes package."""

from fastapi import APIRouter

from .discovery import router as discovery_router
from .gap_analysis import router as gap_analysis_router
from .ndas import router as ndas_router
from .profile import router as profile_router
from .ratings import router as ratings_router
from .requests import router as requests_router

router = APIRouter(prefix="/teaming", tags=["Teaming Board"])
router.include_router(discovery_router)
router.include_router(profile_router)
router.include_router(requests_router)
router.include_router(gap_analysis_router)
router.include_router(ndas_router)
router.include_router(ratings_router)

__all__ = ["router"]
