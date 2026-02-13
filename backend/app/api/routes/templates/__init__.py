"""Templates routes package."""

from fastapi import APIRouter

from .crud import router as crud_router
from .models import ProposalTemplate
from .utils import _ensure_system_templates

router = APIRouter(prefix="/templates", tags=["Templates"])
router.include_router(crud_router)

__all__ = ["router", "ProposalTemplate", "_ensure_system_templates"]
