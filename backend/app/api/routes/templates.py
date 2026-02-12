"""
RFP Sniper - Template Library Routes
=====================================
Pre-built proposal response templates for common requirements.
"""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import JSON, Column, Field, SQLModel, Text, select

from app.api.deps import UserAuth, get_current_user
from app.database import get_session

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/templates", tags=["Templates"])


# =============================================================================
# Template Models
# =============================================================================


class ProposalTemplate(SQLModel, table=True):
    """
    Pre-built response templates for common proposal requirements.
    """

    __tablename__ = "proposal_templates"

    id: int | None = Field(default=None, primary_key=True)

    # Template identification
    name: str = Field(max_length=255, index=True)
    category: str = Field(max_length=100, index=True)  # "Past Performance", "Technical", etc.
    subcategory: str | None = Field(default=None, max_length=100)

    # Template content
    description: str = Field(max_length=1000)
    template_text: str = Field(sa_column=Column(Text))

    # Placeholders that need to be filled
    # Format: {"company_name": "Your company name", "project_name": "Relevant project"}
    placeholders: dict = Field(default={}, sa_column=Column(JSON))

    # Metadata
    is_system: bool = Field(default=True)  # System templates vs user-created
    user_id: int | None = Field(default=None, foreign_key="users.id")  # For user templates
    usage_count: int = Field(default=0)

    # Keywords for matching
    keywords: list[str] = Field(default=[], sa_column=Column(JSON))

    # Marketplace fields
    is_public: bool = Field(default=False, index=True)
    rating_sum: int = Field(default=0)
    rating_count: int = Field(default=0)
    forked_from_id: int | None = Field(default=None, foreign_key="proposal_templates.id")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Request/Response Schemas
# =============================================================================


class TemplateCreate(BaseModel):
    """Create a new template."""

    name: str
    category: str
    subcategory: str | None = None
    description: str
    template_text: str
    placeholders: dict = {}
    keywords: list[str] = []


class TemplateUpdate(BaseModel):
    """Update a template."""

    name: str | None = None
    category: str | None = None
    subcategory: str | None = None
    description: str | None = None
    template_text: str | None = None
    placeholders: dict | None = None
    keywords: list[str] | None = None


class TemplateResponse(BaseModel):
    """Template response."""

    id: int
    name: str
    category: str
    subcategory: str | None
    description: str
    template_text: str
    placeholders: dict
    keywords: list[str]
    is_system: bool
    is_public: bool
    rating_sum: int
    rating_count: int
    forked_from_id: int | None
    user_id: int | None
    usage_count: int
    created_at: datetime
    updated_at: datetime


# =============================================================================
# System Templates (Pre-loaded)
# =============================================================================

