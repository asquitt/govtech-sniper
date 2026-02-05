# GovDash-Style Product Plan (Exact Products)

As of February 5, 2026. This is a build plan tailored to this repo (FastAPI + Next.js) and structured so you can implement in Codex.

## Objective
Build a GovDash-style platform with a single Opportunity record that powers Discover, Capture, Proposal, Contract, and Dash (AI agent), plus a shared Data Library and enterprise integrations.

## Product Suite (Exact Products)
1. Discover
2. Capture CRM
3. Proposal Cloud
4. Contract Cloud
5. Dash (AI Agent)
6. Data Library (Shared)
7. Integrations & Admin (Shared)

## Core Data Model (Single Opportunity Record)
Create a canonical `opportunity` entity and attach all workflow objects to it. This reduces data duplication and unlocks cross-module analytics.

### Tables (New or Expanded)
- opportunities
- opportunity_sources
- opportunity_requirements
- opportunity_scores
- capture_plans
- gate_reviews
- teaming_partners
- proposal_projects
- proposal_sections
- proposal_versions
- submission_packages
- contract_awards
- contract_tasks
- contract_deliverables
- cpars_reviews
- data_library_items
- data_library_tags
- integrations
- audit_events

### Relationships
- opportunity -> capture_plans, proposal_projects, contract_awards, opportunity_requirements
- proposal_projects -> proposal_sections, submission_packages, proposal_versions
- contract_awards -> contract_tasks, contract_deliverables, cpars_reviews
- data_library_items -> opportunities, proposal_sections, dash_sessions

## Architecture Plan (Repo-Specific)
Backend: expand FastAPI services and SQLModel models under `backend/app/models` and `backend/app/services`.
Frontend: add App Router pages under `frontend/src/app/(dashboard)` and components in `frontend/src/components`.

### New API Route Groups
- /api/v1/opportunities
- /api/v1/capture
- /api/v1/proposals
- /api/v1/contracts
- /api/v1/dash
- /api/v1/integrations

## Product Specs and Build Plan

### 1) Discover
Purpose: Normalize and surface opportunities across federal and SLED, with relevance scoring and qualification.

Scope:
- Source ingestion (SAM.gov, GSA eBuy, PIEE, SLED).
- Opportunity normalization into a single schema.
- Deduping, versioning, and snapshot diffs.
- Qualification scoring and recommended opportunities list.

Key Screens:
- Discover list view with filters (agency, NAICS, set-aside, deadline, score).
- Opportunity detail page with summary and source documents.
- Changes tab for snapshot diffs.

Backend Work:
- Extend existing `rfps` to `opportunities` or create a new `opportunities` table and map current RFPs to it.
- Reuse `sam_opportunity_snapshots` for versioning; add `opportunity_id`.
- Build scoring service in `backend/app/services/filters.py`.

Acceptance Criteria:
- New opportunities appear within ingestion window.
- Diffs available for opportunities with updated snapshots.
- Scoring explains why an opportunity is recommended.


### 2) Capture CRM
Purpose: Manage the bid pipeline, decisions, and teaming for each opportunity.

Scope:
- Capture pipeline stages and forecasting.
- Bid/no-bid decisions with rationale.
- Capability matrix and solution notes.
- Teaming partners management and notes.

Key Screens:
- Capture pipeline board/table with stage KPIs.
- Opportunity capture detail panel with bid decision and notes.
- Teaming partner directory and mapping to opportunities.

Backend Work:
- Create `capture_plans`, `gate_reviews`, `teaming_partners` models.
- Add activity feed events to `audit_events`.
- Add endpoints to create/update bid decisions and gate reviews.

Acceptance Criteria:
- Every opportunity can be moved across stages.
- Gate review history is preserved.
- Teaming partners can be linked to specific opportunities.


### 3) Proposal Cloud
Purpose: Turn compliance requirements and library assets into a compliant submission package.

Scope:
- Compliance matrix extraction.
- Annotated proposal outline generation.
- Section drafting with citations.
- Submission package tracking and final export.

Key Screens:
- Compliance matrix editor (left panel) and draft preview (right panel).
- Section editor with citations and evidence panel.
- Submission tracker with due dates and ownership.

Backend Work:
- Build `proposal_projects`, `proposal_sections`, `proposal_versions`, `submission_packages` models.
- Reuse `ComplianceMatrix` as `opportunity_requirements`.
- Extend `draft.py` with project and section endpoints.
- Export service to generate DOCX/PDF.

