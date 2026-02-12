# Enhancement Plan: Closing All Competitive Gaps

> **Created**: February 12, 2026
> **Goal**: Close every identified gap vs GovDash, Govly, GovSignals, and emerging competitors
> **Approach**: Honest audit → fix stubs → build missing → quality-tune → ship

---

## Audit Summary (What's Real vs Smoke)

| Feature | Status | Gap |
|---------|--------|-----|
| Data Sources (7 of 11) | STUB (hardcoded samples) | Replace stubs with real API clients |
| Email Ingestion | STUB (no IMAP client) | Build actual IMAP fetch + parse pipeline |
| Notifications/Email | STUB (logs only) | Wire up Resend/SendGrid for real delivery |
| Semantic Search | PARTIAL (hash-based vectors) | Replace with Gemini text-embedding-004 + pgvector |
| Track Changes | NOT BUILT | Build TipTap suggestion/track-changes mode |
| Market Signals | PARTIAL (no auto-ingestion) | Build RSS/news feed ingestion pipeline |
| SharePoint Sync | REAL | ✅ No action |
| SCIM Provisioning | REAL | ✅ No action |
| Word Add-in | REAL (not published) | Prep AppSource manifest + submission |
| Graphics Generation | REAL (Mermaid only) | ✅ No action |
| AI Draft Quality | REAL (sophisticated) | Quality benchmark against GovDash claims |
| FedRAMP/CMMC | NOT STARTED (readiness tracker only) | Create public timeline + start assessment |
| SOC 2 | NOT STARTED | Begin Type II prep |
| Data Privacy Page | NOT BUILT | Publish public guarantee page |
| Shared Team Inboxes | NOT BUILT | Build email inbox per workspace |
| Canada/International | NOT BUILT | Add buyandsell.gc.ca provider |

---

## Phase 1: Fix the Stubs (Make Existing Features Real)

### 1.1 Replace Stub Data Source Providers
**Gap**: 7 of 11 data sources return hardcoded data
**Files**: `backend/app/services/data_sources/`

| Provider | Current | Target |
|----------|---------|--------|
| SLED BidNet | Hardcoded 3 opps | BidNet Direct API or scrape |
| DIBBS | Hardcoded 2 opps | DLA DIBBS public search API |
| GSA MAS | Static 1 opp | SAM.gov entity API for MAS |
| CIO-SP3 | Static 1 opp | NIH NITAAC API |
| ITES | Static 1 opp | Army CHESS portal API |
| OASIS | Static 1 opp | GSA OASIS SB portal |
| SEWP V | Partial | Validate SEWP endpoint URLs |

**Deliverable**: Each provider returns real, live opportunity data.

### 1.2 Wire Up Email Delivery (Notifications)
**Gap**: `EmailService.send_email()` just logs
**File**: `backend/app/services/notifications.py`

- [ ] Add Resend SDK (`resend` package) — simple, modern, cheap
- [ ] Implement `send_email()` with Resend API
- [ ] Wire up: opportunity alerts, digest emails, review notifications, invite emails
- [ ] Add `RESEND_API_KEY` to config

### 1.3 Build Email Ingestion (IMAP Client)
**Gap**: No IMAP client, mock test connection
**File**: `backend/app/services/email_ingest_service.py` (new)

- [ ] Build IMAP client using `aioimaplib`
- [ ] Parse forwarded RFP emails → extract attachments
- [ ] Auto-create RFP records from parsed solicitations
- [ ] Wire to Celery periodic task for polling
- [ ] Encrypt IMAP passwords at rest (AES via secrets vault)

### 1.4 Upgrade Semantic Search to Real Embeddings
**Gap**: Hash-based 128-dim vectors, not true semantic
**Files**: `backend/app/services/embedding_service.py`

- [ ] Replace hash function with `text-embedding-004` Gemini API calls
- [ ] Add pgvector extension to PostgreSQL
- [ ] Migrate `DocumentEmbedding.embedding_json` to `vector(768)` column
- [ ] Rebuild embedding pipeline for all existing documents
- [ ] Update search API to use pgvector `<=>` cosine distance

---

## Phase 2: Build Missing Features

### 2.1 Track Changes / Suggestions Mode (TipTap)
**Gap**: NOT BUILT — editors can't see AI-generated vs human-edited content
**Target**: TipTap `@tiptap/suggestion` or custom marks

- [ ] Add `ai_generated` mark to TipTap schema (highlights AI content)
- [ ] When AI generates content, wrap in `ai_generated` mark
- [ ] Add "Accept / Reject" UI for AI suggestions
- [ ] Add "Show Changes" toggle to editor toolbar
- [ ] Store suggestion history in `ProposalSectionVersion`

### 2.2 Shared Team Inboxes
**Gap**: Govly has this, we don't
**Target**: Per-workspace shared inbox for opportunity notifications

