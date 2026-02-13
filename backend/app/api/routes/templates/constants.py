"""
System template definitions.
"""

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
\u2022 {accomplishment_1}
\u2022 {accomplishment_2}
\u2022 {accomplishment_3}

**Relevance to Current Requirement:**
This experience directly demonstrates our capability to {relevance_statement}. The technical complexity and scope align closely with the requirements outlined in Section {section_reference}.

**Performance Metrics:**
\u2022 On-time delivery rate: {delivery_rate}%
\u2022 Customer satisfaction: {satisfaction_rating}
\u2022 Quality metrics: {quality_metrics}

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
\u2022 Sprint Planning (4 hours)
\u2022 Daily Stand-ups (15 minutes)
\u2022 Sprint Review/Demo ({demo_duration})
\u2022 Sprint Retrospective (2 hours)

**Team Structure:**
Our cross-functional team includes:
\u2022 Product Owner (Government-designated)
\u2022 Scrum Master: {scrum_master_name}
\u2022 Development Team: {dev_team_size} engineers
\u2022 QA Engineers: {qa_team_size}
\u2022 DevOps/SRE: {devops_team_size}

**Definition of Done:**
All user stories must meet the following criteria before acceptance:
\u2022 Code complete and peer-reviewed
\u2022 Unit tests written with >{test_coverage}% coverage
\u2022 Integration tests passing
\u2022 Security scan completed (no Critical/High findings)
\u2022 Documentation updated
\u2022 Product Owner acceptance

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
\u2022 Documented quality policies and procedures
\u2022 Regular internal audits
\u2022 Continuous improvement processes
\u2022 Corrective and preventive action tracking

**Quality Control Measures:**

*Development Phase:*
\u2022 Code reviews for 100% of deliverables
\u2022 Automated static code analysis
\u2022 Security vulnerability scanning
\u2022 Performance testing against defined baselines

*Testing Phase:*
\u2022 Unit testing (minimum {unit_test_coverage}% coverage)
\u2022 Integration testing
\u2022 System testing
\u2022 User acceptance testing (UAT)
\u2022 Regression testing for all changes

**Defect Management:**
{defect_process_description}

Priority levels and response times:
\u2022 Critical: {critical_response}
\u2022 High: {high_response}
\u2022 Medium: {medium_response}
\u2022 Low: {low_response}

**Quality Metrics:**
We track and report the following metrics {reporting_frequency}:
\u2022 Defect density
\u2022 Test coverage
\u2022 On-time delivery rate
\u2022 Customer satisfaction scores

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
\u2022 {degree_1}, {school_1}, {year_1}
\u2022 {degree_2}, {school_2}, {year_2}

**Certifications:**
\u2022 {cert_1}
\u2022 {cert_2}
\u2022 {cert_3}

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
\u2022 Cage Code: {cage_code}
\u2022 Commercial and Government Entity (CAGE) Code: {cage_code}

**Personnel Clearances:**
{clearance_summary}

All proposed personnel either currently hold or are eligible to obtain the required {required_clearance} clearance. We commit to ensuring all personnel have appropriate clearances prior to accessing any classified information or systems.

**Cybersecurity Compliance:**
Our organization complies with the following frameworks and standards:
\u2022 NIST SP 800-171 (CUI protection)
\u2022 NIST Cybersecurity Framework
\u2022 {additional_framework_1}
\u2022 {additional_framework_2}

**CMMC Status:**
{cmmc_status}

**Incident Response:**
{incident_response_summary}

**Security Training:**
All employees complete annual security awareness training covering:
\u2022 Insider threat awareness
\u2022 Phishing and social engineering
\u2022 Proper handling of CUI/classified information
\u2022 Physical security protocols

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
