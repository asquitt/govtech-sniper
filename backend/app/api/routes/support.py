"""Support center routes for help articles, tutorials, and in-app chat."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.services.auth_service import UserAuth

router = APIRouter(prefix="/support", tags=["support"])


class HelpArticle(BaseModel):
    id: str
    title: str
    category: str
    summary: str
    content: str
    tags: list[str]
    last_updated: str


class TutorialStep(BaseModel):
    title: str
    instruction: str
    route: str
    action_label: str | None = None


class InteractiveTutorial(BaseModel):
    id: str
    title: str
    feature: str
    estimated_minutes: int
    steps: list[TutorialStep]


class SupportChatRequest(BaseModel):
    message: str
    current_route: str | None = None


class SupportChatResponse(BaseModel):
    reply: str
    suggested_article_ids: list[str]
    suggested_tutorial_id: str | None = None
    generated_at: str


HELP_ARTICLES: list[HelpArticle] = [
    HelpArticle(
        id="getting-started-first-proposal",
        title="Getting Started: First Proposal in 15 Minutes",
        category="Onboarding",
        summary="Set up workspace, ingest an opportunity, analyze requirements, and generate a draft.",
        content=(
            "Use the guided setup wizard in the sidebar. Start with Opportunities, run Analysis, "
            "open Proposals, and export a submission-ready package."
        ),
        tags=["onboarding", "proposal", "analysis", "export"],
        last_updated="2026-02-10",
    ),
    HelpArticle(
        id="template-marketplace-playbook",
        title="Template Marketplace Playbook",
        category="Templates",
        summary="Use proposal-structure and compliance-matrix templates, then publish team variants.",
        content=(
            "Browse vertical templates by contract type and compliance vehicle. Fork to your library, "
            "customize placeholders, and publish private variants to the community marketplace."
        ),
        tags=["templates", "marketplace", "compliance", "proposal-structure"],
        last_updated="2026-02-10",
    ),
    HelpArticle(
        id="report-builder-guide",
        title="Report Builder and Delivery Guide",
        category="Reporting",
        summary="Create drag-and-drop report views, share with teammates, and schedule email delivery.",
        content=(
            "Open Reports, drag fields into your selected list, set filters, and save your view. "
            "Enable sharing and configure recipient schedules for automated email delivery."
        ),
        tags=["reports", "builder", "sharing", "email"],
        last_updated="2026-02-10",
    ),
    HelpArticle(
        id="security-and-governance-faq",
        title="Security and Governance FAQ",
        category="Compliance",
        summary="Understand data handling, access controls, and audit exports.",
        content=(
            "All protected API routes enforce RBAC checks. Governance events are logged and can be "
            "exported for audits from collaboration and admin surfaces."
        ),
        tags=["security", "rbac", "audit", "governance"],
        last_updated="2026-02-10",
    ),
]

TUTORIALS: list[InteractiveTutorial] = [
    InteractiveTutorial(
        id="tutorial-first-proposal",
        title="First Proposal Walkthrough",
        feature="Onboarding",
        estimated_minutes=8,
        steps=[
            TutorialStep(
                title="Open Opportunities",
                instruction="Ingest or create an opportunity to start the proposal lifecycle.",
                route="/opportunities",
                action_label="Open Opportunities",
            ),
            TutorialStep(
                title="Run Analysis",
                instruction="Generate requirements and compliance insights from the solicitation.",
                route="/analysis",
                action_label="Open Analysis",
            ),
            TutorialStep(
                title="Draft and Export",
                instruction="Create a proposal draft and export for delivery.",
                route="/proposals",
                action_label="Open Proposals",
            ),
        ],
    ),
    InteractiveTutorial(
        id="tutorial-template-marketplace",
        title="Template Marketplace Walkthrough",
        feature="Templates",
        estimated_minutes=6,
        steps=[
            TutorialStep(
                title="Review Vertical Proposal Kits",
                instruction="Pick an IT, construction, or professional-services proposal structure.",
                route="/templates",
                action_label="Open Templates",
            ),
            TutorialStep(
                title="Apply Compliance Matrix Template",
                instruction="Select a contract-vehicle matrix and fork it to your template library.",
                route="/templates",
            ),
            TutorialStep(
                title="Publish to Community",
                instruction="Share your tailored template so teammates can discover and reuse it.",
                route="/templates",
            ),
        ],
    ),
    InteractiveTutorial(
        id="tutorial-reports",
        title="Custom Reports Walkthrough",
        feature="Reporting",
        estimated_minutes=7,
        steps=[
            TutorialStep(
                title="Build a Field Layout",
                instruction="Drag fields into your selected column layout in Reports.",
                route="/reports",
                action_label="Open Reports",
            ),
            TutorialStep(
                title="Share Saved View",
                instruction="Share the report with specific teammates by email.",
                route="/reports",
            ),
            TutorialStep(
                title="Schedule Delivery",
                instruction="Configure a weekly digest and verify delivery preview.",
                route="/reports",
            ),
        ],
    ),
]


def _select_support_response(message: str) -> tuple[str, list[str], str | None]:
    query = message.lower()
    if any(token in query for token in ("template", "marketplace", "compliance matrix")):
        return (
            "Use the Templates page to pick a vertical pack, fork it, and publish your variant.",
            ["template-marketplace-playbook"],
            "tutorial-template-marketplace",
        )
    if any(token in query for token in ("report", "dashboard", "email schedule", "share view")):
        return (
            "Open Reports and use the builder to choose fields, save a view, then configure delivery.",
            ["report-builder-guide"],
            "tutorial-reports",
        )
    if any(token in query for token in ("start", "first proposal", "onboarding", "setup")):
        return (
            "Launch the guided onboarding wizard from the sidebar to complete your first proposal flow.",
            ["getting-started-first-proposal"],
            "tutorial-first-proposal",
        )
    if any(token in query for token in ("security", "audit", "rbac", "compliance")):
        return (
            "Security controls are enforced on protected routes, and audit exports are available in-app.",
            ["security-and-governance-faq"],
            None,
        )
    return (
        "I can help with onboarding, templates, reporting, and governance workflows. Ask a specific question to get a guided path.",
        ["getting-started-first-proposal", "report-builder-guide"],
        None,
    )


@router.get("/help-center/articles", response_model=list[HelpArticle])
async def list_help_articles(
    q: str | None = Query(None, description="Search help article text"),
    category: str | None = Query(None, description="Filter by article category"),
    current_user: UserAuth = Depends(get_current_user),
) -> list[HelpArticle]:
    _ = current_user
    results = HELP_ARTICLES
    if category:
        results = [item for item in results if item.category.lower() == category.lower()]
    if q:
        query = q.lower()
        results = [
            item
            for item in results
            if query in item.title.lower()
            or query in item.summary.lower()
            or query in item.content.lower()
            or any(query in tag.lower() for tag in item.tags)
        ]
    return results


@router.get("/help-center/articles/{article_id}", response_model=HelpArticle)
async def get_help_article(
    article_id: str,
    current_user: UserAuth = Depends(get_current_user),
) -> HelpArticle:
    _ = current_user
    match = next((item for item in HELP_ARTICLES if item.id == article_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Help article not found")
    return match


@router.get("/tutorials", response_model=list[InteractiveTutorial])
async def list_interactive_tutorials(
    feature: str | None = Query(None, description="Filter by feature area"),
    current_user: UserAuth = Depends(get_current_user),
) -> list[InteractiveTutorial]:
    _ = current_user
    if not feature:
        return TUTORIALS
    return [item for item in TUTORIALS if item.feature.lower() == feature.lower()]


@router.get("/tutorials/{tutorial_id}", response_model=InteractiveTutorial)
async def get_interactive_tutorial(
    tutorial_id: str,
    current_user: UserAuth = Depends(get_current_user),
) -> InteractiveTutorial:
    _ = current_user
    tutorial = next((item for item in TUTORIALS if item.id == tutorial_id), None)
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")
    return tutorial


@router.post("/chat", response_model=SupportChatResponse)
async def support_chat(
    payload: SupportChatRequest,
    current_user: UserAuth = Depends(get_current_user),
) -> SupportChatResponse:
    _ = current_user
    reply, article_ids, tutorial_id = _select_support_response(payload.message)
    if payload.current_route and payload.current_route.startswith("/reports"):
        tutorial_id = tutorial_id or "tutorial-reports"
    return SupportChatResponse(
        reply=reply,
        suggested_article_ids=article_ids,
        suggested_tutorial_id=tutorial_id,
        generated_at=datetime.utcnow().isoformat(),
    )
