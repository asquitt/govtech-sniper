# Competitive Analysis & Task Roadmap: GovTech Sniper vs GovDash vs Govly

> **Generated**: February 6, 2026
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
3. **Compliance matrix quality**: Full-solicitation parsing catches requirements hidden in Sections C and H
4. **Increased output**: Customers pursue 3x more opportunities with the same team
5. **Word integration**: The Word Assistant is consistently called a "game changer"
6. **Support quality**: "Extremely responsive and considerate"
7. **Pink-team-ready draft quality**: AI drafts are usable starting points, not generic filler
8. **End-to-end platform**: Eliminates need for 5+ disconnected tools

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
- Collaboration workspace
- Email ingestion
- CRM sync

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
| GSA eBuy integration | ❌ | ✅ | ✅ |
| SLED sources (10,000+) | ❌ (tag only) | ✅ | ✅ |
| Private contract vehicles (GWACs/IDIQs) | ❌ | ❌ | ✅ (40+) |
| Procurement forecasts | ❌ | ❌ | ✅ |
| Industry days & events | ❌ | ❌ | ✅ |
| DIBBS (DLA) | ❌ | ❌ | ✅ |
| Canada coverage | ❌ | ❌ | ✅ |
| Market signals / daily intel | ❌ | ❌ | ✅ |
| AI opportunity matching (Bid Match) | ✅ (Killer Filter) | ✅ | ✅ |
| Semantic search | ❌ | ❌ | ✅ |
| RFQ predictions | ❌ | ❌ | ✅ |
| Free tier | ❌ | ❌ | ✅ |
| Opportunity change tracking | ✅ (snapshots) | 🟡 | ✅ (alerts) |
| Award tracking | ✅ | ✅ | ✅ |
| Budget intelligence | ✅ | ❌ | ✅ |
| Contact intelligence (AI-extracted) | 🟡 (manual) | ❌ | ✅ |

### Proposal Writing

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| Compliance matrix generation | ✅ | ✅ | ❌ |
| Full solicitation parsing (Sections C, H, PWS) | 🟡 | ✅ | ❌ |
| Annotated outline generation | ❌ | ✅ | ❌ |
| Writing plans (per-section instructions) | ❌ | ✅ | ❌ |
| AI proposal draft generation | ✅ | ✅ | ❌ |
| Pink-team-ready quality | 🟡 | ✅ | ❌ |
| Focus documents / knowledge base RAG | ✅ | ✅ | ❌ |
| Citation automation | ✅ | ✅ | ❌ |
| Rich text section editor | 🟡 | ✅ | ❌ |
| Word Assistant (MS Word add-in) | 🟡 (sessions) | ✅ (full add-in) | ❌ |
| Past performance reuse | 🟡 | ✅ | ❌ |
| Color team reviews (pink/red/gold) | ❌ | ✅ | ❌ |
| Graphic generation | 🟡 (tracking) | ✅ | ❌ |
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
| Gantt chart view | ❌ | ✅ | ❌ |
| Custom pipeline stages | ✅ | ✅ | ❌ |
| Custom fields | ✅ | ✅ | ❌ |
| Gate reviews | ✅ | ✅ | ❌ |
| Win probability scoring | ✅ | ✅ | ❌ |
| Bid decision tracking | ✅ | ✅ | ❌ |
| Teaming partners | ✅ | ✅ | ✅ |
| Competitor tracking | ✅ | ✅ | ✅ |
| Salesforce sync | ❌ | ✅ (bidirectional) | ✅ |
| Teammate evaluation/workshare | ❌ | ✅ | ❌ |

### Contract Management

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| Post-award tracking | ✅ | ✅ | ❌ |
| CPARS preparation | ✅ | ✅ | ❌ |
| Deliverable tracking | ✅ | ✅ | ❌ |
| Contract modifications/CLINs | ❌ | ✅ | ❌ |
| Hierarchical contract structures | ❌ | ✅ | ❌ |
| Monthly status reports | ✅ | ✅ | ❌ |