SYSTEM_TEMPLATES = [
    {
        "name": "Past Performance - Federal Project",
        "category": "Past Performance",
        "subcategory": "Federal",
        "description": "Template for describing past performance on federal contracts",
        "template_text": """**Contract Reference: {project_name}**

**Client:** {agency_name}
**Contract Number:** {contract_number}
**Period of Performance:** {start_date} - {end_date}
**Contract Value:** ${contract_value}

**Project Description:**
{company_name} successfully delivered {service_description} in support of {agency_name}'s mission requirements. Our team of {team_size} professionals provided comprehensive {service_type} services.

**Key Accomplishments:**
• {accomplishment_1}
• {accomplishment_2}
• {accomplishment_3}

**Relevance to Current Requirement:**
This experience directly demonstrates our capability to {relevance_statement}. The technical complexity and scope align closely with the requirements outlined in Section {section_reference}.

**Performance Metrics:**
• On-time delivery rate: {delivery_rate}%
• Customer satisfaction: {satisfaction_rating}
• Quality metrics: {quality_metrics}

**Contracting Officer Reference:**
{cor_name}, {cor_title}
Email: {cor_email}
Phone: {cor_phone}""",
        "placeholders": {
            "project_name": "Project or contract name",
            "agency_name": "Federal agency name",
            "contract_number": "Contract/Task Order number",
            "start_date": "MM/YYYY",
            "end_date": "MM/YYYY or Present",
            "contract_value": "Total contract value",
            "company_name": "Your company name",
            "service_description": "Brief description of services",
            "service_type": "Type of services (IT, consulting, etc.)",
            "team_size": "Number of team members",
            "accomplishment_1": "Key accomplishment",
            "accomplishment_2": "Key accomplishment",
            "accomplishment_3": "Key accomplishment",
            "relevance_statement": "How this relates to current RFP",
            "section_reference": "RFP section reference",
            "delivery_rate": "Percentage",
            "satisfaction_rating": "Rating or score",
            "quality_metrics": "Quality achievements",
            "cor_name": "COR name",
            "cor_title": "COR title",
            "cor_email": "COR email",
            "cor_phone": "COR phone",
        },
        "keywords": ["past performance", "federal", "contract", "experience", "reference"],
    },
    {
        "name": "Technical Approach - Agile Methodology",
        "category": "Technical",
        "subcategory": "Methodology",
        "description": "Template for describing Agile software development approach",
        "template_text": """**Technical Approach: Agile Software Development**

{company_name} proposes an Agile methodology aligned with SAFe (Scaled Agile Framework) principles to ensure iterative delivery, continuous improvement, and stakeholder engagement throughout the {project_duration} period of performance.

**Sprint Cadence:**
We will execute {sprint_length}-week sprints with the following ceremonies:
• Sprint Planning (4 hours)
• Daily Stand-ups (15 minutes)
• Sprint Review/Demo ({demo_duration})
• Sprint Retrospective (2 hours)

**Team Structure:**
Our cross-functional team includes:
• Product Owner (Government-designated)
• Scrum Master: {scrum_master_name}
• Development Team: {dev_team_size} engineers
• QA Engineers: {qa_team_size}
• DevOps/SRE: {devops_team_size}

**Definition of Done:**
All user stories must meet the following criteria before acceptance:
• Code complete and peer-reviewed
• Unit tests written with >{test_coverage}% coverage
• Integration tests passing
• Security scan completed (no Critical/High findings)
• Documentation updated
• Product Owner acceptance

**Continuous Integration/Continuous Deployment:**
{ci_cd_description}

**Risk Mitigation:**
{risk_approach}

This approach has been successfully applied on {similar_project_count} similar federal engagements, consistently delivering on schedule and within budget.""",
        "placeholders": {
            "company_name": "Your company name",
            "project_duration": "Contract duration",
            "sprint_length": "2 or 3",
            "demo_duration": "Demo duration (e.g., 2 hours)",
            "scrum_master_name": "Proposed Scrum Master",
            "dev_team_size": "Number of developers",
            "qa_team_size": "Number of QA engineers",
            "devops_team_size": "Number of DevOps engineers",
            "test_coverage": "Code coverage percentage",
            "ci_cd_description": "CI/CD pipeline description",
            "risk_approach": "Risk mitigation approach",
            "similar_project_count": "Number of similar projects",
        },
        "keywords": ["agile", "scrum", "methodology", "sprint", "devops", "technical approach"],
    },
    {
        "name": "Quality Assurance Plan",
        "category": "Quality",
        "subcategory": "QA Plan",
        "description": "Template for Quality Assurance Plan section",
        "template_text": """**Quality Assurance Plan**

{company_name} is committed to delivering high-quality solutions that meet or exceed {agency_name}'s requirements. Our Quality Assurance Plan establishes systematic processes for ensuring quality throughout the project lifecycle.

**Quality Management System:**
Our QMS is {certification_type} certified and includes:
• Documented quality policies and procedures
• Regular internal audits
• Continuous improvement processes
• Corrective and preventive action tracking

**Quality Control Measures:**

*Development Phase:*
• Code reviews for 100% of deliverables
• Automated static code analysis
• Security vulnerability scanning
• Performance testing against defined baselines

*Testing Phase:*
• Unit testing (minimum {unit_test_coverage}% coverage)
• Integration testing
• System testing
• User acceptance testing (UAT)
• Regression testing for all changes

**Defect Management:**
{defect_process_description}

Priority levels and response times:
• Critical: {critical_response}
• High: {high_response}
• Medium: {medium_response}
• Low: {low_response}

**Quality Metrics:**
We track and report the following metrics {reporting_frequency}:
• Defect density
• Test coverage
• On-time delivery rate
• Customer satisfaction scores

**Continuous Improvement:**
{improvement_process}""",
        "placeholders": {
            "company_name": "Your company name",
            "agency_name": "Client agency",
            "certification_type": "ISO 9001:2015 or CMMI",
            "unit_test_coverage": "Coverage percentage",
            "defect_process_description": "Defect tracking process",
            "critical_response": "Response time for critical issues",
            "high_response": "Response time for high priority",
            "medium_response": "Response time for medium priority",
            "low_response": "Response time for low priority",
            "reporting_frequency": "Weekly/Monthly",
            "improvement_process": "Continuous improvement approach",
        },
        "keywords": ["quality", "QA", "testing", "defect", "CMMI", "ISO"],
    },
    {
        "name": "Key Personnel Resume",
        "category": "Personnel",
        "subcategory": "Resume",
        "description": "Template for key personnel resume/bio",
        "template_text": """**{person_name}**
**Proposed Role:** {proposed_role}
**Years of Experience:** {years_experience}
**Clearance:** {clearance_level}

**Professional Summary:**
{professional_summary}

**Education:**
• {degree_1}, {school_1}, {year_1}
• {degree_2}, {school_2}, {year_2}

**Certifications:**
• {cert_1}
• {cert_2}
• {cert_3}

**Relevant Experience:**

*{job_1_title}* | {job_1_company} | {job_1_dates}
{job_1_description}

*{job_2_title}* | {job_2_company} | {job_2_dates}
{job_2_description}

**Technical Skills:**
{technical_skills}

**Relevance to This Contract:**
{relevance_statement}""",
        "placeholders": {
            "person_name": "Full name",
            "proposed_role": "Role on this contract",
            "years_experience": "Total years of experience",
            "clearance_level": "Security clearance level",
            "professional_summary": "2-3 sentence summary",
            "degree_1": "Degree type and field",
            "school_1": "University name",
            "year_1": "Graduation year",
            "degree_2": "Additional degree",
            "school_2": "University name",
            "year_2": "Graduation year",
            "cert_1": "Certification",
            "cert_2": "Certification",
            "cert_3": "Certification",
            "job_1_title": "Job title",
            "job_1_company": "Company/Agency",
            "job_1_dates": "Date range",
            "job_1_description": "Job description",
            "job_2_title": "Job title",
            "job_2_company": "Company/Agency",
            "job_2_dates": "Date range",
            "job_2_description": "Job description",
            "technical_skills": "Comma-separated skills",
            "relevance_statement": "Why this person is right for this role",
        },
        "keywords": ["resume", "personnel", "key personnel", "bio", "experience"],
    },
    {
        "name": "Security Compliance Statement",
        "category": "Security",
        "subcategory": "Compliance",
        "description": "Template for security compliance and clearance statement",
        "template_text": """**Security Compliance Statement**

{company_name} maintains a robust security posture and is fully committed to meeting all security requirements outlined in the solicitation.

**Facility Clearance:**
{company_name} holds a {facility_clearance} facility clearance (FCL) granted by {granting_agency}.
• Cage Code: {cage_code}
• Commercial and Government Entity (CAGE) Code: {cage_code}

**Personnel Clearances:**
{clearance_summary}

All proposed personnel either currently hold or are eligible to obtain the required {required_clearance} clearance. We commit to ensuring all personnel have appropriate clearances prior to accessing any classified information or systems.

**Cybersecurity Compliance:**
Our organization complies with the following frameworks and standards:
• NIST SP 800-171 (CUI protection)
• NIST Cybersecurity Framework
• {additional_framework_1}
• {additional_framework_2}

**CMMC Status:**
{cmmc_status}

**Incident Response:**
{incident_response_summary}

**Security Training:**
All employees complete annual security awareness training covering:
• Insider threat awareness
• Phishing and social engineering
• Proper handling of CUI/classified information
• Physical security protocols

**Commitment:**
{company_name} acknowledges and accepts all security requirements outlined in {document_reference} and commits to full compliance throughout the period of performance.""",
        "placeholders": {
            "company_name": "Your company name",
            "facility_clearance": "SECRET/TOP SECRET",
            "granting_agency": "DCSA or other agency",
            "cage_code": "Your CAGE code",
            "clearance_summary": "Summary of personnel clearances",
            "required_clearance": "Required clearance level",
            "additional_framework_1": "Additional security framework",
            "additional_framework_2": "Additional security framework",
            "cmmc_status": "Current CMMC certification status",
            "incident_response_summary": "Incident response capability",
            "document_reference": "Security requirements document reference",
        },
        "keywords": ["security", "clearance", "NIST", "CMMC", "compliance", "classified"],
    },
    {
        "name": "Proposal Structure - IT Services",
        "category": "Proposal Structure",
        "subcategory": "IT Services",
        "description": "End-to-end proposal structure tuned for IT modernization and software delivery contracts.",
        "template_text": """# Volume I - Technical Proposal

## 1. Executive Summary
- Mission alignment with {agency_name}
- Business outcomes and value statement

## 2. Technical Understanding
- Current-state assessment
- Target architecture for {service_scope}
- Risk and dependency map

## 3. Technical Approach
- Agile delivery model and sprint cadence
- DevSecOps pipeline and release governance
- Data migration and interoperability plan

## 4. Cybersecurity & Compliance
- Zero trust controls and incident response
- CMMC/NIST mappings

## 5. Staffing and Key Personnel
- Program leadership
- Surge and continuity plan

## 6. Transition and Management
- Transition-in timeline (30/60/90 days)
- Quality management and KPI reporting

## 7. Past Performance
- Relevant contracts for {service_scope}

## 8. Pricing Narrative
- Basis of estimate and labor mix rationale""",
        "placeholders": {
            "agency_name": "Client agency",
            "service_scope": "Service scope",
        },
        "keywords": ["proposal structure", "it services", "devsecops", "agile", "modernization"],
        "is_public": True,
    },
    {
        "name": "Proposal Structure - Construction",
        "category": "Proposal Structure",
        "subcategory": "Construction",
        "description": "Structured proposal outline for design-build and federal construction programs.",
        "template_text": """# Volume I - Technical Proposal

## 1. Executive Summary
- Delivery approach for {project_type}
- Safety-first commitment

## 2. Project Understanding
- Site constraints and phasing
- Stakeholder and permitting dependencies

## 3. Construction Execution Plan
- Work breakdown and sequencing
- Trade partner management
- QA/QC checkpoints

## 4. Safety & Environmental Plan
- EM 385-1-1 safety controls
- Environmental compliance and reporting

## 5. Schedule Management
- Baseline schedule and critical path controls
- Weather and contingency strategy

## 6. Staffing and Subcontracting
- Superintendent and QC manager roles
- Small-business subcontracting plan

## 7. Past Performance
- Similar federal facility delivery records

## 8. Cost Narrative
- Cost realism assumptions and escalation factors""",
        "placeholders": {
            "project_type": "Project type",
        },
        "keywords": ["proposal structure", "construction", "design-build", "safety", "schedule"],
        "is_public": True,
    },
    {
        "name": "Proposal Structure - Professional Services",
        "category": "Proposal Structure",
        "subcategory": "Professional Services",
        "description": "Reusable proposal structure for advisory, PMO, and program support engagements.",
        "template_text": """# Volume I - Technical Proposal

## 1. Executive Summary
- Client challenge statement
- Outcomes and confidence plan

## 2. Approach to Performance Work Statement
- Task-by-task execution model
- Governance and decision cadence

## 3. Management Plan
- Program controls and escalation paths
- Staffing continuity and backfill strategy

## 4. Quality Assurance
- Deliverable quality gates
- Corrective-action workflow

## 5. Knowledge Transfer
- Onboarding playbook
- Transition-out and documentation controls

## 6. Key Personnel
- Leadership bios and role alignment

## 7. Past Performance
- Comparable advisory/program wins

## 8. Pricing Narrative
- Labor category rationale and assumptions""",
        "placeholders": {},
        "keywords": [
            "proposal structure",
            "professional services",
            "pmo",
            "advisory",
            "management",
        ],
        "is_public": True,
    },
    {
        "name": "Compliance Matrix - GSA MAS Task Order",
        "category": "Compliance Matrix",
        "subcategory": "GSA MAS",
        "description": "Pre-built compliance matrix format for MAS task orders with traceability fields.",
        "template_text": """| Solicitation Requirement | Reference | Response Owner | Status | Evidence Source |
| --- | --- | --- | --- | --- |
| Scope alignment to SIN and labor categories | Section L/M | Capture Lead | Not Started | Labor mapping workbook |
| Corporate experience relevance | PWS 3.0 | Proposal Manager | Not Started | Past performance library |
| Security and data handling controls | CUI clause package | Security Lead | Not Started | SSP and policies |
| Price narrative and basis of estimate | Pricing instructions | Pricing Lead | Not Started | BOE model |""",
        "placeholders": {},
        "keywords": ["compliance matrix", "gsa mas", "task order", "traceability"],
        "is_public": True,
    },
    {
        "name": "Compliance Matrix - OASIS+",
        "category": "Compliance Matrix",
        "subcategory": "OASIS+",
        "description": "Pre-built matrix template for OASIS+ service-order proposal compliance tracking.",
        "template_text": """| Requirement | RFP Reference | Assigned Team | Status | Validation Artifact |
| --- | --- | --- | --- | --- |
| Domain qualification and scope fit | Scope matrix | Capture Lead | Not Started | Domain qualification sheet |
| Staffing and labor qualifications | L.5 Personnel | HR Lead | Not Started | Resume package |
| Performance metrics and SLAs | PWS KPI section | Delivery Lead | Not Started | KPI plan |
| Risk management and mitigation | L.7 Risk | Program Manager | Not Started | Risk register |""",
        "placeholders": {},
        "keywords": ["compliance matrix", "oasis+", "services", "sla", "risk"],
        "is_public": True,
    },
    {
        "name": "Compliance Matrix - 8(a) STARS III",
        "category": "Compliance Matrix",
        "subcategory": "8(a) STARS III",
        "description": "Compliance matrix baseline for 8(a) STARS III task-order submissions.",
        "template_text": """| Requirement | Clause/Section | Owner | Status | Evidence |
| --- | --- | --- | --- | --- |
| 8(a) eligibility and socioeconomic attestation | Solicitation reps/certs | Contracts Lead | Not Started | SBA profile |
| Technical factor response mapping | Section M factors | Technical Lead | Not Started | Annotated outline |
| Past performance references | L.8 Experience | Past Performance Lead | Not Started | CPARS references |
| Pricing and discount narrative | Pricing volume instructions | Pricing Lead | Not Started | Pricing model |""",
        "placeholders": {},
        "keywords": ["compliance matrix", "8(a)", "stars iii", "task order", "socioeconomic"],
        "is_public": True,
    },
]


