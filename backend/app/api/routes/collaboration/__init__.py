"""Collaboration routes package."""

from fastapi import APIRouter

from .compliance import router as compliance_router
from .helpers import _require_member_role
from .invitations import router as invitations_router
from .members import router as members_router
from .portal import router as portal_router
from .presence import router as presence_router
from .sharing import router as sharing_router
from .workspaces import router as workspaces_router

router = APIRouter(prefix="/collaboration", tags=["Collaboration"])

router.include_router(workspaces_router)
router.include_router(invitations_router)
router.include_router(members_router)
router.include_router(sharing_router)
router.include_router(compliance_router)
router.include_router(portal_router)
router.include_router(presence_router)

__all__ = ["router", "_require_member_role"]