### AI Capabilities

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| AI assistant (Dash) | ✅ | ✅ | ✅ |
| Semantic document search | 🟡 | ✅ | ✅ |
| Agentic tool-calling | ✅ | ✅ | ✅ |
| Voice mode | ❌ | ✅ | ❌ |
| AI agents (autonomous) | ❌ | 🟡 | ✅ |
| AI contact extraction | ❌ | ❌ | ✅ |
| AI opportunity predictions | ❌ | ❌ | ✅ |
| AI-generated graphics | ❌ | ✅ | ❌ |

### Collaboration

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| Team management | ✅ | ✅ | ✅ |
| RBAC with custom roles | ✅ | ✅ | ✅ |
| Task assignment & comments | 🟡 | ✅ | ✅ |
| Cross-org workspaces | ❌ | ❌ | ✅ |
| Partner/sub sharing | ❌ | ❌ | ✅ |
| Teaming board (find partners) | ❌ | ❌ | ✅ |
| Vendor search | ❌ | ❌ | ✅ |
| Shared team inboxes | ❌ | ❌ | ✅ |
| Real-time collaborative editing | ❌ | ✅ | ❌ |

### Integrations

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| Salesforce | ❌ | ✅ | ✅ |
| SharePoint | ❌ | ✅ | ❌ |
| Microsoft Word Add-in | 🟡 | ✅ | ❌ |
| Unanet | ❌ | ❌ | ✅ |
| Microsoft Dynamics | ❌ | ❌ | 🔨 |
| Webhooks | ✅ | ✅ | ❌ |
| API access | ✅ | ❌ | ✅ |

### Reporting & Analytics

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| Win rate analytics | ❌ | ✅ | ❌ |
| Pipeline value/stage breakdown | ❌ | ✅ | ❌ |
| Conversion rates | ❌ | ✅ | ❌ |
| Proposal turnaround time | ❌ | ✅ | ❌ |
| NAICS performance | ❌ | ✅ | ❌ |
| Team performance metrics | ❌ | ✅ | ❌ |
| Revenue forecasting | ❌ | ✅ | ❌ |
| Usage metrics dashboard | ✅ | ✅ | ✅ |
| Custom/dynamic reports | ❌ | ✅ | ❌ |
| Data visualizations/trends | ❌ | ❌ | ✅ |

### Security & Compliance

| Feature | GovTech Sniper | GovDash | Govly |
|---------|---------------|---------|-------|
| SSO (OIDC/SAML) | ✅ | ✅ | 🟡 |
| SCIM provisioning | ✅ | 🟡 | ❌ |
| MFA | ✅ | ✅ | 🟡 |
| Audit logging | ✅ | ✅ | 🟡 |
| Encryption at rest | ✅ | ✅ | ✅ |
| FedRAMP Moderate | ❌ | ✅ | ❌ |
| CMMC certification | ❌ | ✅ | ✅ |
| GovCloud hosting | ❌ | ✅ | ❌ |
| Data not used for model training | ❌ (unclear) | ✅ | ❌ |

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
**Gap**: We only have SAM.gov. Govly has 40+ contract vehicles and 10,000+ SLED sources. GovDash has GSA eBuy and SLED.
- [ ] **1a. GSA eBuy integration** — Ingest RFQs from GSA eBuy; map to existing RFP model
- [ ] **1b. SLED data source integration** — Partner with or scrape from aggregators (Bonfire, BidNet Direct) for state/local/education opportunities
- [ ] **1c. FPDS integration** — Pull award data from Federal Procurement Data System for competitor/award intelligence
- [ ] **1d. USAspending integration** — Spending data for budget intelligence and agency analysis
- [ ] **1e. DIBBS integration** — Defense Logistics Agency bid board for defense-focused customers
- [ ] **1f. GWAC/IDIQ contract vehicle feeds** — Start with SEWP, CIO-SP, ITES, GSA MAS, OASIS (evaluate partnership model vs direct scraping)

