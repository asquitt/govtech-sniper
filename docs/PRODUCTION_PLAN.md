# GovTech Sniper: Production Enhancement Plan

## Competitive Intelligence Summary

### Market Context (2025-2026)
- RFP automation AI market: **$1.1B → $2.43B by 2029** (21.7% CAGR)
- 24% of GovCon firms now have enterprise-wide AI policies (doubled from 12% in 2024)
- AI-native app spend up **400%** for large enterprises
- FedRAMP + CMMC Level 2 are now **table stakes**, not differentiators

### Competitor Snapshot

| | GovDash | Govly | Vultron | GovTech Sniper (Us) |
|---|---------|-------|---------|---------------------|
| **Funding** | $40M (Series B) | $13.1M (Series A) | $22M (Series A) | Bootstrapped |
| **Customers** | ~200 | ~200 | 400+ | Pre-launch |
| **Focus** | End-to-end lifecycle | Market network + discovery | AI proposal writing | Full lifecycle + AI |
| **AI Model** | OpenAI (GPT-4o) | Proprietary | Licensed winning proposals | Google Gemini |
| **Pricing** | Custom (enterprise) | $3K-15K/yr | Custom (enterprise) | TBD |
| **Strength** | Breadth of features | Partner network | Proposal quality | Speed + modern stack |

### What Customers Love Most

**GovDash customers rave about:**
1. End-to-end platform (no tool sprawl) — "transform a week into a few hours"
2. Microsoft Word/SharePoint integration — called a "game-changer"
3. Compliance matrix automation — nothing falls through the cracks
4. Customer service — "available 7 days a week, in minutes"
5. Results — $5B+ in customer contract wins in 2025

**Govly customers rave about:**
1. Ease of use — simple UI that teams pick up quickly
2. Partner network — primes and subs collaborate on opportunities
3. Centralized RFQ management — "saves countless hours"
4. Broader data sources — 30+ GWACs beyond SAM.gov
5. Customer-centric development — actually listens to product suggestions

**Vultron customers rave about:**
1. Draft quality — "60% draft in minutes, more time editing vs writing"
2. Time savings — 72% reduction in drafting time, 2+ days/week saved per user
3. Licensed winning proposal data — trained on actual winning federal proposals
4. Compliance accuracy — 95%+ compliance rate
5. Word add-in — works where proposal teams actually work

### Key Gaps in Our Platform (vs. Competitors)

| Gap | GovDash Has | Govly Has | Vultron Has | Priority |
|-----|-------------|-----------|-------------|----------|
| Dash-style AI assistant chat | Yes | Yes | Yes | **P0** |
| Word add-in (functional, not scaffold) | Yes | No | Yes | **P0** |
| Opportunity discovery beyond SAM.gov | Yes (eBuy, SLED) | Yes (30+ GWACs) | No | **P0** |
| Bid/no-bid decision engine | Partial | No | Partial | **P0** |
| Win probability scoring | Implied | No | Yes | **P1** |
| Partner network/marketplace | No | Yes | No | **P1** |
| Licensed/trained proposal data | Implied | No | Yes | **P1** |
| Mobile experience (PWA) | No | No | No | **P1** |
| SSO (Okta, Azure AD) | Yes (Entra) | No | Yes | **P1** |
| FedRAMP path | Yes (Moderate) | No | Yes (SOC2) | **P2** |
| Stripe billing integration | Unknown | Yes | Unknown | **P1** |

---

## Enhancement Plan: 8-Week Sprint Cycles

### Phase 1: AI Core Superiority (Weeks 1-2)
**Goal: Make our AI the best in market. This is our primary differentiator.**

#### 1.1 Dash AI Chat Assistant (P0)
**What competitors have:** GovDash's "Dash" is an always-available LLM assistant that works across the entire platform — answers questions about opportunities, generates content, searches documents, and provides agency insights.

