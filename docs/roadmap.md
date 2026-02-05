# Product Roadmap (Full Plan)

This roadmap is the end-to-end plan from foundation through full GovDash-equivalent platform. It is structured so we can execute sequentially without blocking questions.

## Phase 0 - Foundation (Complete)
- Audit logging for security and compliance.
- Webhook subscriptions + delivery logs.
- Integrations registry scaffolding.
- Dash (AI) session/message + minimal ask endpoint.
- Knowledge Base list response fixes + stats endpoint.
- Security: ownership checks on document endpoints.
- Tests for audit, webhooks, integrations, dash.

## Phase 1 - Discover + Capture MVP
### Discover
- Opportunity list + filtering by status, qualified, date.
- Scoring improvements (deadline urgency, qualification score).
- Snapshot diff surfaced in UI.

### Capture
- Capture plans, gate reviews, teaming partners + linking.
- Capture UI with plan creation + stage/decision updates.
- Audit + webhook events for capture actions.
- Tests covering full capture lifecycle.

## Phase 2 - Proposal Cloud MVP
- Compliance matrix editor improvements.
- Section drafting with citations (RAG + KB).
- Submission package tracking and export.
- UI: proposal workspace, section editor, citation panel.
- Tests: proposal CRUD, section generation, export.

## Phase 3 - Contract Cloud MVP
- Contract award model and tracking.
- Deliverables and status reports.
- CPARS preparation workflows.
- Tests: contract CRUD, deliverable workflows.

## Phase 4 - Dash AI Agent
- Tool-calling actions (summaries, compliance gaps, draft sections).
- Multi-step workflows with context retrieval.
- Chat UI enhancements and prompts.
- Tests: deterministic mock responses, tool invocation coverage.

## Phase 5 - Integrations + Enterprise
- Okta + Microsoft SSO flows.
- SharePoint, Salesforce sync + webhooks.
- Admin settings, roles, and permissions.
- Observability dashboards and advanced audit views.

## Phase 6 - Production Hardening
- Real SSO flows, SCIM provisioning, MFA.
- Encryption and secrets management.
- Migrations, background jobs, caching.
- SLO dashboards and alerting.
- E2E and load testing.

## Phase 7 - GovDash + Govly Parity Expansion
- Saved searches and alerting for opportunities.
- Market intelligence fields (vehicles, incumbents, contacts, budgets).
- Pipeline customization and Kanban capture views.
- Word add-in workflows and graphics request pipeline.
- Competitive intel summaries and contract intelligence.

## Phase 8 - Proposal Governance (GovDash Parity)
- Compliance shreds + document classification for RFP content.
- Proposal outline editor with volumes, page limits, and reviewer assignments.
- Review mode and redline workflows.
- Compliance package export bundle.
- Labor category + key personnel mapping with adjudication.

## Phase 9 - Govly Intelligence + Automation
- Budget document ingestion + tagging.
- Award summaries + competitor win tracking.
- AI predictions and industry analysis reports.
- Collaboration workspace: tasks, comments, and team workflows.
- Email ingestion pipeline + procurement portal automation hooks.
- CRM sync (Salesforce/Unanet) scaffolding.
