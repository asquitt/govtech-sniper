"""
Reviews Routes Package
======================
Split from single reviews.py (829 lines) into focused sub-modules.
"""

from fastapi import APIRouter

from app.api.routes.reviews.comments import router as comments_router
from app.api.routes.reviews.crud import router as crud_router

# Re-export for backward compat (used by export/compliance.py)
from app.api.routes.reviews.packet import get_review_packet  # noqa: F401
from app.api.routes.reviews.packet import router as packet_router

router = APIRouter(prefix="/reviews", tags=["Reviews"])
router.include_router(crud_router)
router.include_router(comments_router)
router.include_router(packet_router)