#### 2. Salesforce Integration
**Gap**: Both competitors have Salesforce integration. This is table stakes for enterprise customers.
- [ ] **2a. Bidirectional opportunity sync** — Push/pull opportunities between Sniper and Salesforce
- [ ] **2b. Custom field mapping** — Map Sniper capture fields to Salesforce fields
- [ ] **2c. Webhook-based real-time sync** — Leverage existing webhook infrastructure
- [ ] **2d. Salesforce app listing** — Package as a Salesforce AppExchange app

#### 3. Proposal Writing Workflow Maturity
**Gap**: GovDash's full-solicitation parsing, annotated outlines, and writing plans are their #1 selling point.
- [ ] **3a. Full solicitation parsing (Sections C, H, PWS)** — Expand Deep Read beyond Sections L/M to parse the entire RFP package
- [ ] **3b. Annotated outline generation** — After compliance matrix, auto-generate a proposal outline with section headings, compliance mappings, and document scaffolding
- [ ] **3c. Writing plans per section** — Allow users to add bullet-point instructions per proposal section (key points, strengths, tone, differentiators) before AI generation
- [ ] **3d. Focus document selection** — Let users select which knowledge base documents to prioritize for each proposal (not just all docs)

#### 4. Analytics & Reporting Dashboard
**Gap**: GovDash has a full reporting center. We have basic usage metrics only.
- [ ] **4a. Win rate tracking** — Calculate and display win/loss ratio from capture pipeline data
- [ ] **4b. Pipeline value by stage** — Aggregate opportunity values across capture stages
- [ ] **4c. Proposal turnaround metrics** — Track time from opportunity to submission
- [ ] **4d. Conversion rate tracking** — Track progression rates through pipeline stages
- [ ] **4e. Exportable reports** — CSV/PDF export of analytics data
- [ ] **4f. Dashboard UI** — Build a dedicated analytics page with charts and KPIs

#### 5. Rich Text Proposal Editor
**Gap**: GovDash has a full rich text editor for in-platform collaboration. We have basic section content display.
- [ ] **5a. WYSIWYG section editor** — Implement a rich text editor (TipTap or Slate.js) for proposal sections
- [ ] **5b. Inline formatting** — Bold, italic, headers, lists, tables within sections
- [ ] **5c. Track changes / suggestions mode** — Show AI-generated vs human-edited content
- [ ] **5d. Comments on sections** — Allow team members to leave comments on specific sections
- [ ] **5e. Section versioning** — Track changes over time with diff view

---

### P1 — High Priority (Ship Within 60 Days)

#### 6. Color Team Review Workflow
**Gap**: GovDash supports structured pink/red/gold team reviews. We have nothing.
- [ ] **6a. Pink team review** — Mark proposal as ready for pink team; assign reviewers; collect structured feedback
- [ ] **6b. Red team review** — Post-pink-team review with evaluation criteria and scoring
- [ ] **6c. Gold team review** — Final review before submission with executive sign-off
- [ ] **6d. Review comments and resolution** — Structured feedback with accept/reject/discuss actions
- [ ] **6e. Review status dashboard** — Track review progress across all sections

#### 7. Microsoft Word Add-in (Full Implementation)
**Gap**: GovDash's Word Assistant is their most-praised feature. We only have session tracking.
- [ ] **7a. Word add-in UI** — Build the actual Office.js add-in with sidebar panel
- [ ] **7b. AI writing assistance** — Text shortening, expansion, rewriting within Word
- [ ] **7c. Compliance check in Word** — Verify section content against compliance matrix requirements
- [ ] **7d. Section sync** — Push/pull section content between Sniper and Word document
- [ ] **7e. Microsoft AppSource listing** — Publish add-in for enterprise distribution

#### 8. Free Tier / PLG Strategy
**Gap**: Govly's free plan drives adoption and network effects. We have no free tier.
- [ ] **8a. Define free tier limits** — SAM.gov search (30-day window), basic filtering, limited AI analysis
- [ ] **8b. Implement free tier** — Enforce usage limits in API rate limiter
- [ ] **8c. Self-serve signup** — Remove demo-booking requirement for free tier
- [ ] **8d. Upgrade nudges** — In-product prompts when hitting free tier limits
- [ ] **8e. Landing page for free tier** — Marketing page highlighting free features

