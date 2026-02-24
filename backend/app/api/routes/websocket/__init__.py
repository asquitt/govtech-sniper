"""
WebSocket Routes Package
========================
Split from single websocket.py (858 lines) into focused sub-modules.
"""

from fastapi import APIRouter

from app.api.routes.websocket.diagnostics import router as diagnostics_router
from app.api.routes.websocket.endpoints import router as endpoints_router
from app.api.routes.websocket.manager import manager  # noqa: F401 - re-export for other modules

router = APIRouter(tags=["WebSocket"])
router.include_router(endpoints_router)
router.include_router(diagnostics_router)

# Re-export utility functions used by other modules
from app.api.routes.websocket.endpoints import notify_task_complete, notify_user  # noqa: E402, F401