- [ ] Add `WorkspaceInbox` model (workspace_id, messages)
- [ ] Add `InboxMessage` model (sender, subject, body, attachments, read_by)
- [ ] Route: `POST /collaboration/workspaces/{id}/inbox`
- [ ] Route: `GET /collaboration/workspaces/{id}/inbox`
- [ ] Frontend inbox UI in workspace view
- [ ] WebSocket notifications for new messages

### 2.3 Market Signal Auto-Ingestion
**Gap**: CRUD works but no automated data feed
**Target**: RSS/news feed ingestion for gov contracting news

- [ ] Build RSS feed parser service (`feedparser` library)
- [ ] Curate initial feed list (FedBizOpps blog, DefenseOne, FCW, GovExec, NextGov)
- [ ] Celery periodic task: poll feeds every 6 hours
- [ ] AI classification: score relevance by user's NAICS/agency interests
- [ ] Wire to notification system for daily digest

### 2.4 Canada / International Coverage
**Gap**: Govly has Canada. We don't.

- [ ] Add `buyandsell_gc` data source provider
- [ ] Parse buyandsell.gc.ca open data API
- [ ] Add multi-currency support to opportunity model (CAD)
- [ ] Add country/province filtering to search
- [ ] Add `grants_gc` for Canadian grants

### 2.5 Data Privacy & Security Posture

#### Public Data Privacy Page
- [ ] Add `/privacy/ai-data` public page
- [ ] Content: "Your data is never used to train AI models"
- [ ] Document Gemini API ephemeral mode usage
- [ ] Link from settings, footer, and onboarding

#### SOC 2 Type II Prep
- [ ] Document security controls inventory
- [ ] Map controls to SOC 2 Trust Service Criteria
- [ ] Identify gaps in logging, access control, change management
- [ ] Create remediation plan

#### FedRAMP/CMMC Timeline
- [ ] Publish public timeline on `/compliance` page
- [ ] Q2 2026: Complete SSP (System Security Plan)
- [ ] Q3 2026: Engage 3PAO for readiness assessment
- [ ] Q4 2026: Submit FedRAMP Moderate package
- [ ] Parallel: CMMC Level 2 self-assessment

---

## Phase 3: Quality & Distribution

### 3.1 AI Draft Quality Benchmarking
**Goal**: Verify our drafts match GovDash's "pink-team-ready" claim

- [ ] Create 5 benchmark RFPs (IT services, construction, professional services, R&D, logistics)
- [ ] Generate proposals for each using our pipeline
- [ ] Score against pink-team criteria: compliance coverage, specificity, citation density, readability
- [ ] Compare output quality to GovDash case study claims
- [ ] Tune prompts based on findings

### 3.2 Word Add-in AppSource Submission
**Gap**: Code exists, not published to marketplace

- [ ] Create AppSource developer account
- [ ] Build manifest.xml with proper metadata
- [ ] Screenshot package for marketplace listing
- [ ] Submit to Microsoft Partner Center
- [ ] Marketing page at `/integrations/word`

### 3.3 Salesforce AppExchange Submission
**Gap**: Integration works, not listed

- [ ] Create ISV partner account
- [ ] Package as Salesforce Connected App
- [ ] Security review submission
- [ ] Create listing with screenshots + video
- [ ] Marketing page at `/integrations/salesforce`

---

## Execution Order

| Session | Work | Impact |
|---------|------|--------|
| **S1** | 1.2 Email delivery (Resend) + 1.4 Semantic search (pgvector) | Unblocks notifications + search quality |
| **S2** | 1.1 Replace stub data sources (7 providers) | Data credibility — biggest Govly gap |
| **S3** | 2.1 Track changes + 2.5a Privacy page | Editor parity + trust signal |
| **S4** | 1.3 Email ingestion (IMAP) + 2.3 Market signals | Automation features |
| **S5** | 2.2 Shared team inboxes + 2.4 Canada | Collaboration + international |
| **S6** | 3.1 AI quality benchmark + 3.2 Word AppSource + 3.3 Salesforce AppExchange | Distribution + quality proof |
| **S7** | 2.5b-d SOC 2 / FedRAMP / CMMC timeline | Enterprise trust |

---

## Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| Real data sources (not stubs) | 4/11 | 11/11 |
| Email delivery | Mock/log only | Real delivery via Resend |
| Semantic search | Hash-based | Gemini embeddings + pgvector |
| Track changes | Not built | Full suggestion mode |
| Word Add-in distribution | Code only | On AppSource |
| Data privacy page | None | Public guarantee |
| Notification types working | 0 | 5+ (alerts, digests, invites, reviews, signals) |
| FedRAMP status | Readiness tracker | Public timeline + SSP started |

---

*Each session ends with: verification → commit → push. No exceptions.*