#### 9. Semantic Search
**Gap**: Govly has NLP-powered semantic search. We have keyword-based filtering.
- [ ] **9a. Embedding pipeline** — Generate embeddings for opportunity text, compliance requirements, and knowledge base documents
- [ ] **9b. Vector storage** — Add pgvector extension to PostgreSQL (or standalone vector DB)
- [ ] **9c. Semantic search API** — Accept natural language queries and return semantically relevant results
- [ ] **9d. Cross-entity search** — Search across RFPs, proposals, knowledge base, and capture plans simultaneously
- [ ] **9e. Search UI** — Global search bar with semantic results and faceted filtering

#### 10. Contact Intelligence
**Gap**: Govly has AI-extracted contacts from opportunity documents. We have manual contact management.
- [ ] **10a. AI contact extraction** — Use LLM to extract contacts (names, titles, emails, phones) from RFP documents
- [ ] **10b. Agency contact database** — Build/populate a searchable database of government agency contacts
- [ ] **10c. Contact linking** — Auto-link extracted contacts to opportunities and agencies
- [ ] **10d. Contact search/filter** — Search contacts by agency, role, location

#### 11. Past Performance Reuse System
**Gap**: GovDash automates past performance retrieval and repackaging. We store docs but don't intelligently reuse them.
- [ ] **11a. Past performance tagging** — Tag knowledge base documents with contract number, agency, value, period, NAICS
- [ ] **11b. Relevance matching** — AI-match past performances to current RFP requirements
- [ ] **11c. Narrative repackaging** — Auto-generate past performance narratives tailored to the current proposal's evaluation criteria
- [ ] **11d. Past performance library UI** — Browse, search, and manage past performances with metadata

---

### P2 — Medium Priority (Ship Within 90 Days)

#### 12. Procurement Forecasts ✅
**Gap**: Govly surfaces solicitations before they're publicly posted.
- [x] **12a. Agency forecast data ingestion** — Pull procurement forecasts from agency planning documents and forecast feeds
- [x] **12b. Forecast-to-opportunity linking** — Match forecasts to eventual solicitations when posted
- [x] **12c. Forecast alerts** — Notify users when forecasted opportunities match their profile

#### 13. Cross-Organization Collaboration
**Gap**: Govly's workspaces allow primes, subs, and partners to collaborate on a shared platform.
- [ ] **13a. External workspace invitations** — Invite users from other organizations to specific workspaces
- [ ] **13b. Partner portal** — Lightweight view for teaming partners to see shared opportunities
- [ ] **13c. Selective data sharing** — Control what data external partners can see
- [ ] **13d. Partner contract feed sharing** — Share relevant contract vehicle feeds with partners

#### 14. Teaming Board / Partner Discovery
**Gap**: Govly has a teaming board to find and connect with potential partners.
- [ ] **14a. Company profile pages** — Each organization has a public profile with capabilities, set-asides, past performance
- [ ] **14b. Partner search** — Search for potential teaming partners by NAICS, set-aside, capability, clearance
- [ ] **14c. Teaming requests** — Send/receive teaming partnership requests
- [ ] **14d. Teaming board UI** — Marketplace-style view of available teaming partners

#### 15. Gantt Chart Pipeline View
**Gap**: GovDash has Gantt chart view alongside Kanban.
- [ ] **15a. Timeline visualization** — Show capture plans on a timeline with milestones
- [ ] **15b. Dependency tracking** — Show dependencies between capture activities
- [ ] **15c. Deadline visualization** — Highlight approaching deadlines and overdue items

#### 16. AI-Generated Graphics
**Gap**: GovDash generates visual graphics within proposals.
- [ ] **16a. Chart/diagram generation** — AI-generated charts, org charts, process flows from proposal content
- [ ] **16b. Template library** — Pre-built graphic templates (management approach, staffing plan, timeline)
- [ ] **16c. In-editor insertion** — Insert generated graphics directly into proposal sections
- [ ] **16d. Export with graphics** — Include generated graphics in DOCX/PDF exports