# =============================================================================
# Helpers
# =============================================================================


def _to_template_response(template: ProposalTemplate) -> TemplateResponse:
    return TemplateResponse(
        id=template.id,
        name=template.name,
        category=template.category,
        subcategory=template.subcategory,
        description=template.description,
        template_text=template.template_text,
        placeholders=template.placeholders,
        keywords=template.keywords,
        is_system=template.is_system,
        is_public=template.is_public,
        rating_sum=template.rating_sum,
        rating_count=template.rating_count,
        forked_from_id=template.forked_from_id,
        user_id=template.user_id,
        usage_count=template.usage_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


async def _ensure_system_templates(session: AsyncSession) -> None:
    created = 0
    updated = 0

    for template_data in SYSTEM_TEMPLATES:
        result = await session.execute(
            select(ProposalTemplate).where(
                ProposalTemplate.name == template_data["name"],
                ProposalTemplate.is_system == True,
            )
        )
        existing = result.scalars().first()
        desired_public = bool(template_data.get("is_public", False))
        if existing:
            if existing.is_public != desired_public:
                existing.is_public = desired_public
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                updated += 1
            continue

        template = ProposalTemplate(
            name=template_data["name"],
            category=template_data["category"],
            subcategory=template_data.get("subcategory"),
            description=template_data["description"],
            template_text=template_data["template_text"],
            placeholders=template_data["placeholders"],
            keywords=template_data["keywords"],
            is_system=True,
            is_public=desired_public,
        )
        session.add(template)
        created += 1

    if created or updated:
        await session.commit()
        logger.info("System templates synchronized", created=created, updated=updated)


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/", response_model=list[TemplateResponse])
async def list_templates(
    category: str | None = Query(None, description="Filter by category"),
    subcategory: str | None = Query(None, description="Filter by subcategory"),
    search: str | None = Query(None, description="Search in name and keywords"),
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TemplateResponse]:
    """
    List all available templates.
    Includes system templates and user's custom templates.
    """
    await _ensure_system_templates(session)

    query = select(ProposalTemplate).where(
        (ProposalTemplate.is_system == True) | (ProposalTemplate.user_id == current_user.id)
    )

    if category:
        query = query.where(ProposalTemplate.category == category)
    if subcategory:
        query = query.where(ProposalTemplate.subcategory == subcategory)

    result = await session.execute(query.order_by(ProposalTemplate.category, ProposalTemplate.name))
    templates = list(result.scalars().all())

    # Filter by search if provided
    if search:
        search_lower = search.lower()
        templates = [
            t
            for t in templates
            if search_lower in t.name.lower()
            or any(search_lower in kw.lower() for kw in t.keywords)
        ]

    return [_to_template_response(t) for t in templates]


@router.get("/categories")
async def list_categories(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """
    List all template categories.
    """
    await _ensure_system_templates(session)
    result = await session.execute(select(ProposalTemplate.category).distinct())
    categories = [row[0] for row in result.all()]
    return sorted(categories)


@router.get("/categories/list", include_in_schema=False)
async def list_categories_legacy(
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """
    Backward-compatible alias for older frontend clients.
    """
    await _ensure_system_templates(session)
    result = await session.execute(select(ProposalTemplate.category).distinct())
    categories = [row[0] for row in result.all()]
    return sorted(categories)


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TemplateResponse:
    """
    Get a specific template by ID.
    """
    await _ensure_system_templates(session)

    result = await session.execute(
        select(ProposalTemplate).where(ProposalTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check access
    if not template.is_system and template.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return _to_template_response(template)


@router.post("/", response_model=TemplateResponse)
async def create_template(
    request: TemplateCreate,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TemplateResponse:
    """
    Create a custom template.
    """
    template = ProposalTemplate(
        name=request.name,
        category=request.category,
        subcategory=request.subcategory,
        description=request.description,
        template_text=request.template_text,
        placeholders=request.placeholders,
        keywords=request.keywords,
        is_system=False,
        user_id=current_user.id,
    )

    session.add(template)
    await session.commit()
    await session.refresh(template)

    logger.info("Template created", template_id=template.id, user_id=current_user.id)

    return _to_template_response(template)


@router.post("/{template_id}/use")
async def use_template(
    template_id: int,
    placeholders: dict,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Use a template with provided placeholder values.
    Returns the filled-in template text.
    """
    await _ensure_system_templates(session)

    result = await session.execute(
        select(ProposalTemplate).where(ProposalTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if not template.is_system and template.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Fill in placeholders
    filled_text = template.template_text
    for key, value in placeholders.items():
        filled_text = filled_text.replace(f"{{{key}}}", str(value))

    # Update usage count
    template.usage_count += 1
    await session.commit()

    # Check for unfilled placeholders
    import re

    unfilled = re.findall(r"\{(\w+)\}", filled_text)

    return {
        "filled_text": filled_text,
        "unfilled_placeholders": unfilled,
    }


@router.post("/seed-system-templates")
async def seed_system_templates(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Seed the database with system templates.
    This endpoint should be called during initial setup.
    """
    before_result = await session.execute(
        select(sa_func.count()).where(ProposalTemplate.is_system == True)
    )
    before_count = before_result.scalar() or 0

    await _ensure_system_templates(session)

    after_result = await session.execute(
        select(sa_func.count()).where(ProposalTemplate.is_system == True)
    )
    after_count = after_result.scalar() or 0
    created = max(0, after_count - before_count)

    logger.info("Seeded system templates", created=created, total=after_count)

    return {
        "message": f"Created {created} system templates",
        "total_system_templates": after_count,
    }