**What we build:**
- [ ] Full-page `/dash` chat interface with conversation history
- [ ] Context-aware: automatically pulls in current RFP, proposal, or capture plan
- [ ] Document Q&A: "What are the key requirements in this RFP?"
- [ ] Cross-entity search: "Show me all proposals for DoD from last 6 months"
- [ ] Content generation: "Draft an executive summary for this proposal"
- [ ] Streaming responses via SSE for real-time feel
- [ ] Conversation persistence (save/load chat threads)
- [ ] Suggested prompts based on current context

**Backend:**
- `POST /api/v1/dash/chat` — streaming chat endpoint
- `GET /api/v1/dash/conversations` — list saved conversations
- `DashService` with Gemini 1.5 Pro, context injection from active entities
- Tool-use pattern: Dash can call internal APIs (search, analyze, generate)

**Frontend:**
- Chat panel component (reusable as sidebar + full page)
- Message bubbles with markdown rendering
- File/document attachment in chat
- Typing indicator + streaming text display

#### 1.2 Agentic AI Proposal Generation (P0)
**Why:** Vultron's #1 advantage is "60% draft in minutes." Our generation exists but needs to be dramatically faster and higher quality.

**Enhancements:**
- [ ] Multi-section batch generation (generate entire proposal in one action)
- [ ] Citation-backed output with `[[Source: document.pdf, Page X]]` verification
- [ ] Compliance-aware generation: auto-check each section against compliance matrix
- [ ] Tone/style matching from uploaded past winning proposals
- [ ] "Rewrite" and "Expand" quick actions on any paragraph
- [ ] Side-by-side: generated draft vs. RFP requirement for verification
- [ ] Progress tracking: show generation status per section in real-time

#### 1.3 Smart Compliance Matrix (P0)
**Why:** GovDash and Vultron both cite compliance automation as their top value prop. Ours exists but needs to be bulletproof.

**Enhancements:**
- [ ] Cross-reference Sections L + M + C + PWS simultaneously (not sequentially)
- [ ] Auto-detect implied requirements (not just explicit ones)
- [ ] Compliance confidence score per requirement (high/medium/low)
- [ ] Gap analysis: highlight requirements with no matching content in knowledge base
- [ ] Amendment tracking: when RFP amendments arrive, auto-diff the compliance matrix
- [ ] Export compliance matrix as standalone Excel/DOCX

---

### Phase 2: Microsoft Integration Excellence (Weeks 3-4)
**Goal: Ship a production Word add-in. This is the #1 feature GovDash customers love.**

#### 2.1 Microsoft Word Add-in (P0)
**Current state:** Scaffold only (session tracking, event logging). Not functional.

**What we build:**
- [ ] Office.js task pane add-in with authentication
- [ ] "Generate Section" button: select a section → AI generates content → inserts into Word
- [ ] Compliance checker: highlight non-compliant paragraphs in Word
- [ ] Knowledge base search: find relevant past performance without leaving Word
- [ ] Section sync: push/pull sections between Word and web app
- [ ] Template insertion: insert boilerplate sections from template library
- [ ] Real-time status: show which sections are complete/pending in task pane

**Technical:**
- Office Add-in manifest (XML) for Word Desktop + Word Online
- React-based task pane using our existing component library
- REST API calls to existing backend endpoints
- MSAL authentication for Microsoft accounts

#### 2.2 SharePoint Deep Integration (P1)
**Current state:** Basic file browser and export. Needs bi-directional sync.

**Enhancements:**
- [ ] Auto-sync proposal documents to designated SharePoint folder
- [ ] Watch SharePoint folders for new RFP uploads → auto-ingest
- [ ] Version history sync between app and SharePoint
- [ ] Proposal review comments synced with SharePoint annotations
- [ ] Team permissions inherited from SharePoint groups

---

### Phase 3: Opportunity Discovery Engine (Weeks 5-6)
**Goal: Match Govly's breadth of opportunity sources. Go beyond SAM.gov.**

#### 3.1 Multi-Source Opportunity Ingestion (P0)
**Why:** Govly's main differentiator is 30+ GWACs. GovDash added GSA eBuy and SLED. We only have SAM.gov + FPDS.