#### 17. Voice Mode for Dash
**Gap**: GovDash has voice mode for hands-free interaction.
- [ ] **17a. Speech-to-text input** — Browser-based voice input for Dash queries
- [ ] **17b. Text-to-speech output** — Read Dash responses aloud
- [ ] **17c. Voice commands** — "Analyze this RFP", "Show my pipeline", "Draft section 3"

#### 18. Contract Modifications & CLINs
**Gap**: GovDash handles contract modifications and CLIN management.
- [ ] **18a. Contract modification tracking** — Track modifications with effective dates and descriptions
- [ ] **18b. CLIN management** — Line item tracking with quantities, values, and fulfillment status
- [ ] **18c. Hierarchical contracts** — Support parent/child contract relationships (task orders, delivery orders)

#### 19. SharePoint Integration
**Gap**: GovDash has SharePoint integration for document storage and proposal export.
- [ ] **19a. SharePoint file browser** — Browse and import documents from SharePoint folders
- [ ] **19b. Proposal export to SharePoint** — Export proposals directly to SharePoint
- [ ] **19c. Two-way sync** — Keep documents in sync between Sniper and SharePoint

#### 20. Revenue Forecasting
**Gap**: GovDash tracks revenue timelines and forecasting.
- [ ] **20a. Expected revenue per opportunity** — Track expected contract value and probability-weighted pipeline
- [ ] **20b. Revenue timeline** — Visualize expected revenue by month/quarter
- [ ] **20c. Win probability weighting** — Apply win probability to expected values for forecasting
- [ ] **20d. Pipeline reports** — Aggregate forecasting across all active opportunities

---

### P3 — Lower Priority (Ship Within 120 Days)

#### 21. Industry Days & Events Calendar
**Gap**: Govly tracks pre-solicitation conferences and industry days.
- [ ] **21a. Event data ingestion** — Pull industry day events from government sources
- [ ] **21b. Calendar view** — Display events on an interactive calendar
- [ ] **21c. Event alerts** — Notify users of relevant industry days based on their profile

#### 22. Market Signals / Daily Intelligence
**Gap**: Govly provides daily intelligence from government news, budgets, and congressional orders.
- [ ] **22a. News aggregation** — Pull government contracting news from curated sources
- [ ] **22b. Budget document analysis** — AI-summarize relevant agency budget documents
- [ ] **22c. Signal scoring** — Rate signal relevance based on user's NAICS codes and agency interests
- [ ] **22d. Daily digest email** — Email summary of relevant market signals

#### 23. FedRAMP / CMMC Certification
**Gap**: GovDash has FedRAMP Moderate Equivalency. Govly has CMMC Level 2. We have neither.
- [ ] **23a. Security assessment preparation** — Document security controls against NIST 800-53
- [ ] **23b. GovCloud deployment** — Migrate to AWS/Azure GovCloud
- [ ] **23c. 3PAO audit** — Engage an accredited third-party assessor
- [ ] **23d. Data handling documentation** — Document that user data is never used for model training
- [ ] **23e. CMMC Level 2 assessment** — Prepare for CMMC certification

#### 24. Autonomous AI Agents
**Gap**: Govly has autonomous agents (Program Analyst, Government Programs). GovDash has increasingly autonomous Dash.
- [ ] **24a. Research agent** — Agent that autonomously researches an agency, incumbents, and competitors for a given opportunity
- [ ] **24b. Capture planning agent** — Agent that generates a capture plan from an opportunity analysis
- [ ] **24c. Proposal prep agent** — Agent that gathers all relevant knowledge base docs, extracts requirements, and sets up a proposal workspace
- [ ] **24d. Competitive intel agent** — Agent that monitors competitor wins and surfaces relevant insights

