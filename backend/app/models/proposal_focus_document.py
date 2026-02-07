"""
RFP Sniper - Proposal Focus Document Model
============================================
Links proposals to specific knowledge base documents for targeted generation.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ProposalFocusDocument(SQLModel, table=True):
    """
    Links a proposal to specific knowledge base documents.
    When focus docs are set, generation uses only these instead of all user docs.
    """
    __tablename__ = "proposal_focus_documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    proposal_id: int = Field(foreign_key="proposals.id", index=True)
    document_id: int = Field(foreign_key="knowledge_base_documents.id", index=True)
    priority_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
