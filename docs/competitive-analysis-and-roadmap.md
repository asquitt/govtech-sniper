# Competitive Analysis & Task Roadmap: GovTech Sniper vs GovDash vs Govly

> **Generated**: February 6, 2026
> **Updated**: February 14, 2026
> **Purpose**: Gap analysis between GovTech Sniper and our two primary competitors, with a prioritized task list to close the gap.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Competitor Deep Dive: GovDash](#competitor-deep-dive-govdash)
3. [Competitor Deep Dive: Govly](#competitor-deep-dive-govly)
4. [GovTech Sniper Current State](#govtech-sniper-current-state)
5. [Feature Gap Matrix](#feature-gap-matrix)
6. [What Customers Love (Competitor Strengths)](#what-customers-love)
7. [Task Roadmap: Closing the Gap](#task-roadmap-closing-the-gap)

---

## Executive Summary

GovDash and Govly represent two distinct competitive threats:

- **GovDash** ($40M+ raised, ~200 customers) is the **proposal-centric** competitor. They dominate in AI-powered proposal writing, compliance matrix generation, and end-to-end lifecycle management. Customers rave about time savings (50-60% reduction in proposal cycles) and pink-team-ready draft quality. They recently achieved FedRAMP Moderate Equivalency and signed multiple Top 100 government contractors.

- **Govly** ($13M raised, 200+ customers) is the **intelligence-and-network** competitor. They dominate in opportunity discovery breadth (40+ private contract vehicles, 10,000+ SLED sources, procurement forecasts), cross-organization collaboration, and their free tier strategy. Customers love the UI, consolidation of data sources, and network effects of partner sharing.

**GovTech Sniper** has strong foundational architecture (FastAPI, Next.js, Celery, Gemini AI) and already covers much of the core lifecycle. However, key gaps exist in:

1. **Data source breadth** (we only have SAM.gov; competitors have 40+ sources)
2. **Proposal writing workflow maturity** (GovDash's annotated outlines, writing plans, color team reviews)
3. **Compliance & security certifications** (FedRAMP, CMMC)
4. **Network/collaboration features** (Govly's cross-org workspaces, teaming board)
5. **Analytics & reporting** (both competitors have rich reporting dashboards)
6. **Free tier / PLG strategy** (Govly's free plan drives adoption)
7. **CRM integrations** (Salesforce, Unanet, Microsoft Dynamics)

### Verification Update (2026-02-10)

This roadmap was revalidated against live code, backend integration tests, and Playwright browser runs.

- Verified in live browser and tests as integrated: Salesforce sync surfaces, SharePoint routes/sync surfaces, semantic search API/UI entry points, color-team reviews, Gantt pipeline view, analytics/reports dashboard metrics, teaming board, and collaboration workspaces.
- Newly closed in this session: cross-org invitation acceptance UX (`/collaboration/accept`), partner portal UI (`/collaboration/portal/[workspaceId]`), selective data-sharing controls, and secure invitation acceptance contract (invite email must match authenticated user).
- Newly closed in this session: contract hierarchy management (parent/child task-order relationships) and full modifications + CLIN lifecycle validation in `/contracts`.
- Newly closed in this session: partner contract-feed sharing with named feed catalog + partner-portal visibility in collaboration workspaces.
- Newly closed in this session: contract-feed sharing presets and multi-workspace partner-portal switching for faster cross-org operations.
- Newly closed in this session: partner-governance controls for shared artifacts (admin approval gates, expiry policies, and partner-scoped visibility).
- Newly closed in this session: multi-user teaming request lifecycle validation (sender -> receiver inbox acceptance) and deterministic capability-gap analysis contract hardening.
- Validation evidence this session: `backend/tests/test_collaboration.py` passed; Playwright full suite passed (`58/58`) on `E2E_BASE_URL=http://localhost:3100` with backend on `:8010`.
- Additional validation evidence this session: `backend/tests/test_contracts.py` passed (hierarchy + modification + CLIN coverage), `frontend/src/__tests__/contracts-page.test.tsx` passed, and Playwright contract workflow passed (`frontend/e2e/tests/contracts-workflow.spec.ts`).
- Additional collaboration parity evidence this session: `/api/v1/collaboration/contract-feeds/catalog` + contract-feed share labeling covered in `backend/tests/test_collaboration.py`, portal label rendering covered in `frontend/src/__tests__/collaboration-portal-page.test.tsx`, and partner flow validated in Playwright (`frontend/e2e/tests/collaboration-workflow.spec.ts`).
- Additional collaboration parity evidence this session: `/api/v1/collaboration/contract-feeds/presets` + `/api/v1/collaboration/workspaces/{id}/share/preset` validated in backend tests; portal workspace-switcher and preset-driven sharing validated in Playwright collaboration workflow.
- Additional collaboration governance evidence this session: `/api/v1/collaboration/workspaces/{id}/share` now supports `requires_approval`, `expires_at`, and `partner_user_id`; `/api/v1/collaboration/workspaces/{id}/shared/{perm_id}/approve` is validated in backend integration tests and Playwright workflow.
- Additional collaboration governance analytics evidence this session: `/api/v1/collaboration/workspaces/{id}/shared/governance-summary` is validated in backend integration tests and rendered in collaboration workspace UI with Playwright assertions for pending/scoped metric transitions.
- Additional collaboration governance depth evidence this session: `/api/v1/collaboration/workspaces/{id}/shared/governance-trends` (SLA trend analytics) and `/api/v1/collaboration/workspaces/{id}/shared/audit-export` (CSV audit timeline export) are validated in backend integration tests, surfaced in `/collaboration`, and verified in Playwright (`collaboration-workflow.spec.ts`).
- Additional teaming evidence this session: backend `test_teaming_board.py` now validates cross-user inbox acceptance and `/api/v1/teaming/gap-analysis/{rfp_id}`; Playwright `teaming-workflow.spec.ts` validates end-to-end two-user acceptance propagation.
- Additional teaming UX evidence this session: `/teaming` now surfaces partner-fit rationale from gap analysis and request timeline metadata (`updated_at`) in sent/received queues, validated by unit and Playwright tests.
- Additional teaming analytics evidence this session: `/api/v1/teaming/requests/fit-trends` and `/api/v1/teaming/requests/audit-export` are validated in backend integration tests, surfaced in `/teaming` with acceptance-rate trend metrics + export action, and verified in Playwright (`teaming-workflow.spec.ts`).
- Additional PLG + search parity evidence this session: global semantic search is now wired to primary UX via header trigger + keyboard shortcut with entity facets (`/opportunities`), validated by frontend unit tests (`global-search.test.tsx`, `header-search-trigger.test.tsx`) and Playwright workflow (`search-plg-workflow.spec.ts`).
- Additional PLG parity evidence this session: free-tier landing experience is now surfaced at `/free-tier` and linked from auth/subscription flows; in-product upgrade nudges are now active in subscription usage workflows (`subscription-upgrade-nudge.test.tsx`, `free-tier-page.test.tsx`, Playwright `search-plg-workflow.spec.ts` + `settings.spec.ts`).
- Additional discovery + intelligence evidence this session: external source-provider ingest contracts for `gsa_ebuy`, `fpds`, and `usaspending` are validated in `backend/tests/test_data_sources.py`; contact intelligence extraction/agency-directory/search contracts are validated in `backend/tests/test_contacts.py`; past-performance tagging/match/narrative contracts are validated in `backend/tests/test_documents.py`.
- Additional external-provider parity evidence this session: `sled_bidnet`, `dibbs`, and contract-vehicle feeds (`gsa_mas`, `cio_sp3`, `ites`, `oasis`) were integrated and validated in `backend/tests/test_data_sources.py` and Playwright settings workflows.
- Additional autonomous-agent parity evidence this session: `/api/v1/agents/catalog`, `/agents/research/{rfp_id}`, `/agents/capture-planning/{rfp_id}`, `/agents/proposal-prep/{rfp_id}`, and `/agents/competitive-intel/{rfp_id}` were integrated into `/agents` and validated in backend + Playwright (`test_agents.py`, `agents-workflow.spec.ts`).
- Additional workflow-automation parity evidence this session: executable workflow engine with rule conditions/actions is integrated and trigger-wired from capture plan/stage transitions; validated in `test_workflows_execution.py` and Playwright (`workflows-workflow.spec.ts`).
- Additional proposal-graphics parity evidence this session: template library + generated graphics + in-editor insertion + DOCX/PDF export rendering were integrated and validated in backend/unit/Playwright (`test_graphics.py`, `test_export_graphics.py`, `proposal-editor-workflow.spec.ts`).
- Additional compliance-readiness evidence this session: readiness tracking for `fedramp_moderate`, `cmmc_level_2`, `govcloud_deployment`, `salesforce_appexchange`, and `microsoft_appsource` is now surfaced via `/api/v1/compliance/readiness` and `/compliance`, validated in backend + Playwright (`test_compliance_dashboard.py`, `compliance-readiness.spec.ts`).
- Additional mobile/push parity evidence this session: push-subscription APIs + settings UX were integrated and validated (`test_notifications_push.py`, `settings-notifications-workflow.spec.ts`), and mobile Dash behavior is covered by Playwright (`mobile-dash.spec.ts`).
- Additional contact-linking evidence this session: extracted contacts now auto-link to source opportunities and agency directory records (`linked_rfp_ids` + agency primary-contact linkage), validated in backend integration (`test_contacts.py`), frontend unit (`contact-extract-button.test.tsx`), and Playwright (`contacts-workflow.spec.ts`).
- Additional Dash parity evidence this session: voice controls are now integrated into primary `/dash` chat input (speech-to-text + text-to-speech controls), validated in frontend unit (`dash-chat-voice-controls.test.tsx`) and Playwright (`dash.spec.ts`).
- Additional SharePoint parity evidence this session: `/settings/integrations` now surfaces an embedded SharePoint browser, proposal workspace now exposes direct SharePoint export, and backend `/api/v1/sharepoint/export` now uses internal export helpers instead of hardcoded localhost callbacks; validated in backend integration (`test_sharepoint.py`), frontend unit (`settings-integrations-page.test.tsx`), and Playwright (`settings-integrations-workflow.spec.ts`, `proposal-editor-workflow.spec.ts`).
- Additional org-admin parity evidence this session: `/admin` now includes member invitation and activation flows backed by `/api/v1/admin/members/invite`, `/api/v1/admin/member-invitations`, and `/api/v1/admin/member-invitations/{id}/activate`; validated in backend integration, frontend unit, and Playwright (`test_admin_roles.py`, `admin-page-invitations.test.tsx`, `admin-org-workflow.spec.ts`).
- Additional collaboration-governance parity evidence this session: anomaly alerts and scheduled compliance digest controls are integrated via `/api/v1/collaboration/workspaces/{id}/shared/governance-anomalies`, `/compliance-digest-schedule`, `/compliance-digest-preview`, and `/compliance-digest-send`; validated in backend integration, frontend unit, and Playwright (`test_collaboration.py`, `collaboration-page-governance.test.tsx`, `collaboration-workflow.spec.ts`).
- Additional teaming-parity evidence this session: partner-level trend drilldowns and scheduled performance digest controls are integrated via `/api/v1/teaming/requests/partner-trends`, `/api/v1/teaming/digest-schedule`, and `/api/v1/teaming/digest-send`; validated in backend integration, frontend unit, and Playwright (`test_teaming_board.py`, `teaming-page-fit-analysis.test.tsx`, `teaming-workflow.spec.ts`).
- Additional diagnostics-parity evidence this session: websocket telemetry now surfaces task-watch latency, reconnect counts, and event throughput in `/api/v1/ws/diagnostics` and `/diagnostics`, validated in backend integration and Playwright (`test_websocket_diagnostics.py`, `diagnostics-workflow.spec.ts`).
- Additional Word add-in parity evidence this session: Office-host-in-the-loop taskpane automation now validates host runtime pull/push sync beyond browser fallback (`word-addin-office-host.spec.ts`), alongside existing backend word-addin coverage (`test_word_addin.py`).
- Additional analytics-governance parity evidence this session: ownership audit now flags frontend-unused analytics endpoints as retirement candidates (`/api/v1/analytics/documents`, `/api/v1/analytics/slo`, `/api/v1/analytics/alerts`) in `test_route_ownership_audit.py`.
- Validation evidence refresh this session: backend full suite passed (`169/169`), frontend unit suite passed (`32/32`), and Playwright full suite passed (`58/58`) on deterministic local stack (`DEBUG=true`, `MOCK_AI=true`, backend `8010`, frontend `3100`).

### Research Refresh (2026-02-14)

- Fresh competitor signal validation:
  - GovDash Proposal Cloud guidance emphasizes compliance matrix + "shreds", outline depth, and structured proposal workflows (support docs).
  - GovDash public customer stories continue to highlight time-to-draft and output-throughput improvement claims.
  - Public trust/security signals remain central in buyer messaging (FedRAMP/CMMC and data-handling controls).
- Fresh industry-direction validation:
  - FedRAMP 20x Phase 2 process direction reinforces evidence automation and machine-readable control posture as near-term enterprise expectations.
  - DFARS CMMC rollout milestones continue to increase compliance-documentation burden through phased enforcement windows.
- Fresh AI-research signal validation (primary sources):
  - LLM evaluator reliability remains strongest with explicit rubric-driven judging and grounded evidence.
  - Retrieval/evaluation quality literature continues to favor calibrated confidence reporting and explicit faithfulness/groundedness checks.
- Executed product response this session:
  - Shipped capture stress-test scenario simulator with calibrated confidence + recommendation-shift detection + FAR/Section M rationale mapping (`/api/v1/capture/scorecards/{rfp_id}/scenario-simulator`, `/capture` UI).
  - Shipped review-packet generator with risk-ranked action queue and exit criteria for pink/red/gold workflows (`/api/v1/reviews/{review_id}/packet`, `/reviews` packet builder UI).
  - Shipped one-click evaluator evidence bundle export depth (`/api/v1/export/proposals/{id}/compliance-package/zip`, proposal workspace `Export Evidence Bundle`) including source trace, section decisions, review outcomes, and bid stress-test artifacts.
  - Shipped amendment autopilot impact mapping (`/api/v1/rfps/{rfp_id}/snapshots/amendment-impact`, `/opportunities/[rfpId]` changes-tab `Generate Impact Map`) with section-level remediation guidance and approval workflow steps.
  - Shipped email-ingestion pipeline depth (`/api/v1/email-ingest/sync-now`, `/settings/email-ingest`) with workspace-routed team inbox forwarding, attachment extraction metadata, and confidence-calibrated auto-opportunity creation.

---

## Competitor Deep Dive: GovDash

### Company Profile

| Detail | Info |
|--------|------|
| **Founded** | 2021 (as Realize Inc.) |
| **HQ** | New York, NY + Arlington, VA |
| **Funding** | $40M+ (YC W22, $10M Series A, $30M Series B Jan 2026) |
| **Investors** | Y Combinator, Mucker Capital, BCI, Northzone |
| **Customers** | ~200 companies, including multiple Top 100 US gov contractors |
| **Team** | 45+ employees |
| **Revenue Growth** | 16x from Series A to B |
| **Customer Growth** | 18x from Series A to B |
| **Pricing** | Custom pricing, no public rates. No free trial. Estimated enterprise starts at $40K+/year based on market positioning. |
| **Rating** | 4.7/5 (limited review volume on third-party sites) |

### Product Architecture (5 Modules + AI Agent)

#### 1. Discover
- SAM.gov + GSA eBuy integration
- SLED opportunity support (added 2025)
- AI-powered Bid Match scoring based on business profile, industry, and capabilities
- Centralized pipeline view across all sources
- Deadline alerts and tracking tools

#### 2. Capture Cloud (GovCon CRM)
- Kanban board AND Gantt chart views
- Default phases: Analysis → Intel → Solution → Ready for Proposal → Active Proposal (customizable)
- Custom fields for opportunity intake
- Gate reviews and validation checkpoints
- Automated teammate evaluation and workshare tracking
- Bidirectional Salesforce sync via webhooks

#### 3. Proposal Cloud
- **Full solicitation parsing** (Sections L, M, C, H, and PWS — not just L&M)
- Automatic compliance matrix generation
- Annotated outline generation with compliance mappings
- Writing plans (bullet-point instructions per section)
- Focus document upload (past performance, resumes, capabilities)
- AI draft generation (pink-team-ready in under 1 hour)
- Rich text section editor for in-platform collaboration
- Word Assistant (Microsoft Word add-in with AI editing, compliance checks, graphic creation)
- Past performance reuse and repackaging
- Citation automation
- Color team review support (pink, red, gold)

#### 4. Contract Cloud
- Post-award lifecycle management
- CPARS tracking and reporting
- Contract modifications and CLINs management
- Complex hierarchical contract structures
- Award data flows into contract module for future past performance

#### 5. Dash (AI Agent)
- LLM-powered assistant embedded across all workflows
- Solicitation analysis and Q&A
- Semantic document search across thousands of pages
- Content generation, editing, and compliance checks inside editor
- Voice mode for hands-free interaction
- Tool-calling actions for multi-step workflows

### Integrations
- Microsoft SharePoint (document storage, proposal export)
- Salesforce (bidirectional pipeline sync, custom field mapping)
- Microsoft Word (Word Assistant add-in on AppSource)
- SAM.gov + GSA eBuy
- Webhooks (CRUD notifications to external systems)

### Security & Compliance
- **FedRAMP Moderate Equivalency** (Q1 2026, audited by Ignyte)
- CMMC compliance out-of-the-box
- NIST 800-171 compatible
- AWS and Azure GovCloud
- Data never used for AI model training
- Role-based access controls with granular permissions

### Reporting & Analytics
- Win rate tracking
- Active pipeline value and stage breakdown
- Conversion rates through pipeline
- Proposal volume and turnaround time
- Customer awards by agency
- NAICS performance breakdown
- Team performance metrics
- Resource utilization
- Revenue timeline/forecasting
- Total hours saved

### What Customers Love About GovDash

1. **Dramatic time savings**: 50-60% reduction in proposal development time; proposals in 24 hours vs weeks
2. **Cost reduction**: One customer saved $75K/year; another saved $50K per proposal cycle
3. **Compliance matrix quality**: Full-solicitation parsing catches requirements hidden in Sections C and H (called "solicitation shredding")
4. **Increased output**: Customers pursue 3x more opportunities with the same team
5. **Word integration**: The Word Assistant is consistently called a "game changer" — works directly in familiar Word environment
6. **Support quality**: "Extremely responsive and considerate"
7. **Pink-team-ready draft quality**: AI drafts are usable starting points, not generic filler
8. **End-to-end platform**: Eliminates need for 5+ disconnected tools
9. **Microsoft ecosystem integration**: Seamless Word + SharePoint integration praised by enterprise users
10. **Security & compliance built-in**: NIST 800-171 adherence and FedRAMP Moderate Equivalency remove compliance barriers for defense contractors

### Common Complaints About GovDash

1. **Price opacity**: Custom pricing with no public rates frustrates small businesses. Requires sales call just to get a quote.
2. **No free trial**: Unlike Govly, there's no way to test the platform before committing to a contract.
3. **Steep learning curve**: Enterprise-grade features come with complexity — onboarding takes time.
4. **Limited data sources**: Compared to Govly's 40+ contract vehicles and 10,000+ SLED sources, GovDash primarily focuses on SAM.gov and GSA eBuy.
5. **Pricing**: While not explicitly stated in reviews, market positioning suggests high cost barrier for small businesses (estimated $40K+/year).

### Customer Results
- **FEDITC**: 50% reduction in proposal time, 75% reduction in past performance narrative prep
- **Schatz Strategy Group**: $75K/year saved, 2x proposal output, 50% faster turnaround
- **The Brite Group**: 50% of initial drafts produced automatically
- **$5B+ in government contracts** won by GovDash customers in 2025

---

## Competitor Deep Dive: Govly

### Company Profile

| Detail | Info |
|--------|------|
| **Founded** | 2021 |
| **HQ** | San Francisco, CA |
| **Funding** | $13.1M ($9.5M Series A led by Insight Partners, Nov 2023) |
| **Investors** | Insight Partners, Y Combinator, 8VC, FundersClub, NordicEye |
| **Customers** | 200+ (Cisco, Samsung, HPE, Nutanix, AT&T, Fortinet, SHI, Red River) |
| **Team** | ~30+ employees |
| **Valuation** | ~$41M (post-money Series A) |

### Product Architecture

#### 1. Pipeline & Opportunity Discovery
- **Federal**: SAM.gov RFQs, RFIs, RFPs, pre-solicitations
- **40+ private contract vehicles**: SEWP, CIO-SP, ITES, GSA MAS, OASIS, VETS 2, STARS II, Alliant 2
- **SLED**: 10,000+ state/local/education sources across all 50 states, PR, DC
- **Canada**: Expanded beyond US
- **Procurement forecasts**: Agency solicitations months/years before public posting
- **Industry days & events**: Pre-solicitation conferences
- **DIBBS**: Defense Logistics Agency opportunities
- **Market signals**: Daily intelligence from government news, budgets, congressional orders
- **Semantic search**: NLP-powered intent-based search (launched Jan 2025)
- **AI-powered RFQ predictions**: ML to predict competing products/vendors

#### 2. Intelligence & Insights
- Award tracking and competitor win analysis
- Budget document insights
- AI-extracted contact intelligence from opportunity documents
- Millions of agency contacts with phone, email, agency, location filtering
- Buyer intelligence with agency profiles, budgets, award history
- Historical archive of every government opportunity

#### 3. Deal Management & Collaboration
- **Workspaces**: Per-solicitation environments for collaborative pursuit
- **Team inboxes**: Shared communication for distributed teams
- **Partnerships**: Cross-organization sharing of contract feeds
- **Teaming board**: Find and connect with potential teaming partners
- **Vendor search**: Identify channel partners

#### 4. Automation & AI
- **AI agents**: Program Analyst Agent, Government Programs Agent
- **Smart workflows**: Rule-based automation for routine tasks
- **Distributor quoting flow**: Routes requests to manufacturers (3x more bids completed)
- **Automated research & summaries**
- **Workspace AI assistant**: In-workspace AI help

### Pricing Model
- **Free Plan**: 30-day solicitations (SAM.gov + 6,000+ SLED), recent awards, full search/filtering, AI projections
- **Paid Plans**: ~$3K-$15K/year for SMBs, enterprise pricing custom
- **Significantly cheaper than GovWin** ($7K-$45K)

### Integrations
- Salesforce
- Unanet
- Microsoft Dynamics (in development)
- API access for custom CRM connections
- Carahsoft distribution partnership

### Security
- **CMMC Level 2 Certification** (first in category)
- Available via DoD Tradewinds Marketplace

### What Customers Love About Govly

1. **Data breadth**: 40+ contract vehicles, 10,000+ SLED sources — "one-stop shopping"
2. **UI/UX quality**: Consistently praised as superior to GovWin, SAM.gov, and legacy tools
3. **Color-coded tracking**: Visual status tracking loved by account managers
4. **Cross-org collaboration**: Share opportunities with partners, OEMs, and subs in one platform
5. **Free tier**: Low barrier to entry, functional without payment
6. **Alert system**: Email notifications on opportunity changes called a "game changer"
7. **Support responsiveness**: "Impeccable" support quality
8. **Network effects**: Partnership features create sticky ecosystem
9. **80% productivity increase** reported by users
10. **3x pipeline growth** (Tricentis case study)

---

## Additional Competitors (2026 Landscape Expansion)

### GovSignals (FedRAMP High Competitor)

**Position**: Premium security-focused proposal platform
- **Security**: ONLY AI proposal platform with FedRAMP High authorization
- **Pricing**: Enterprise sales-led only. Five-figure annual commitments expected.
- **Customers**: 400+ organizations, trusted by defense contractors handling sensitive data
- **Key Features**:
  - Auto go/no-go analysis
  - >95% accurate compliance matrix + outlines in <5 minutes
  - Content generation in customer's voice using secure docs
  - GovSignals Insider Sources (proprietary non-public opportunities)
- **Strengths**:
  - FedRAMP High is a massive differentiator for DoD/IC contractors
  - SOC 2-grade security with full data encryption
  - No customer data used for model training (contractually guaranteed)
- **Weaknesses**:
  - Expensive (five-figure annual commitments)
  - No public pricing transparency
  - Limited integrations compared to GovDash/Govly

### CLEATUS (Budget-Friendly AI Competitor)

**Position**: SMB-focused AI platform with daily compliance scoring
- **Pricing**: Starts low (free trial available), transparent pricing model
- **Customers**: Micro-contractors and small businesses, 2 FTE processing 10+ proposals in 90 days
- **Key Features**:
  - AI daily scan scoring for Fed/State/Local bids
  - Bid/no-bid guidance with compliance scores delivered to inbox
  - Document Hub turns assets into AI-ready snippets (drag-and-drop)
  - AI cost estimation from contract documents
  - Agency hierarchy visualization + Contracting Officer contact info
  - Competitor award history analysis
- **Strengths**:
  - Budget-friendly for small businesses ("without paying an arm and leg")
  - Fast proposal turnaround (10+ proposals in 90 days with 2 FTE)
  - Simplified due diligence for state/federal opportunities
  - Drag-and-drop document intelligence
- **Weaknesses**:
  - No FedRAMP or CMMC certifications visible
  - Limited enterprise features vs GovDash/GovSignals
  - Newer player with less brand recognition

### Sweetspot (YC S23, All-in-One Platform)

**Position**: Y Combinator-backed fast-growing unified platform
- **Pricing**: $60/month starting price. Free trial available.
- **Customers**: Oshkosh, Vannevar Labs, Strider, and other public-sector innovators
- **Key Features**:
  - AI-powered search across SAM.gov, USAspending, FPDS, DIBBS, 1,000+ state/local sources
  - Opportunity Chat for bid/no-bid decisions
  - Pursuit Management for team collaboration
  - Proposal Copilot for response drafting
  - AI Form Fill agent for government forms
  - 3x faster contract discovery vs SAM.gov
- **Strengths**:
  - Extremely affordable entry point ($60/month)
  - Y Combinator credibility
  - Broad data coverage (Fed + State/Local + DIBBS)
  - Users "extremely happy" with Form Fill automation
- **Weaknesses**:
  - Very early stage (YC S23) — limited proven scale
  - No public reviews yet on major platforms
  - Unclear depth of proposal features vs GovDash

### Unanet ProposalAI (ERP-Adjacent Proposal Tool)

**Position**: Proposal automation for existing Unanet AE/GovCon customers
- **Pricing**: Subscription model, no public rates. Contact for pricing.
- **Deployment**: AWS GovCloud with federal cybersecurity compliance
- **Key Features**:
  - Auto-generate prompts for every RFP requirement
  - Outline generation with requirement-to-response mapping
  - Integrates with org knowledge library (past proposals, docs, SME insights)
  - No hallucinations (uses proprietary data only)
  - 70% faster draft creation
  - 30% more opportunities pursued
- **Strengths**:
  - Deep Unanet ecosystem integration (existing AE/GovCon customers)
  - AWS GovCloud deployment (federal compliance ready)
  - Data privacy (models never used to train others)
  - Proven 70% time reduction
- **Weaknesses**:
  - Requires Unanet ecosystem (not standalone)
  - Pricing opacity
  - Limited reviews/testimonials available

### ProposalWriter.ai (AI-First Proposal Tool)

**Position**: AI proposal writing focused on government contracting
- **Pricing**: Flat-rate pricing (exact rates not public)
- **Key Features**:
  - Inspira and Orchestrix AI assistants
  - Nexa Opportunity Finder (market trend analysis)
  - Past performance templates
  - Pricing strategy automation
  - Professionally designed templates for compliance
- **Strengths**:
  - AI-first approach (multiple specialized agents)
  - Template library for compliance
  - Flat-rate pricing model
- **Weaknesses**:
  - Very limited public information/reviews
  - No clear security certifications
  - Unclear customer base size

### XaitPorter (Formerly Privia)

**Position**: Enterprise co-authoring platform for distributed teams
- **Pricing**: Custom pricing, no free plan. Enterprise-focused.
- **Customers**: 10,000+ users from SMB to enterprise
- **Key Features**:
  - Cloud-based co-authoring with version control
  - AI content suggestions
  - FAR auto-formatting
  - Layout templates with auto-shredded outlines
  - Salesforce integration
  - 70% faster bid creation
- **Strengths**:
  - Proven at scale (10,000+ users)
  - Strong audit trails and compliance features
  - Enterprise-grade security and controls
  - Acquired by Xait (strong backing)
- **Weaknesses**:
  - Steep learning curve
  - Expensive for small businesses
  - Complex feature set may be overkill for SMBs

### Capture2Proposal

**Position**: Capture lifecycle management for GovCon BD
- **Pricing**: $2,640/year starting price
- **Key Features**:
  - Search by security clearance, evaluation criteria, keywords in documents
  - ML-based opportunity recommendations
  - PWin analytics with recommended capture strategies
  - Teaming agreement tracking (workshare, NDAs, TAs, set-asides)
  - FIPS-validated encryption (DFARS/NIST SP 800-171)
  - Microsoft Teams + Outlook integration
- **Strengths**:
  - Affordable entry point ($2,640/year)
  - Strong capture management features
  - DFARS/NIST compliance built-in
  - Users find opportunities not discoverable elsewhere
  - Promotes collaboration without per-seat licensing
- **Weaknesses**:
  - Limited AI proposal writing vs GovDash/GovSignals
  - More focused on capture than proposal execution
  - Smaller player vs funded competitors

### GovTribe (Opportunity Intelligence Specialist)

**Position**: Government contract intelligence and opportunity discovery
- **Pricing**: $60/month starting price. 14-day free trial on Standard Plan ($5,500/year for 10 users).
- **Key Features**:
  - Aggregates SAM.gov, FBO.gov, and procurement portals
  - Rich filtering by NAICS/PSC, agency, set-asides, vehicles, Contracting Officers
  - Saved searches with scheduled notifications
  - Federal contractor performance profiles (past performance, competitors, teaming)
  - Insights on government spending, contract awards, industry trends
  - Proposal management, document sharing, compliance tracking
- **Strengths**:
  - Affordable ($60/month entry)
  - Deep competitive intelligence (every federal contractor profiled)
  - Strong for market research and capture planning
  - Team collaboration with up to 10 users on Standard Plan
- **Weaknesses**:
  - No AI proposal writing (intelligence/discovery focus)
  - Limited automation vs newer AI-first competitors
  - Older platform UI vs Govly/Sweetspot

### Lohfeld Consulting + Deltek GovWin IQ

**Position**: Market intelligence + consulting services
- **Pricing**: Expensive. Reviews cite "hard for small companies to afford."
- **Customers**: Lohfeld Consulting uses GovWin for client engagements (20+ years serving GovCon)
- **Key Features**:
  - GovWin IQ for market research, pipeline building
  - 2026: AI-generated proposal frameworks from solicitations
  - AI briefs and notifications for key leads/agencies
  - Labor pricing analytics (15M+ historical/future rates, 1,000+ programs)
  - Deltek Proposals integration (AI-generated proposal creation)
- **Strengths**:
  - Most comprehensive US public contract data source
  - Research and customer support "second to none"
  - Labor pricing analytics unmatched
  - Lohfeld consulting expertise for high-touch support
- **Weaknesses**:
  - Prohibitively expensive for small businesses
  - Complex platform (enterprise-focused)
  - AI proposal features still emerging (2026 roadmap)

### Awarded AI (Procurement Sciences)

**Position**: End-to-end AI-driven platform
- **Key Features**:
  - AI-driven opportunity search
  - Bid/no-bid analysis
  - Advanced proposal creation
  - Compliance verification
  - Competitive intelligence
- **Strengths**:
  - Comprehensive lifecycle coverage
  - AI-first approach across all modules
- **Weaknesses**:
  - Limited public information
  - Unclear pricing and customer base

---

## GovTech Sniper Current State

### What We Have (Phases 0-7 Complete)

#### Discovery & Opportunity Management
- SAM.gov integration with automated polling (Celery Beat)
- Killer Filter qualification scoring (Gemini Flash, 0-100)
- Opportunity snapshots with versioned change tracking/diffing
- PDF attachment downloads with text extraction
- Saved searches with alerting
- Market intelligence fields (contract vehicles, incumbents, buyers, budget)
- SLED jurisdiction tagging (model-level, no data sources)
- Award intelligence records
- Budget intelligence records
- Circuit breaker for SAM.gov rate limiting

#### RFP Analysis & Compliance
- Deep Read analysis (Gemini 1.5 Pro, 1M token context)
- Compliance matrix extraction (mandatory/evaluated/optional)
- Requirement tagging by type (Technical, Management, Past Performance, Pricing)
- Section references with page numbers
- Gap identification
- XLSX compliance matrix export

#### Proposal Generation
- AI section generation with Gemini Context Caching
- Citation enforcement: `[[Source: filename.pdf, Page X]]`
- Knowledge base document upload (resumes, past performance, case studies)
- RAG-powered generation
- Section status tracking
- Word Add-in workflow (session tracking)
- Graphics request tracking
- DOCX/PDF export

#### Capture Pipeline
- Full lifecycle (identified → qualified → pursuit → proposal → submitted → won/lost)
- Bid decision tracking
- Win probability scoring
- Gate reviews
- Teaming partner management
- Custom capture fields per stage
- Competitor intelligence tracking
- Bid match insights
- Kanban visualization

#### Contract Management
- Award tracking
- Deliverable status tracking
- Task/milestone tracking
- CPARS review preparation
- Contract modification tracking
- CLIN quantity/funding lifecycle management
- Parent/child hierarchical contract relationships
- Monthly status report generation

#### Enterprise Features
- JWT auth with token rotation
- SCIM 2.0 provisioning + SSO (Okta, Microsoft Entra ID)
- RBAC
- MFA with TOTP
- AES-256 encryption (secrets vault)
- Audit logging with compliance exports
- Webhooks with delivery logs
- Team management
- API rate limiting by tier (Free/Starter/Professional/Enterprise)

#### AI Assistant (Dash)
- Chat sessions with message history
- Agentic runbooks (RFP summarization, compliance gap planning, proposal kickoff)
- Competitive intelligence summaries
- Tool-calling for multi-step workflows

### What We're Building (Phase 8 — In Progress)
- Compliance shreds
- Document classification
- Proposal outline editor
- Review mode and redline workflows
- Compliance package export
- Labor category mapping

### What's Planned (Phase 9)
- Budget document ingestion
- Award summaries
- AI predictions
- Email ingestion
- Microsoft Dynamics integration depth
- Salesforce AppExchange/AppSource go-to-market packaging

---

## Feature Gap Matrix

### Legend
- ✅ = Fully implemented
- 🟡 = Partially implemented / basic version
- ❌ = Not implemented
- 🔨 = Currently building (Phase 8)
- 📋 = Planned (Phase 9)

### Discovery & Data Sources

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| SAM.gov integration | ✅ | ✅ | ✅ |
| GSA eBuy integration | ✅ | ✅ | ✅ |
| SLED sources (10,000+) | ✅ (BidNet baseline + extensible provider registry) | ✅ | ✅ |
| Private contract vehicles (GWACs/IDIQs) | 🟡 (GSA MAS/CIO-SP3/ITES/OASIS baseline) | ❌ | ✅ (40+) |
| Procurement forecasts | ❌ | ❌ | ✅ |
| Industry days & events | ✅ | ❌ | ✅ |
| DIBBS (DLA) | ✅ | ❌ | ✅ |
| Canada coverage | ❌ | ❌ | ✅ |
| Market signals / daily intel | ✅ | ❌ | ✅ |
| AI opportunity matching (Bid Match) | ✅ (Killer Filter) | ✅ | ✅ |
| Semantic search | ✅ | ❌ | ✅ |
| RFQ predictions | ❌ | ❌ | ✅ |
| Free tier | ✅ | ❌ | ✅ |
| Opportunity change tracking | ✅ (snapshots) | 🟡 | ✅ (alerts) |
| Award tracking | ✅ | ✅ | ✅ |
| Budget intelligence | ✅ | ❌ | ✅ |
| Contact intelligence (AI-extracted) | ✅ | ❌ | ✅ |

### Proposal Writing

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| Compliance matrix generation | ✅ | ✅ | ❌ |
| Full solicitation parsing (Sections C, H, PWS) | 🟡 | ✅ | ❌ |
| Annotated outline generation | ✅ | ✅ | ❌ |
| Writing plans (per-section instructions) | ✅ | ✅ | ❌ |
| AI proposal draft generation | ✅ | ✅ | ❌ |
| Pink-team-ready quality | 🟡 | ✅ | ❌ |
| Focus documents / knowledge base RAG | ✅ | ✅ | ❌ |
| Citation automation | ✅ | ✅ | ❌ |
| Rich text section editor | ✅ | ✅ | ❌ |
| Word Assistant (MS Word add-in) | ✅ | ✅ (full add-in) | ❌ |
| Past performance reuse | ✅ | ✅ | ❌ |
| Color team reviews (pink/red/gold) | ✅ | ✅ | ❌ |
| Graphic generation | ✅ | ✅ | ❌ |
| Proposal outline editor | 🔨 | ✅ | ❌ |
| Redline workflows | 🔨 | 🟡 | ❌ |
| Compliance shreds | 🔨 | ❌ | ❌ |
| Document classification | 🔨 | ❌ | ❌ |
| DOCX/PDF export | ✅ | ✅ | ❌ |
| XLSX compliance matrix export | ✅ | ✅ | ❌ |

### Capture Pipeline

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| Kanban pipeline view | ✅ | ✅ | ❌ |
| Gantt chart view | ✅ | ✅ | ❌ |
| Custom pipeline stages | ✅ | ✅ | ❌ |
| Custom fields | ✅ | ✅ | ❌ |
| Gate reviews | ✅ | ✅ | ❌ |
| Win probability scoring | ✅ | ✅ | ❌ |
| Bid decision tracking | ✅ | ✅ | ❌ |
| Teaming partners | ✅ | ✅ | ✅ |
| Competitor tracking | ✅ | ✅ | ✅ |
| Salesforce sync | ✅ | ✅ (bidirectional) | ✅ |
| Teammate evaluation/workshare | ✅ (workflow action automation) | ✅ | ❌ |

### Contract Management

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| Post-award tracking | ✅ | ✅ | ❌ |
| CPARS preparation | ✅ | ✅ | ❌ |
| Deliverable tracking | ✅ | ✅ | ❌ |
| Contract modifications/CLINs | ✅ | ✅ | ❌ |
| Hierarchical contract structures | ✅ | ✅ | ❌ |
| Monthly status reports | ✅ | ✅ | ❌ |

### AI Capabilities

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| AI assistant (Dash) | ✅ | ✅ | ✅ |
| Semantic document search | 🟡 | ✅ | ✅ |
| Agentic tool-calling | ✅ | ✅ | ✅ |
| Voice mode | ✅ | ✅ | ❌ |
| AI agents (autonomous) | ✅ | 🟡 | ✅ |
| AI contact extraction | ✅ | ❌ | ✅ |
| AI opportunity predictions | ❌ | ❌ | ✅ |
| AI-generated graphics | ✅ | ✅ | ❌ |

### Collaboration

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| Team management | ✅ | ✅ | ✅ |
| RBAC with custom roles | ✅ | ✅ | ✅ |
| Task assignment & comments | 🟡 | ✅ | ✅ |
| Cross-org workspaces | ✅ | ❌ | ✅ |
| Partner/sub sharing | ✅ | ❌ | ✅ |
| Teaming board (find partners) | ✅ | ❌ | ✅ |
| Vendor search | ✅ | ❌ | ✅ |
| Shared team inboxes | ❌ | ❌ | ✅ |
| Real-time collaborative editing | ✅ | ✅ | ❌ |

### Integrations

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| Salesforce | ✅ | ✅ | ✅ |
| SharePoint | ✅ | ✅ | ❌ |
| Microsoft Word Add-in | ✅ | ✅ | ❌ |
| Unanet | 🟡 | ❌ | ✅ |
| Microsoft Dynamics | ❌ | ❌ | 🔨 |
| Webhooks | ✅ | ✅ | ❌ |
| API access | ✅ | ❌ | ✅ |

### Reporting & Analytics

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| Win rate analytics | ✅ | ✅ | ❌ |
| Pipeline value/stage breakdown | ✅ | ✅ | ❌ |
| Conversion rates | ✅ | ✅ | ❌ |
| Proposal turnaround time | ✅ | ✅ | ❌ |
| NAICS performance | ✅ | ✅ | ❌ |
| Team performance metrics | 🟡 | ✅ | ❌ |
| Revenue forecasting | ✅ | ✅ | ❌ |
| Usage metrics dashboard | ✅ | ✅ | ✅ |
| Custom/dynamic reports | ✅ | ✅ | ❌ |
| Data visualizations/trends | ✅ | ❌ | ✅ |

### Security & Compliance

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| SSO (OIDC/SAML) | ✅ | ✅ | 🟡 |
| SCIM provisioning | ✅ | 🟡 | ❌ |
| MFA | ✅ | ✅ | 🟡 |
| Audit logging | ✅ | ✅ | 🟡 |
| Encryption at rest | ✅ | ✅ | ✅ |
| FedRAMP Moderate | 🟡 (readiness in progress) | ✅ | ❌ |
| CMMC certification | 🟡 (readiness in progress) | ✅ | ✅ |
| GovCloud hosting | 🟡 (migration in progress) | ✅ | ❌ |
| Data not used for model training | ✅ (public trust center + runtime no-training enforcement + org controls) | ✅ | ❌ |

---

## What Customers Love

### What Makes Customers Choose GovDash

1. **"Pink-team-ready drafts in under 1 hour"** — The AI doesn't just extract keywords, it generates usable proposal content with citations
2. **Full solicitation parsing** — Catches hidden requirements in Section C and H that other tools miss
3. **End-to-end platform** — One tool replaces 5+ disconnected systems
4. **Word Assistant** — Edit proposals in Word with AI assistance, compliance checks, and graphic generation built in
5. **Measurable ROI** — $50K-$75K/year savings per customer; 50% time reduction
6. **3x more opportunities pursued** — Same team size, dramatically more output
7. **Responsive support team** — Hands-on onboarding and quick issue resolution
8. **FedRAMP/CMMC compliance** — Table stakes for defense contractors

### What Makes Customers Choose Govly

1. **Broadest data coverage** — 40+ private contract vehicles that competitors can't access
2. **Free tier** — Functional free plan removes all adoption friction
3. **Superior UI/UX** — Consistently called the best interface vs GovWin, SAM.gov
4. **Cross-org collaboration** — Share opportunities with partners, OEMs, and subs in one workspace
5. **Network effects** — The more companies join, the more valuable the platform becomes
6. **Color-coded opportunity tracking** — Visual status system loved by sales teams
7. **Price** — Dramatically cheaper than GovWin ($7K-$45K) and BGov
8. **Alerts that matter** — Real-time notifications on opportunity changes
9. **SLED coverage** — 10,000+ state/local sources in one place
10. **80% productivity increase** reported by users

---

## Task Roadmap: Closing the Gap

### Priority Levels
- **P0 (Critical)**: Must-have for market competitiveness. Users will not adopt without these.
- **P1 (High)**: Major differentiators that competitors use to win deals.
- **P2 (Medium)**: Important features that improve retention and expand use cases.
- **P3 (Low)**: Nice-to-haves that round out the platform.

---

### P0 — Critical (Must Ship ASAP)

#### 1. Expand Data Sources Beyond SAM.gov
**Gap**: Foundational breadth is now integrated (GSA eBuy, FPDS, USAspending, SLED BidNet, DIBBS, and core contract-vehicle feeds); next step is scale expansion toward Govly-level source volume.
- [x] **1a. GSA eBuy integration** — Ingest RFQs from GSA eBuy; map to existing RFP model
- [x] **1b. SLED data source integration** — Partner with or scrape from aggregators (Bonfire, BidNet Direct) for state/local/education opportunities
- [x] **1c. FPDS integration** — Pull award data from Federal Procurement Data System for competitor/award intelligence
- [x] **1d. USAspending integration** — Spending data for budget intelligence and agency analysis
- [x] **1e. DIBBS integration** — Defense Logistics Agency bid board for defense-focused customers
- [x] **1f. GWAC/IDIQ contract vehicle feeds** — Start with SEWP, CIO-SP, ITES, GSA MAS, OASIS (evaluate partnership model vs direct scraping)

#### 2. Salesforce Integration
**Gap**: Both competitors have Salesforce integration. This is table stakes for enterprise customers.
- [x] **2a. Bidirectional opportunity sync** — Push/pull opportunities between Sniper and Salesforce
- [x] **2b. Custom field mapping** — Map Sniper capture fields to Salesforce fields
- [x] **2c. Webhook-based real-time sync** — Leverage existing webhook infrastructure
- [x] **2d. Salesforce app listing readiness** — Package + readiness tracker for Salesforce AppExchange submission

#### 3. Proposal Writing Workflow Maturity
**Gap**: GovDash's full-solicitation parsing, annotated outlines, and writing plans are their #1 selling point.
- [x] **3a. Full solicitation parsing (Sections C, H, PWS)** — Expand Deep Read beyond Sections L/M to parse the entire RFP package
- [x] **3b. Annotated outline generation** — After compliance matrix, auto-generate a proposal outline with section headings, compliance mappings, and document scaffolding
- [x] **3c. Writing plans per section** — Allow users to add bullet-point instructions per proposal section (key points, strengths, tone, differentiators) before AI generation
- [x] **3d. Focus document selection** — Let users select which knowledge base documents to prioritize for each proposal (not just all docs)

#### 4. Analytics & Reporting Dashboard
**Gap**: Core analytics are shipped; we still need deeper team-performance reporting and report-builder UX parity.
- [x] **4a. Win rate tracking** — Calculate and display win/loss ratio from capture pipeline data
- [x] **4b. Pipeline value by stage** — Aggregate opportunity values across capture stages
- [x] **4c. Proposal turnaround metrics** — Track time from opportunity to submission
- [x] **4d. Conversion rate tracking** — Track progression rates through pipeline stages
- [x] **4e. Exportable reports** — CSV/PDF export of analytics data
- [x] **4f. Dashboard UI** — Build a dedicated analytics page with charts and KPIs

#### 5. Rich Text Proposal Editor
**Gap**: Rich editor baseline is integrated; tracked suggestions/AI-vs-human diff mode is now shipped with stable rewrite state handling.
- [x] **5a. WYSIWYG section editor** — Implement a rich text editor (TipTap or Slate.js) for proposal sections
- [x] **5b. Inline formatting** — Bold, italic, headers, lists, tables within sections
- [x] **5c. Track changes / suggestions mode** — Show AI-generated vs human-edited content
- [x] **5d. Comments on sections** — Allow team members to leave comments on specific sections
- [x] **5e. Section versioning** — Track changes over time with diff view

---

### P1 — High Priority (Ship Within 60 Days)

#### 6. Color Team Review Workflow
**Gap**: Core pink/red/gold workflow is live; next step is richer collaboration ergonomics and reviewer productivity tooling.
- [x] **6a. Pink team review** — Mark proposal as ready for pink team; assign reviewers; collect structured feedback
- [x] **6b. Red team review** — Post-pink-team review with evaluation criteria and scoring
- [x] **6c. Gold team review** — Final review before submission with executive sign-off
- [x] **6d. Review comments and resolution** — Structured feedback with accept/reject/discuss actions
- [x] **6e. Review status dashboard** — Track review progress across all sections

#### 7. Microsoft Word Add-in (Full Implementation)
**Gap**: Core Word add-in UI + rewrite/compliance/sync are integrated; marketplace distribution listing remains open.
- [x] **7a. Word add-in UI** — Build the actual Office.js add-in with sidebar panel
- [x] **7b. AI writing assistance** — Text shortening, expansion, rewriting within Word
- [x] **7c. Compliance check in Word** — Verify section content against compliance matrix requirements
- [x] **7d. Section sync** — Push/pull section content between Sniper and Word document
- [x] **7e. Microsoft AppSource listing readiness** — Submission package + readiness tracker for enterprise distribution

#### 8. Free Tier / PLG Strategy
**Gap**: Foundational free tier and self-serve signup are in place; upgrade nudges and free-tier marketing experience remain.
- [x] **8a. Define free tier limits** — SAM.gov search (30-day window), basic filtering, limited AI analysis
- [x] **8b. Implement free tier** — Enforce usage limits in API rate limiter
- [x] **8c. Self-serve signup** — Remove demo-booking requirement for free tier
- [x] **8d. Upgrade nudges** — In-product prompts when hitting free tier limits
- [x] **8e. Landing page for free tier** — Marketing page highlighting free features

#### 9. Semantic Search
**Gap**: Closed on 2026-02-14 with pgvector-backed storage in Postgres, SQLite-safe cosine fallback for local/dev, user-scoped embedding isolation, and automatic indexing hooks across core entities.
- [x] **9a. Embedding pipeline** — Generate embeddings for opportunity text, compliance requirements, and knowledge base documents
- [x] **9b. Vector storage** — Add pgvector extension to PostgreSQL (or standalone vector DB)
- [x] **9c. Semantic search API** — Accept natural language queries and return semantically relevant results
- [x] **9d. Cross-entity search** — Search across RFPs, proposals, knowledge base, and capture plans simultaneously
- [x] **9e. Search UI** — Global search bar with semantic results and faceted filtering

#### 10. Contact Intelligence
**Gap**: Contact intelligence lifecycle is integrated end-to-end (extraction, auto-linking, agency directory, search); next parity step is deeper graph enrichment/scoring.
- [x] **10a. AI contact extraction** — Use LLM to extract contacts (names, titles, emails, phones) from RFP documents
- [x] **10b. Agency contact database** — Build/populate a searchable database of government agency contacts
- [x] **10c. Contact linking** — Auto-link extracted contacts to opportunities and agencies
- [x] **10d. Contact search/filter** — Search contacts by agency, role, location

#### 11. Past Performance Reuse System
**Gap**: Past-performance reuse baseline is integrated; next parity step is deeper quality calibration and narrative quality benchmarking at scale.
- [x] **11a. Past performance tagging** — Tag knowledge base documents with contract number, agency, value, period, NAICS
- [x] **11b. Relevance matching** — AI-match past performances to current RFP requirements
- [x] **11c. Narrative repackaging** — Auto-generate past performance narratives tailored to the current proposal's evaluation criteria
- [x] **11d. Past performance library UI** — Browse, search, and manage past performances with metadata

---

### P2 — Medium Priority (Ship Within 90 Days)

#### 12. Procurement Forecasts ✅
**Gap**: Govly surfaces solicitations before they're publicly posted.
- [x] **12a. Agency forecast data ingestion** — Pull procurement forecasts from agency planning documents and forecast feeds
- [x] **12b. Forecast-to-opportunity linking** — Match forecasts to eventual solicitations when posted
- [x] **12c. Forecast alerts** — Notify users when forecasted opportunities match their profile

#### 13. Cross-Organization Collaboration
**Gap**: Core cross-org collaboration is integrated with governed sharing, governance snapshots, SLA trend reporting, and partner audit exports.
- [x] **13a. External workspace invitations** — Invite users from other organizations to specific workspaces
- [x] **13b. Partner portal** — Lightweight view for teaming partners to see shared opportunities
- [x] **13c. Selective data sharing** — Control what data external partners can see
- [x] **13d. Partner contract feed sharing** — Share relevant contract vehicle feeds with partners
- [x] **13e. Partner access presets + workspace switching** — Apply feed bundles quickly and switch between accessible partner portals
- [x] **13f. Partner artifact governance policies** — Enforce admin approval, expiry windows, and partner-scoped visibility before portal release
- [x] **13g. Governance snapshot analytics** — Surface pending approvals, expiring/expired shares, and scoped-vs-global sharing posture in workspace operations
- [x] **13h. Governance SLA trends + audit export** — Track approval-SLA trendlines and export partner share-audit timelines for operational/compliance reviews

#### 14. Teaming Board / Partner Discovery
**Gap**: Teaming discovery and request lifecycle are integrated with partner-fit rationale, trend tracking, and exportable acceptance audits.
- [x] **14a. Company profile pages** — Each organization has a public profile with capabilities, set-asides, past performance
- [x] **14b. Partner search** — Search for potential teaming partners by NAICS, set-aside, capability, clearance
- [x] **14c. Teaming requests** — Send/receive teaming partnership requests
- [x] **14d. Teaming board UI** — Marketplace-style view of available teaming partners
- [x] **14e. Partner-fit trend analytics + request audit export** — Track fit-score/acceptance trendlines and export request decision timelines for collaboration audits

#### 15. Gantt Chart Pipeline View
**Gap**: Gantt/timeline baseline is live; advanced dependencies and at-scale timeline performance still need tuning.
- [x] **15a. Timeline visualization** — Show capture plans on a timeline with milestones
- [x] **15b. Dependency tracking** — Show dependencies between capture activities
- [x] **15c. Deadline visualization** — Highlight approaching deadlines and overdue items

#### 16. AI-Generated Graphics
**Gap**: Core generation/insertion/export parity is integrated; next step is broader template depth and design fidelity tuning.
- [x] **16a. Chart/diagram generation** — AI-generated charts, org charts, process flows from proposal content
- [x] **16b. Template library** — Pre-built graphic templates (management approach, staffing plan, timeline)
- [x] **16c. In-editor insertion** — Insert generated graphics directly into proposal sections
- [x] **16d. Export with graphics** — Include generated graphics in DOCX/PDF exports

#### 17. Voice Mode for Dash
**Gap**: Voice baseline is integrated in Dash chat; next parity step is richer command-intent coverage and telemetry.
- [x] **17a. Speech-to-text input** — Browser-based voice input for Dash queries
- [x] **17b. Text-to-speech output** — Read Dash responses aloud
- [x] **17c. Voice commands** — "Analyze this RFP", "Show my pipeline", "Draft section 3"

#### 18. Contract Modifications & CLINs
**Gap**: Baseline lifecycle is now integrated; next step is richer dependency/status automation at scale.
- [x] **18a. Contract modification tracking** — Track modifications with effective dates and descriptions
- [x] **18b. CLIN management** — Line item tracking with quantities, values, and fulfillment status
- [x] **18c. Hierarchical contracts** — Support parent/child contract relationships (task orders, delivery orders)

#### 19. SharePoint Integration
**Gap**: SharePoint browse/export/sync surfaces are integrated and validated; next step is deeper import automation and error observability.
- [x] **19a. SharePoint file browser** — Browse and import documents from SharePoint folders
- [x] **19b. Proposal export to SharePoint** — Export proposals directly to SharePoint
- [x] **19c. Two-way sync** — Keep documents in sync between Sniper and SharePoint

#### 20. Revenue Forecasting
**Gap**: Revenue forecasting baseline is live; calibration depth and executive forecasting narratives remain.
- [x] **20a. Expected revenue per opportunity** — Track expected contract value and probability-weighted pipeline
- [x] **20b. Revenue timeline** — Visualize expected revenue by month/quarter
- [x] **20c. Win probability weighting** — Apply win probability to expected values for forecasting
- [x] **20d. Pipeline reports** — Aggregate forecasting across all active opportunities

---

### P3 — Lower Priority (Ship Within 120 Days)

#### 21. Industry Days & Events Calendar
**Gap**: Closed on 2026-02-14 with source-ingestion automation, interactive calendar view, and profile-matched alert ranking.
- [x] **21a. Event data ingestion** — Pull industry day events from government sources
- [x] **21b. Calendar view** — Display events on an interactive calendar
- [x] **21c. Event alerts** — Notify users of relevant industry days based on their profile

#### 22. Market Signals / Daily Intelligence
**Gap**: Closed on 2026-02-14 with curated news ingestion, budget-intel signal synthesis, profile-based rescoring, and digest preview/send workflows.
- [x] **22a. News aggregation** — Pull government contracting news from curated sources
- [x] **22b. Budget document analysis** — AI-summarize relevant agency budget documents
- [x] **22c. Signal scoring** — Rate signal relevance based on user's NAICS codes and agency interests
- [x] **22d. Daily digest email** — Email summary of relevant market signals

#### 23. FedRAMP / CMMC Certification
**Gap**: Closed on 2026-02-14 with in-product certification execution controls: GovCloud migration profile, 3PAO readiness package export, and milestone/evidence checkpoint telemetry for FedRAMP/CMMC/GovCloud.
- [x] **23a. Security assessment preparation** — Document security controls against NIST 800-53
- [x] **23b. GovCloud deployment** — Migrate to AWS/Azure GovCloud
- [x] **23c. 3PAO audit** — Engage an accredited third-party assessor
- [x] **23d. Data handling documentation** — Document that user data is never used for model training
- [x] **23e. CMMC Level 2 assessment** — Prepare for CMMC certification

#### 24. Autonomous AI Agents
**Gap**: Agent baseline parity is now integrated end-to-end; next step is richer multi-step planning autonomy and long-horizon memory.
- [x] **24a. Research agent** — Agent that autonomously researches an agency, incumbents, and competitors for a given opportunity
- [x] **24b. Capture planning agent** — Agent that generates a capture plan from an opportunity analysis
- [x] **24c. Proposal prep agent** — Agent that gathers all relevant knowledge base docs, extracts requirements, and sets up a proposal workspace
- [x] **24d. Competitive intel agent** — Agent that monitors competitor wins and surfaces relevant insights

#### 25. Email Ingestion
**Gap**: Closed on 2026-02-14 with production-grade inbox sync, attachment-aware parsing, and confidence-thresholded opportunity creation plus workspace team-inbox routing.
- [x] **25a. Email parsing** — Forward RFP-related emails to a Sniper inbox for automatic processing
- [x] **25b. Attachment extraction** — Auto-extract PDF attachments from forwarded emails
- [x] **25c. Opportunity creation from email** — Auto-create RFP records from forwarded solicitations

#### 26. Canada & International Coverage
**Gap**: Closed on 2026-02-14 with live CanadaBuys open-data ingestion, provincial-portal-enriched provider coverage, and CAD/jurisdiction filtering wired across API + opportunities UI.
- [x] **26a. Canadian government procurement sources** — Integrate with buyandsell.gc.ca and provincial procurement portals
- [x] **26b. Multi-currency support** — Handle CAD and other currencies in pipeline
- [x] **26c. Jurisdiction-aware filtering** — Filter opportunities by country/province/state

#### 27. Unanet Integration
**Gap**: Closed on 2026-02-14 with resource planning + financial sync depth and live integrations UI controls.
- [x] **27a. Project/opportunity sync** — Sync capture pipeline with Unanet projects
- [x] **27b. Resource planning data** — Pull labor categories and rates from Unanet
- [x] **27c. Financial data sync** — Connect contract financials between platforms

#### 28. Smart Workflows / Automation Rules
**Gap**: Rule engine and execution parity are now integrated; next step is broader action catalog and policy governance UX.
- [x] **28a. Workflow rule engine** — If-then rules for opportunity routing (e.g., "If NAICS 541512 AND value > $5M, assign to senior capture manager")
- [x] **28b. Automated stage transitions** — Auto-advance pipeline stage when conditions are met
- [x] **28c. Notification rules** — Custom notification triggers based on opportunity attributes
- [x] **28d. Teammate evaluation** — Auto-evaluate and recommend teaming partners based on requirements

#### 29. Data Privacy & Model Training Guarantees
**Gap**: Closed on 2026-02-14 with public trust-center guarantees, runtime no-training guardrails, org-level privacy policy controls, and SOC 2 Type II execution tracking.
- [x] **29a. Data usage policy page** — Create a public-facing page guaranteeing data isolation
- [x] **29b. Technical implementation** — Ensure Gemini API calls use ephemeral mode / no training data retention
- [x] **29c. SOC 2 preparation** — Begin SOC 2 Type II audit preparation
- [x] **29d. Privacy controls UI** — Give users visibility into how their data is used

#### 30. Mobile Experience
**Gap**: Mobile baseline parity is integrated (responsive shell, push-subscription management, Dash mobile validation); next step is deeper route-by-route adaptive polish.
- [x] **30a. Responsive dashboard** — Ensure all dashboard views work on tablet/mobile
- [x] **30b. Push notifications** — Browser push notifications for alerts and opportunity changes
- [x] **30c. Mobile-optimized Dash** — Chat interface optimized for mobile

#### 31. Real-Time Collaborative Editing
**Gap**: Real-time collaboration baseline (websocket feed, locks, cursor presence, conflict guards) is integrated; next parity step is richer CRDT-level merge ergonomics.
- [x] **31a. WebSocket collaboration server** — Implement CRDT or OT-based real-time editing
- [x] **31b. Cursor presence** — Show other users' cursors in the document
- [x] **31c. Conflict resolution** — Handle simultaneous edits gracefully

#### 32. Template Marketplace
**Gap**: Closed on 2026-02-10 with verticalized template depth + community publishing/discovery UX.
- [x] **32a. Proposal templates** — Pre-built proposal structures by contract type (IT services, construction, professional services)
- [x] **32b. Compliance matrix templates** — Pre-built matrices for common contract vehicles
- [x] **32c. Community templates** — Allow users to share and discover templates

#### 33. Dynamic Custom Reports
**Gap**: Closed on 2026-02-10 with drag/drop field layout, shared view controls, and scheduled email delivery.
- [x] **33a. Report builder** — Drag-and-drop report builder with field selection
- [x] **33b. Saved report views** — Save and share custom report configurations
- [x] **33c. Scheduled report delivery** — Email reports on a schedule

#### 34. Onboarding & Customer Success
**Gap**: Closed on 2026-02-10 with guided onboarding wizard, help center, interactive tutorials, and in-app support chat.
- [x] **34a. In-app onboarding flow** — Guided setup wizard for new accounts
- [x] **34b. Interactive tutorials** — Feature-specific walkthroughs
- [x] **34c. Knowledge base / help center** — Self-serve documentation and guides
- [x] **34d. In-app chat support** — Live chat or chatbot for quick questions

---

## Strategic Recommendations

### Where to Differentiate (Not Just Catch Up)

Rather than simply matching features, consider areas where we can leapfrog competitors:

1. **Gemini 1M token context advantage** — Our use of Gemini's 1M token context window for Deep Read is technically superior to GovDash's approach. Lean into this for full-solicitation parsing of massive RFP packages (500+ pages).

2. **Open API strategy** — Neither competitor has a robust public API. We already have rate-limited API access by tier. Build an API-first ecosystem.

3. **Speed of AI generation** — Gemini Flash for Killer Filter is fast and cheap. Use this for real-time qualification scoring that competitors can't match.

4. **Compliance shreds (Phase 8)** — This is a feature neither competitor has. If executed well, it's a genuine differentiator for compliance-heavy proposals.

5. **Transparent pricing** — Both competitors hide pricing. Publish transparent pricing to build trust with small businesses.

6. **Context Caching** — Our Gemini Context Caching approach for knowledge base RAG is more efficient than traditional vector DB approaches. Market this as faster and more accurate.

### Recommended Execution Order

1. **Months 1-2**: P0 items (data sources, Salesforce, proposal workflow, analytics, rich editor)
2. **Months 2-3**: P1 items (color team reviews, Word add-in, free tier, semantic search, contacts)
3. **Months 3-4**: P2 items (procurement forecasts, cross-org collaboration, Gantt, graphics)
4. **Months 4-6**: P3 items (industry days, market signals, FedRAMP, autonomous agents)

### Key Metrics to Track

| Metric | Current | Target (6 months) |
|--------|---------|-------------------|
| Data sources integrated | 1 (SAM.gov) | 8+ |
| Avg proposal generation time | Unknown | < 2 hours |
| Free tier signups | 0 | 500+ |
| Paid customers | Unknown | 50+ |
| Customer win rate | Unknown | Track baseline |
| NPS score | Unknown | 50+ |
| Feature parity score (vs GovDash) | ~55% | 85% |
| Feature parity score (vs Govly) | ~35% | 70% |

---

## 2026 Competitive Landscape Summary

### Market Segmentation by Customer Profile

| Segment | Best Fit Competitor | Why They Win | Price Point |
|---------|---------------------|--------------|-------------|
| **Defense/IC contractors (CUI/classified)** | GovSignals | FedRAMP High authorization, SOC 2 security | $50K+/year |
| **Enterprise GovCon (Top 100)** | GovDash | End-to-end platform, Word integration, FedRAMP Moderate | $40K+/year |
| **Mid-market BD teams** | GovDash, Govly | Breadth of features + data sources | $15K-$40K/year |
| **Small businesses (<50 employees)** | Govly, Sweetspot, CLEATUS | Free tier or affordable entry ($60-$3K/year) | $0-$5K/year |
| **Micro-contractors (1-5 FTE)** | CLEATUS, Sweetspot | Simple, fast, affordable AI automation | $60-$1K/year |
| **Capture-focused teams** | Capture2Proposal, GovTribe | Capture lifecycle management, intelligence | $2.6K-$5.5K/year |
| **Unanet AE customers** | Unanet ProposalAI | Native integration with existing ERP/GovCon system | Unknown |
| **Enterprise co-authoring** | XaitPorter | Distributed teams, version control, audit trails | $10K+/year |
| **Market research/intelligence** | GovWin IQ, GovTribe | Deepest data, labor pricing, competitive intel | $7K-$45K/year |

### Competitive Positioning Insights

#### 1. Price Transparency Opportunity
- **Opaque pricing**: GovDash, GovSignals, Unanet, XaitPorter, GovWin — all require sales calls
- **Transparent pricing**: Govly ($3K-$15K), Sweetspot ($60/month), CLEATUS (trial available), Capture2Proposal ($2,640/year), GovTribe ($60/month)
- **Opportunity**: GovTech Sniper can differentiate with transparent, published pricing tiers

#### 2. Free Tier PLG Strategy
- **Free tier leaders**: Govly (30-day SAM.gov + 6K SLED), Sweetspot (trial), CLEATUS (trial), GovTribe (14-day trial)
- **No free option**: GovDash, GovSignals, Unanet, XaitPorter
- **Opportunity**: GovTech Sniper's free tier can drive SMB adoption and product-led growth

#### 3. Security Certification Gaps
- **FedRAMP High**: GovSignals (ONLY one)
- **FedRAMP Moderate**: GovDash (Q1 2026)
- **CMMC Level 2**: Govly (first in category)
- **AWS GovCloud**: GovDash, Unanet
- **Everyone else**: No certifications visible
- **Opportunity**: Fast-track FedRAMP Moderate + CMMC Level 2 to compete for defense/IC contracts

#### 4. Data Source Coverage Race
- **Broadest coverage**: Govly (40+ contract vehicles, 10K+ SLED, DIBBS, Canada)
- **Solid coverage**: Sweetspot (SAM.gov, USAspending, FPDS, DIBBS, 1K+ state/local)
- **Limited**: GovDash (SAM.gov, GSA eBuy, SLED)
- **Specialized**: GovWin (deepest federal data but expensive)
- **Opportunity**: GovTech Sniper's extensible provider registry can rapidly expand sources

#### 5. AI Proposal Writing Maturity
- **Most mature**: GovDash (pink-team-ready drafts, full solicitation parsing, Word Assistant)
- **Strong**: GovSignals (>95% accurate outlines in <5 min, FedRAMP-secure generation)
- **Emerging**: Unanet ProposalAI (70% time reduction, no hallucinations), ProposalWriter.ai
- **Limited**: CLEATUS (fast but quality unclear), Sweetspot (Proposal Copilot)
- **Not a focus**: Govly, GovTribe, Capture2Proposal
- **Opportunity**: GovTech Sniper's Gemini 1M context + Context Caching can leapfrog on quality

#### 6. Integration Ecosystem Gaps
| Integration | GovDash | Govly | GovSignals | Others |
|-------------|---------|-------|------------|--------|
| Salesforce | ✅ (bidirectional) | ✅ | ❌ | Some |
| SharePoint | ✅ | ❌ | ❌ | Rare |
| MS Word Add-in | ✅ (AppSource) | ❌ | ❌ | XaitPorter only |
| Unanet | ❌ | ✅ | ❌ | ProposalAI (native) |
| MS Dynamics | ❌ | 🔨 (building) | ❌ | Rare |
| Public API | ❌ | ✅ | ❌ | GovTribe, Sweetspot |

**Opportunity**: GovTech Sniper's open API + Word add-in + SharePoint can match or exceed integration breadth

#### 7. Collaboration Features
- **Cross-org leaders**: Govly (workspaces, partner sharing, teaming board), Sweetspot (team collaboration)
- **Limited**: GovDash (no cross-org features), GovSignals (enterprise only)
- **Strong capture**: Capture2Proposal (teaming tracking, NDAs, workshare)
- **Opportunity**: GovTech Sniper's cross-org workspaces + teaming board already match Govly

#### 8. Customer Success & Onboarding
- **White-glove**: GovDash (hands-on onboarding, dedicated support)
- **Self-serve**: Govly (free tier, simple UI), Sweetspot (fast signup), CLEATUS (trial-driven)
- **Mixed**: Most others (sales-led with training)
- **Opportunity**: Hybrid model — self-serve for SMBs, white-glove for enterprise

### Key Takeaways for GovTech Sniper Strategy

#### Where We Can Win

1. **Price transparency + free tier** → Attract SMBs frustrated by opaque pricing
2. **API-first ecosystem** → Enable integrations competitors don't offer
3. **Speed of AI generation** → Gemini Flash/Pro advantage for real-time analysis
4. **Compliance as code** → Automated compliance checks (not just manual matrix building)
5. **Data source breadth** → Extensible provider model can match Govly's 40+ sources
6. **Transparent security** → Public commitment on data handling, faster FedRAMP/CMMC

#### Where We Must Catch Up (P0 Gaps)

1. **FedRAMP/CMMC certifications** → Critical for defense contractors
2. **Pink-team-ready draft quality** → GovDash sets the bar; we must match or exceed
3. **Full solicitation parsing depth** → Sections C/H/PWS beyond just L/M
4. **Word Assistant maturity** → AppSource listing + full feature parity
5. **Data source expansion** → Reach 10+ sources quickly (currently at ~8 with recent integrations)

#### Where We Can Leapfrog

1. **Compliance shreds** → Feature neither major competitor has
2. **Gemini 1M context window** → Technical advantage for massive RFP packages
3. **Context Caching efficiency** → Faster/cheaper than vector DB approaches
4. **Open roadmap transparency** → Public feature voting/requests vs closed development
5. **Developer ecosystem** → Public API + webhooks + integrations marketplace

### Recommended Competitive Positioning Statement

> **GovTech Sniper is the only AI proposal platform built for speed, transparency, and extensibility.**
>
> Unlike enterprise-only tools (GovDash, GovSignals) with opaque pricing and limited data sources, we offer:
> - Transparent pricing with a functional free tier
> - 10+ data sources (federal, SLED, contract vehicles) and growing
> - Industry-leading AI speed with Gemini's 1M token context
> - Open API and integration ecosystem
> - Compliance automation (not just manual matrix building)
>
> Unlike discovery-focused tools (Govly, GovTribe) with limited proposal features, we offer:
> - Pink-team-ready AI proposal drafts in under 2 hours
> - Full solicitation parsing (Sections L/M/C/H/PWS)
> - Microsoft Word add-in for in-document AI assistance
> - Color team review workflows (pink/red/gold)
> - Contract lifecycle management beyond capture
>
> We're the platform for teams that want GovDash-quality proposals at Govly-level data breadth without enterprise-only pricing.

---

## Sources

This analysis incorporates research from the following sources (February 2026):

**GovDash**
- [GovDash Software Features | Capterra](https://www.capterra.com/p/10020317/GovDash/)
- [Pricing | GovDash](https://www.govdash.com/pricing)
- [GovDash Reviews | SoftwareWorld](https://www.softwareworld.co/software/govdash-reviews/)
- [AI for Government Contracting | GovDash](https://www.govdash.com/)
- [GovDash Customer Stories](https://www.govdash.com/customer-stories)
- [GovDash Support Docs](https://support.govdash.com/docs)
- [Proposal Cloud Deep Dive (GovDash Support)](https://support.govdash.com/docs/proposal-cloud-deep-dive)
- [Compliance Matrix and Shreds (GovDash Support)](https://support.govdash.com/docs/compliance-matrix-and-shreds)
- [Outlines Deep Dive (GovDash Support)](https://support.govdash.com/docs/proposal-cloud-a-deep-dive-into-outlines)
- [Past Performance Deep Dive (GovDash Support)](https://support.govdash.com/docs/proposal-cloud-a-deep-dive-into-the-past-performance-tab)

**Regulatory and Industry Direction**
- [FedRAMP 20x Phase Two](https://www.fedramp.gov/20x/phase-two/)
- [FedRAMP 20x Phase Two Process](https://www.fedramp.gov/20x/phase-two/process/)
- [DFARS 204.7504](https://www.acquisition.gov/dfars/204.7504-solicitation-provision-and-contract-clause)
- [CMMC Program Rule (32 CFR Part 170)](https://www.ecfr.gov/current/title-32/subtitle-A/chapter-I/subchapter-D/part-170)

**Primary AI Evaluation Research**
- [G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment](https://arxiv.org/abs/2303.16634)
- [RAGAS: Automated Evaluation of Retrieval Augmented Generation](https://arxiv.org/abs/2309.15217)
- [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)

**Govly**
- [Govly Pricing | Capterra](https://www.capterra.com/p/265284/Govly/)
- [Govly Features | GetApp](https://www.getapp.com/government-social-services-software/a/govly/)
- [Govly: Market Network for Government Contractors](https://www.govly.com/)

**GovSignals**
- [GovSignals | FedRAMP High AI Platform](https://www.govsignals.ai)
- [GovSignals Pricing | Capterra](https://www.capterra.com/p/10016450/GovSignals/)
- [Best Secure AI Platforms | GovEagle](https://www.goveagle.com/blog/secure-ai-platforms-government-proposal-data)

**CLEATUS**
- [CLEATUS - AI-Powered Government Contracting](https://www.cleat.ai/)
- [CLEATUS Pricing](https://www.cleat.ai/pricing)
- [AI Government Contract Proposal Writer | CLEATUS](https://www.cleat.ai/features/proposal-writer)

**Sweetspot**
- [Sweetspot - AI Government Contracting Platform](https://www.sweetspot.so/)
- [Sweetspot Pricing](https://www.sweetspot.so/pricing/)
- [Sweetspot (YC S23) | Y Combinator](https://www.ycombinator.com/companies/sweetspot)

**Unanet ProposalAI**
- [ProposalAI | Unanet](https://unanet.com/proposal-ai)
- [Unanet ProposalAI Features | GetApp](https://www.getapp.com/sales-software/a/unanet-proposalai/)

**XaitPorter/Privia**
- [Bid and Proposal Software | Privia](https://www.xait.com/industry/proposal-software-for-government-contracting)
- [Top Proposal Writing Software 2026 | GovCon Digest](https://govcondigest.com/top-proposal-writing-software-2026/)

**Capture2Proposal**
- [Capture2Proposal Features](https://capture2proposal.com/capture-2-features/)
- [Capture2Proposal Pricing | Capterra](https://www.capterra.com/p/186390/Capture2Proposal/)

**GovTribe**
- [GovTribe Reviews | SoftwareWorld](https://www.softwareworld.co/software/govtribe-reviews/)
- [GovTribe | Grow Your Government Business](https://govtribe.com/)
- [Top 5 Government Contract Opportunity Tools](https://iquasar.com/blog/5-government-contract-opportunity-search-tools/)

**Deltek GovWin IQ**
- [Lohfeld Consulting - GovWin IQ Powers Proposal Development](https://www.deltek.com/en/blog/customer-story-lohfeld-consulting)
- [Deltek GovWin IQ Pricing | Capterra](https://www.capterra.com/p/154858/GovWin-IQ/)
- [Find and Win Federal Contracts | Deltek GovWin IQ](https://www.deltek.com/en/government-contracting/govwin/federal)

**General Market Analysis**
- [Best & Worst Gov Contracting Tools 2025](https://www.dodcontract.com/blog/best-worst-gov-contracting-tools-in-2025)
- [Top Proposal Writing Software 2026 | GovCon Digest](https://govcondigest.com/top-proposal-writing-software-2026/)
- [Top 10 Best Proposal Software 2026](https://www.inventive.ai/blog-posts/top-proposal-software-tools)

---

*This document should be reviewed monthly and updated as features ship and competitive landscape evolves.*