#### 25. Email Ingestion
**Gap**: Planned in Phase 9 but not started. Govly has team inboxes.
- [ ] **25a. Email parsing** — Forward RFP-related emails to a Sniper inbox for automatic processing
- [ ] **25b. Attachment extraction** — Auto-extract PDF attachments from forwarded emails
- [ ] **25c. Opportunity creation from email** — Auto-create RFP records from forwarded solicitations

#### 26. Canada & International Coverage
**Gap**: Govly recently added Canada. GovDash is US-only.
- [ ] **26a. Canadian government procurement sources** — Integrate with buyandsell.gc.ca and provincial procurement portals
- [ ] **26b. Multi-currency support** — Handle CAD and other currencies in pipeline
- [ ] **26c. Jurisdiction-aware filtering** — Filter opportunities by country/province/state

#### 27. Unanet Integration
**Gap**: Govly integrates with Unanet (popular GovCon ERP).
- [ ] **27a. Project/opportunity sync** — Sync capture pipeline with Unanet projects
- [ ] **27b. Resource planning data** — Pull labor categories and rates from Unanet
- [ ] **27c. Financial data sync** — Connect contract financials between platforms

#### 28. Smart Workflows / Automation Rules
**Gap**: Govly has rule-based workflow automation. GovDash has automated teammate evaluation.
- [ ] **28a. Workflow rule engine** — If-then rules for opportunity routing (e.g., "If NAICS 541512 AND value > $5M, assign to senior capture manager")
- [ ] **28b. Automated stage transitions** — Auto-advance pipeline stage when conditions are met
- [ ] **28c. Notification rules** — Custom notification triggers based on opportunity attributes
- [ ] **28d. Teammate evaluation** — Auto-evaluate and recommend teaming partners based on requirements

#### 29. Data Privacy & Model Training Guarantees
**Gap**: GovDash explicitly states data is never used for model training. We don't.
- [ ] **29a. Data usage policy page** — Create a public-facing page guaranteeing data isolation
- [ ] **29b. Technical implementation** — Ensure Gemini API calls use ephemeral mode / no training data retention
- [ ] **29c. SOC 2 preparation** — Begin SOC 2 Type II audit preparation
- [ ] **29d. Privacy controls UI** — Give users visibility into how their data is used

#### 30. Mobile Experience
**Gap**: Neither competitor has a native mobile app, but responsive web is expected.
- [ ] **30a. Responsive dashboard** — Ensure all dashboard views work on tablet/mobile
- [ ] **30b. Push notifications** — Browser push notifications for alerts and opportunity changes
- [ ] **30c. Mobile-optimized Dash** — Chat interface optimized for mobile

#### 31. Real-Time Collaborative Editing
**Gap**: GovDash has real-time collaborative editing in their section editor.
- [ ] **31a. WebSocket collaboration server** — Implement CRDT or OT-based real-time editing
- [ ] **31b. Cursor presence** — Show other users' cursors in the document
- [ ] **31c. Conflict resolution** — Handle simultaneous edits gracefully

#### 32. Template Marketplace
**Gap**: Currently scaffolded but not implemented.
- [ ] **32a. Proposal templates** — Pre-built proposal structures by contract type (IT services, construction, professional services)
- [ ] **32b. Compliance matrix templates** — Pre-built matrices for common contract vehicles
- [ ] **32c. Community templates** — Allow users to share and discover templates

#### 33. Dynamic Custom Reports
**Gap**: GovDash has customizable reporting across all modules.
- [ ] **33a. Report builder** — Drag-and-drop report builder with field selection
- [ ] **33b. Saved report views** — Save and share custom report configurations
- [ ] **33c. Scheduled report delivery** — Email reports on a schedule

#### 34. Onboarding & Customer Success
**Gap**: Both competitors emphasize responsive support and onboarding.
- [ ] **34a. In-app onboarding flow** — Guided setup wizard for new accounts
- [ ] **34b. Interactive tutorials** — Feature-specific walkthroughs
- [ ] **34c. Knowledge base / help center** — Self-serve documentation and guides
- [ ] **34d. In-app chat support** — Live chat or chatbot for quick questions

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

*This document should be reviewed monthly and updated as features ship and competitive landscape evolves.*