**New data sources:**
- [ ] **GSA eBuy** — GSA's Request for Quote platform
- [ ] **GovWin IQ API** (if available) or scraping alternative
- [ ] **SEWP V** — NASA's IT procurement vehicle
- [ ] **ITES-SW2** — Army IT Enterprise Solutions
- [ ] **State/Local/Education (SLED)** — Start with top 10 states by GovCon spend
- [ ] **Grants.gov** — Federal grants for applicable customers
- [ ] **FedBizOpps archive** — Historical opportunity data for market intelligence

**Architecture:**
- `DataProvider` abstract base class (already have pattern from FPDS/Canada)
- Each source gets its own provider in `backend/app/services/data_providers/`
- Unified opportunity model with `source_type` field
- Deduplication across sources (same opportunity on SAM.gov and eBuy)
- Configurable per-user: which sources to monitor

#### 3.2 Intelligent Opportunity Matching (P0)
**Why:** GovDash's "Bid Match" and Govly's semantic search both auto-surface relevant opportunities.

**What we build:**
- [ ] Company capability profile (NAICS, past performance, certifications, clearances)
- [ ] AI matching score: how well does this opportunity fit our capabilities?
- [ ] Daily digest email: "5 new opportunities matching your profile"
- [ ] Similar opportunities: "Contractors who bid on X also looked at Y"
- [ ] Trending opportunities: show what similar-sized contractors are pursuing
- [ ] Smart filters: save complex multi-criteria searches with alerts

#### 3.3 Bid/No-Bid Decision Engine (P0)
**Why:** This is the most-requested feature in GovCon forums. Currently manual at most firms.

**What we build:**
- [ ] Scoring framework: 15-20 weighted criteria (past performance fit, competitive landscape, margin potential, resource availability, strategic alignment)
- [ ] AI-assisted scoring: Gemini analyzes RFP against company profile
- [ ] Win probability estimate based on historical data
- [ ] Go/No-Go recommendation with confidence level
- [ ] Decision audit trail for compliance
- [ ] Team voting: multiple stakeholders score independently, then compare
- [ ] Dashboard: bid decision history with win/loss correlation

---

### Phase 4: Collaboration & Team Productivity (Weeks 7-8)
**Goal: Make team collaboration a competitive advantage.**

#### 4.1 Color Team Review Workflow (P1)
**Current state:** Review model exists but needs workflow polish.

**Enhancements:**
- [ ] Pink Team: initial draft review with structured feedback form
- [ ] Red Team: compliance-focused review with checklist
- [ ] Gold Team: executive review with go/no-go decision
- [ ] Review assignment with due dates and reminders
- [ ] Review dashboard: see all active reviews across proposals
- [ ] Comment resolution workflow: assign → address → verify → close
- [ ] Review scoring summary: automated aggregation of reviewer scores
- [ ] Email notifications for review assignments and due dates

#### 4.2 Real-Time Collaboration Polish (P1)
**Current state:** Presence and locking work. Needs Google Docs-level UX.

