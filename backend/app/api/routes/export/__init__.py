"""
Export Routes Package
======================
Split from single export.py (1163 lines) into focused sub-modules.
"""

from fastapi import APIRouter

from app.api.routes.export.compliance import router as compliance_router
from app.api.routes.export.documents import (
    create_docx_proposal as create_docx_proposal,
)
from app.api.routes.export.documents import (
    create_pdf_proposal as create_pdf_proposal,
)
from app.api.routes.export.documents import (
    router as documents_router,
)

router = APIRouter(prefix="/export", tags=["Export"])
router.include_router(documents_router)
router.include_router(compliance_router)
