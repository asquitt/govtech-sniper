"""
Capture Routes Package
======================
Split from capture.py (858 lines) into sub-modules.
Re-exports a single combined router for backward compatibility.
"""

from fastapi import APIRouter

from app.api.routes.capture.bid_decision import router as bid_decision_router
from app.api.routes.capture.fields import router as fields_router
from app.api.routes.capture.gate_reviews import router as gate_reviews_router
from app.api.routes.capture.intelligence import router as intelligence_router
from app.api.routes.capture.plans import router as plans_router
from app.api.routes.capture.teaming import router as teaming_router

router = APIRouter(prefix="/capture", tags=["Capture"])
router.include_router(plans_router)
router.include_router(gate_reviews_router)
router.include_router(teaming_router)
router.include_router(fields_router)
router.include_router(intelligence_router)
router.include_router(bid_decision_router)