Acceptance Criteria:
- Matrix requirements map 1:1 to sections or cross-references.
- Every AI-generated claim is cited to a data library item.
- A submission package can be exported and re-opened.


### 4) Contract Cloud
Purpose: Track post-award execution and CPARS outcomes.

Scope:
- Award capture and contract summary.
- Deliverables and tasks with owners and due dates.
- Monthly status reports and CPARS preparation.

Key Screens:
- Contract overview dashboard with health and deliverables.
- Deliverables list and status report generator.
- CPARS prep view with evidence linking.

Backend Work:
- Create `contract_awards`, `contract_tasks`, `contract_deliverables`, `cpars_reviews` models.
- Add monthly reporting templates under `backend/app/services/export.py`.

Acceptance Criteria:
- Deliverables can be tracked with status and evidence.
- CPARS prep can pull evidence from proposal and contract artifacts.


### 5) Dash (AI Agent)
Purpose: Provide a single assistant for questions, summaries, and drafting across all modules.

Scope:
- Chat UI with memory and context from the Data Library and Opportunity record.
- Actions: summarize solicitation, draft capability statement, explain compliance gaps.
- Tool calling to fetch data from internal APIs.

Key Screens:
- Dash chat interface with references.
- Suggested actions panel by opportunity stage.

Backend Work:
- Create `dash_sessions` and `dash_messages` models.
- Add `dash` service that composes system prompts with context slices.
- Implement tool handlers for data fetch, draft, and citation retrieval.

Acceptance Criteria:
- Dash can answer questions grounded in internal data with citations.
- Dash can generate a capability statement tied to a selected opportunity.


### 6) Data Library (Shared)
Purpose: Central repository for reusable content and evidence.

Scope:
- Document upload, tagging, and versioning.
- Section-level extraction and retrieval.
- Link evidence to proposal sections and contract deliverables.

Key Screens:
- Library list with filters and tags.
- Document detail with extracted sections and citations.

Backend Work:
- Extend `knowledge_base.py` to include tags and versioning.
- Add document processing pipeline and chunk index.

Acceptance Criteria:
- Library items can be linked to proposals and contracts.
- Document updates retain versions and audit history.


### 7) Integrations & Admin (Shared)
Purpose: Enterprise onboarding and workflow integration.

Scope:
- Okta SSO, SharePoint sync, Salesforce sync, webhooks.
- Admin settings: orgs, teams, roles, audit logs.

Key Screens:
- Integration settings page with OAuth flows.
- Admin panel for roles, teams, and permissions.

Backend Work:
- Implement OAuth integrations and sync jobs.
- Add `organizations`, `teams`, `roles`, `permissions`, `audit_events` models.

Acceptance Criteria:
- Admins can manage roles and see audit logs.
- Integrations can sync and are observable.


## Build Roadmap (12 Months)

### Phase 0 (Weeks 1-3): Foundation
- Introduce `organizations` and `opportunities` core schema.
- Migrate current RFPs into opportunities.
- Implement audit events.

### Phase 1 (Weeks 4-10): Discover + Capture MVP
- Ingestion + normalization.
- Capture pipeline, bid/no-bid, gate reviews.
- Opportunity list and detail UI.

### Phase 2 (Weeks 11-20): Proposal Cloud MVP
- Compliance matrix extraction and editor.
- Section drafting with citation enforcement.
- Submission package export.

### Phase 3 (Weeks 21-30): Contract Cloud MVP
- Post-award tracking and deliverables.
- Monthly status reporting.
- CPARS prep.

### Phase 4 (Weeks 31-44): Dash AI Agent
- Chat interface and tool calling.
- Context retrieval from Data Library and Opportunity record.

### Phase 5 (Weeks 45-52): Integrations + SLED
- Okta, SharePoint, Salesforce, webhooks.
- SLED ingestion and normalization.

## Metrics and QA
- Time-to-first-compliance-matrix.
- Proposal draft throughput per user per week.
- Win rate and stage conversion.
- Contract deliverable on-time percentage.

## Notes on Existing Repo Fit
- The existing RFP ingestion, compliance matrix, and draft generation map directly to Discover and Proposal Cloud.
- Expand the current `rfps` model into a unified `opportunities` model to become the platform spine.
- Reuse `documents` endpoints as the base of Data Library.