**Enhancements:**
- [ ] Cursor positions visible to other editors (colored cursors)
- [ ] Inline commenting with @mentions
- [ ] Comment threads with reply chains
- [ ] Suggestion mode (like Word's Track Changes)
- [ ] Section assignment: "This section is assigned to Sarah"
- [ ] Activity feed: "John edited Executive Summary 5 min ago"
- [ ] Conflict resolution: merge changes when lock expires

#### 4.3 Teaming & Partner Network (P1)
**Why:** Govly's #1 differentiator. No other competitor has a partner marketplace.

**Enhancements:**
- [ ] Public company profiles with capabilities, NAICS, clearances, set-asides
- [ ] Partner search: "Find 8(a) small businesses with cybersecurity experience"
- [ ] Teaming request workflow: request → negotiate → accept → NDA tracking
- [ ] Capability gap analysis: "This RFP requires X, you lack it, here are partners who have it"
- [ ] Past teaming history and performance ratings
- [ ] Secure document sharing with partners (NDA-gated)
- [ ] Joint proposal workspace for prime + sub collaboration

---

### Phase 5: Revenue & Billing (Weeks 9-10)
**Goal: Ship self-service billing. Required for launch.**

#### 5.1 Stripe Billing Integration (P0)
- [ ] Stripe subscription management (create, update, cancel)
- [ ] Three tiers: Starter ($99/user/mo), Professional ($199/user/mo), Enterprise (custom)
- [ ] Usage-based add-ons: AI generation credits, additional data sources
- [ ] Annual discount (20% off)
- [ ] Free trial: 14 days, no credit card required
- [ ] Billing portal: invoices, payment methods, usage dashboard
- [ ] Webhook handling: payment success, failure, subscription changes
- [ ] Feature gating enforcement based on active subscription tier

#### 5.2 Pricing Strategy
**Based on market research:**

| Tier | Price | Target | Includes |
|------|-------|--------|----------|
| **Starter** | $99/user/mo | Solo BD managers, small firms | SAM.gov, 5 proposals/mo, basic AI, DOCX export |
| **Professional** | $199/user/mo | Growing contractors | All sources, unlimited proposals, full AI, Word add-in, collaboration |
| **Enterprise** | Custom | Large contractors | SSO/SCIM, SharePoint sync, Salesforce, dedicated support, SLA |

**Justification:** Vultron charges premium ($200+), GovDash is custom-only. Our Starter tier undercuts both and targets the underserved small business segment that Govly identified as their sweet spot ($3K/yr for 5 users = $50/user/mo).

---

### Phase 6: Intelligence & Analytics (Weeks 11-12)
**Goal: Provide market intelligence that drives strategic decisions.**

#### 6.1 Win/Loss Analysis (P1)
- [ ] Post-award debrief tracking: what the agency said about our proposal
- [ ] Win theme analysis: which themes correlate with wins?
- [ ] Competitor tracking: who are we losing to and why?
- [ ] Historical win rate by agency, NAICS, contract size
- [ ] Proposal quality correlation: review scores vs. win rate
- [ ] Recommendation engine: "Proposals with 3+ past performance citations win 2x more"

#### 6.2 Budget Intelligence Enhancement (P1)
- [ ] Agency budget tracking with year-over-year trends
- [ ] Spending forecast by NAICS code
- [ ] Contract vehicle utilization rates
- [ ] "Budget season" alerts: when agencies are most likely to release RFPs
- [ ] Competitor award analysis: who's winning what, at what price

#### 6.3 Pipeline Analytics Dashboard (P1)
- [ ] Weighted pipeline value (probability × contract value)
- [ ] Conversion funnel: opportunities → captures → proposals → wins
- [ ] Resource allocation view: team capacity vs. proposal workload
- [ ] Revenue forecasting: projected wins by quarter
- [ ] KPI benchmarks: your metrics vs. industry averages

---

### Phase 7: Enterprise Readiness (Weeks 13-14)
**Goal: Meet enterprise requirements for large contractor sales.**

#### 7.1 SSO Enhancement (P0)
**Current state:** SCIM exists. Need production SSO.

- [ ] Okta SAML/OIDC integration
- [ ] Microsoft Entra ID (Azure AD) SSO
- [ ] Google Workspace SSO
- [ ] JIT (Just-In-Time) user provisioning
- [ ] Group-based role mapping
- [ ] SSO-only enforcement (disable password login for org)

#### 7.2 Audit & Compliance (P1)
- [ ] SOC 2 Type II evidence collection automation
- [ ] Data retention policies with automated enforcement
- [ ] ITAR/EAR compliance controls
- [ ] CUI marking and handling workflow
- [ ] Data export for compliance audits (all user data, all actions)
- [ ] IP allowlisting for enterprise accounts

#### 7.3 Admin Console (P1)
- [ ] Organization-level admin dashboard
- [ ] User management: invite, deactivate, role assignment
- [ ] Usage analytics: who's using what, how often
- [ ] Billing management for admins
- [ ] Custom branding (logo, colors) for enterprise
- [ ] Data governance: who can export, who can share

---

### Phase 8: Polish & Delight (Weeks 15-16)
**Goal: The 20% that makes users love us.**

#### 8.1 Proposal Templates Library (P1)
- [ ] Pre-built templates for common RFP types (IDIQ, T&M, FFP, CPFF)
- [ ] Agency-specific templates (DoD, HHS, DHS, NASA)
- [ ] Community template marketplace (share and rate templates)
- [ ] Template auto-selection based on RFP analysis
- [ ] One-click proposal setup from template

#### 8.2 Knowledge Base Intelligence (P1)
- [ ] Auto-tag documents by topic, agency, contract type
- [ ] "Content freshness" indicators — flag outdated past performance
- [ ] Smart boilerplate: adapt language to match RFP tone/requirements
- [ ] Duplicate content detection across knowledge base
- [ ] Content gap analysis: "You have no past performance for cybersecurity"

#### 8.3 Mobile Experience (P1)
**Current state:** PWA mobile nav exists.

- [ ] Mobile-optimized review approval workflow
- [ ] Push notifications for deadlines, review assignments, new opportunities
- [ ] Quick proposal status check
- [ ] Mobile-friendly Dash AI chat
- [ ] Offline mode for document reading

#### 8.4 Notifications & Alerts System (P1)
- [ ] Configurable notification preferences per user
- [ ] Email digest options: real-time, daily, weekly
- [ ] In-app notification center with read/unread
- [ ] Slack integration for team notifications
- [ ] Critical alerts: deadline approaching, review overdue, RFP amendment
- [ ] Smart quiet hours: no notifications outside work hours

#### 8.5 Onboarding & Activation (P1)
**Why:** GovDash's structured 5-session onboarding is praised. Self-serve needs to be just as good.

- [ ] Interactive product tour (not just tooltips)
- [ ] "First proposal" guided wizard: upload RFP → analyze → draft → export
- [ ] Sample data: pre-loaded demo RFP + knowledge base for sandbox exploration
- [ ] Video library: 2-minute feature walkthroughs
- [ ] Progress tracker: "Complete 5 actions to unlock full potential"
- [ ] In-app chat support (Intercom or similar)

---

## Priority Matrix

### P0 — Must Ship Before Launch (Weeks 1-10)
| # | Enhancement | Competitor Parity | Est. Effort |
|---|-------------|-------------------|-------------|
| 1 | Dash AI Chat Assistant | GovDash, Vultron | 2 weeks |
| 2 | Agentic multi-section proposal generation | Vultron | 1 week |
| 3 | Smart compliance matrix (cross-reference + gaps) | GovDash, Vultron | 1 week |
| 4 | Word add-in (functional) | GovDash, Vultron | 2 weeks |
| 5 | Multi-source opportunity ingestion (GSA eBuy, SEWP) | GovDash, Govly | 2 weeks |
| 6 | Intelligent opportunity matching + alerts | GovDash, Govly | 1 week |
| 7 | Bid/No-Bid decision engine | Market demand | 1 week |
| 8 | Stripe billing integration | Launch requirement | 1 week |
| 9 | SSO (Okta + Azure AD) | Enterprise requirement | 1 week |

### P1 — Ship Within 60 Days of Launch
| # | Enhancement | Competitive Edge | Est. Effort |
|---|-------------|-----------------|-------------|
| 10 | Color team review workflow | GovDash | 1 week |
| 11 | Real-time collaboration polish | Differentiation | 1 week |
| 12 | Teaming & partner network | Govly | 2 weeks |
| 13 | Win/Loss analysis | Differentiation | 1 week |
| 14 | Pipeline analytics dashboard | GovDash | 1 week |
| 15 | Budget intelligence enhancement | GovDash | 1 week |
| 16 | SharePoint deep integration | GovDash | 1 week |
| 17 | Proposal template library | All competitors | 1 week |
| 18 | Knowledge base intelligence | Vultron | 1 week |
| 19 | Mobile experience | Differentiation | 1 week |
| 20 | Notification & alerts system | Table stakes | 1 week |
| 21 | Onboarding & activation | GovDash | 1 week |
| 22 | Admin console | Enterprise | 1 week |
| 23 | Audit & compliance (SOC 2 prep) | Enterprise | 1 week |

### P2 — Ship Within 90 Days (Differentiation)
| # | Enhancement | Strategic Value |
|---|-------------|----------------|
| 24 | SLED opportunity sources (state/local) | Market expansion |
| 25 | Grants.gov integration | Adjacent market |
| 26 | Post-award transition tools | Unique differentiator |
| 27 | SME knowledge extraction (voice-to-text) | Vultron gap |
| 28 | Custom AI model fine-tuning on customer data | Competitive moat |
| 29 | FedRAMP authorization path | Enterprise requirement |
| 30 | Slack integration | Workflow integration |
| 31 | API marketplace for third-party integrations | Platform play |

---

## Competitive Positioning Strategy

### Our Differentiation (What We Do That Others Don't)

1. **Speed + Modern Stack**: Next.js + FastAPI + Gemini = faster iteration than legacy platforms
2. **Transparent Pricing**: Public pricing tiers vs. competitors' "contact sales" gates
3. **Small Business First**: $99/user tier undercuts every competitor targeting SMBs
4. **Full Lifecycle in One**: Capture → Proposal → Contract (like GovDash) + Partner Network (like Govly) + AI Quality (like Vultron)
5. **Self-Serve Onboarding**: No 5-week implementation required
6. **Google Gemini**: Context caching gives us cost advantage on AI generation

### Messaging Framework

**Tagline:** "Win more government contracts. Faster."

**For small businesses:** "Enterprise proposal quality without the enterprise price tag."

**For mid-market:** "The only platform that combines AI proposal generation, opportunity discovery, and contract management — with pricing you can actually see."

**Against GovDash:** "Same capabilities, transparent pricing, faster onboarding."

**Against Govly:** "Everything Govly offers for discovery, plus AI-powered proposal generation and contract management."

**Against Vultron:** "Vultron-quality proposals, plus opportunity discovery and contract management."

---

## Success Metrics

### Launch Targets (Month 1)
- 50 free trial signups
- 10 paid conversions
- 5 proposals generated end-to-end
- <2 min time to first value (RFP upload → compliance matrix)

### Growth Targets (Month 3)
- 200 free trial signups
- 40 paid customers
- $15K MRR
- NPS > 50
- <24hr proposal draft turnaround

### Scale Targets (Month 6)
- 500 trial signups
- 100 paid customers
- $50K MRR
- 3 enterprise contracts ($1K+/mo each)
- 1 customer win attributed to platform

---

## Technical Debt to Address Pre-Launch

| Issue | Impact | Fix |
|-------|--------|-----|
| ~20 pre-existing TS errors in test files | CI/CD reliability | Fix or suppress with `@ts-expect-error` |
| Agent framework is scaffold-only | Dash AI depends on it | Implement functional agent loop |
| Word add-in is scaffold-only | P0 feature gap | Full implementation needed |
| Canada data provider is stub | Data source credibility | Either implement or remove |
| No rate limiting on public endpoints | Security vulnerability | Add FastAPI rate limiter middleware |
| No email sending service | Notifications blocked | Integrate SendGrid or AWS SES |
| No file upload size limits | DoS risk | Add multipart upload limits |
| No automated database backups | Data loss risk | Configure pg_dump cron + S3 |

---

## Implementation Order (Recommended)

```
Week 1-2:   Dash AI Chat + Agentic Generation + Compliance Matrix
Week 3-4:   Word Add-in + SharePoint Deep Sync
Week 5-6:   Multi-Source Ingestion + Opportunity Matching + Bid/No-Bid
Week 7-8:   Stripe Billing + SSO + Admin Console
Week 9-10:  Color Reviews + Collaboration Polish + Notifications
Week 11-12: Analytics Dashboard + Win/Loss + Budget Intel
Week 13-14: Partner Network + Template Library + Knowledge Base Intel
Week 15-16: Mobile Polish + Onboarding + Launch Prep
```

Each 2-week sprint delivers a shippable increment. No sprint depends on a future sprint. Every sprint ends with working, tested, deployed code.

---

*Last updated: 2026-02-07*
*Based on competitive analysis of GovDash ($40M raised), Govly ($13.1M raised), and Vultron ($22M raised)*
