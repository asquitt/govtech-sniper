# GovTech Sniper

**AI-Powered Government Contract Proposal Automation**

GovTech Sniper is a B2B SaaS platform that automates the process of finding, analyzing, and writing proposals for US Government contracts. It leverages Google Gemini 1.5 Pro's massive context window to generate compliant proposal responses with strict citation tracking.

---

## Overview

Government contractors spend weeks responding to a single RFP. GovTech Sniper reduces that to hours. The platform ingests opportunities from SAM.gov, qualifies them against your company profile, extracts compliance requirements, and generates citation-backed proposal sections using your knowledge base.

---

## Core Capabilities

### SAM.gov Integration & Data Ingestion
- Automated opportunity ingestion from SAM.gov, FPDS, and USAspending
- Scheduled scanning via Celery Beat for new opportunities
- NAICS code, set-aside, and keyword filtering
- Versioned opportunity snapshots with change tracking
- Attachment downloads with PDF text extraction
- Email-based RFP ingestion with automatic parsing
- Configurable data source feeds with health monitoring

### Qualification Engine ("The Killer Filter")
- AI-powered screening using Gemini 1.5 Flash
- Rule-based pre-filtering: NAICS codes, clearances, set-asides
- 0-100 qualification scoring with reasoning
- Eliminates unwinnable opportunities before you invest time

### Deep Read Analysis
- Full RFP parsing with Gemini 1.5 Pro (1M token context)
- Automatic compliance matrix extraction
- Requirement categorization: Mandatory, Evaluated, Optional
- Section-level tagging (Technical, Management, Past Performance)
- Compliance gap identification

### AI Proposal Writer
- RAG-powered section generation with Gemini Context Caching
- Strict citation enforcement: `[[Source: filename.pdf, Page X]]`
- Knowledge base documents cached for repeated use
- Per-section generation with word count tracking
- TipTap rich text editor with real-time collaboration
- Annotated outline generation from compliance matrix
- Focus document selection for targeted generation
- Evidence linking to past performance

### Citation Engine
- Automatic source tracking and verification
- Page-level citation parsing and validation
- Document usage analytics (times cited, last cited)

### Capture Management
- Full capture pipeline from identification to submission
- AI-powered and manual bid/no-bid scoring with scorecards
- Gate reviews for stage progression
- Custom fields and win probability scoring
- Team assignments and contact management
- Budget intelligence and competitive landscape tracking
- Teaming partner directory with NDA tracking and capability gap analysis
- Pipeline timeline visualization (Gantt charts)

### Contract Management
- Contract lifecycle tracking with hierarchy support
- Contract Line Items (CLINs) management
- Deliverable tracking with status monitoring
- Modification and change order management
- Task breakdown and assignment
- Status report generation
- CPARS performance data integration

### Color Team Reviews
- Pink, Red, and Gold team review workflows
- Reviewer assignment with role-based access
- Comment tracking with severity levels (Critical, Major, Minor, Suggestion)
- Compliance checklists with configurable templates
- Overall scoring and go/no-go decisions

### Collaboration & Workspaces
- Multi-user shared workspaces with role-based access (Viewer, Contributor, Admin)
- Workspace invitations and member management
- Shared data permissions and governance
- Team inbox for workspace messaging
- Compliance digest scheduling
- Real-time updates via WebSocket

### Intelligence & Analytics
- Market signal tracking and opportunity intelligence
- Pipeline forecasting with win probability
- Revenue pipeline visualization and forecasting
- Competitive benchmarking
- Win/loss analysis
- Custom report builder with saved configurations
- Resource allocation tracking

### Workflow Automation
- Trigger-based rules (RFP created, stage changed, deadline approaching, score threshold)
- Configurable conditions and actions
- Execution history and audit trail

### Notification System
- Multi-channel delivery: email, in-app, Slack, webhook
- Deadline reminders and RFP match alerts
- Team mention and invite notifications
- Configurable notification preferences

### Word Add-in
- Real-time sync between Microsoft Word and platform
- AI-powered content rewriting within Word
- Session and event tracking for usage analytics

### Enterprise Features
- JWT authentication with token rotation
- SCIM provisioning and SSO (Okta, Microsoft Entra ID)
- Secrets vault with AES-256 encryption
- Comprehensive audit logging
- API rate limiting by subscription tier
- Upload size enforcement with configurable limits
- CORS policy management

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS |
| UI | Shadcn/ui, Radix Primitives, TipTap Editor, Lucide Icons |
| Backend | Python 3.12, FastAPI (async), Pydantic v2 |
| Database | PostgreSQL 16, SQLModel/SQLAlchemy, Alembic |
| Queue/Cache | Redis 7, Celery 5.4, Celery Beat |
| AI | Google Gemini 1.5 Pro/Flash, Context Caching API |
| Observability | Sentry, Structlog, Prometheus |
| Infrastructure | Docker, Docker Compose |
| CI/CD | GitHub Actions (lint, test, security scan, e2e smoke) |

---

## Integrations

| Category | Systems |
|----------|---------|
| Government Data | SAM.gov, FPDS, USAspending |
| Identity & SSO | Okta, Microsoft Entra ID, SCIM |
| CRM | Salesforce (opportunity sync, field mapping) |
| Productivity | Microsoft Word (add-in), SharePoint (auto-sync) |
| Project Management | Unanet |
| Communication | Slack, Email (SMTP), Webhooks |
| AI | Google Gemini 1.5 Pro/Flash with Context Caching |

---

## Project Structure

```
govtech-sniper/
├── docker-compose.yml
├── .github/workflows/ci.yml
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/          # 35+ domain models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic layer
│   │   ├── tasks/           # Celery async tasks
│   │   ├── api/
│   │   │   ├── routes/      # 40+ route modules
│   │   │   ├── deps.py      # Shared dependencies
│   │   │   └── utils.py     # Generic utilities (get_or_404)
│   │   └── observability/
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (dashboard)/ # 25+ dashboard pages
│   │   │   └── word-addin/  # Word add-in standalone UI
│   │   ├── components/      # 18+ component directories
│   │   ├── hooks/           # Custom React hooks
│   │   ├── lib/             # API clients, utilities
│   │   └── types/           # TypeScript interfaces
│   ├── Dockerfile
│   └── package.json
├── scripts/
│   ├── pre-commit           # Git pre-commit hook
│   ├── e2e_smoke.py         # E2E smoke test suite
│   ├── run_e2e.sh           # E2E test runner
│   ├── load_test.py         # Load testing
│   └── compose_guard.sh     # Docker compose safety checks
└── uploads/
```

---

## Quick Start

### Prerequisites

- Docker and Docker Compose v2
- Google Gemini API Key
- SAM.gov API Key (optional with `MOCK_SAM_GOV=true`)

### 1. Configure

```bash
cat > .env << EOF
SAM_GOV_API_KEY=your_sam_gov_api_key
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=$(openssl rand -hex 32)
MOCK_SAM_GOV=true
SAM_DOWNLOAD_ATTACHMENTS=true
SAM_MAX_ATTACHMENTS=10
SAM_CIRCUIT_BREAKER_ENABLED=true
SAM_CIRCUIT_BREAKER_COOLDOWN_SECONDS=900
SAM_CIRCUIT_BREAKER_MAX_SECONDS=3600
EOF
```

Set `MOCK_SAM_GOV=true` to run with deterministic mock data without external SAM.gov calls.

### 2. Start

```bash
docker compose up -d
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| Flower (Celery) | http://localhost:5555 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### 3. Verify

```bash
curl http://localhost:8000/health/ready
```

---

## API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register new user |
| `POST` | `/api/v1/auth/login` | Login, receive JWT |
| `POST` | `/api/v1/auth/refresh-token` | Refresh access token |

### Ingestion & Data Sources
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/ingest/sam` | Trigger SAM.gov search |
| `GET` | `/api/v1/ingest/sam/status/{task_id}` | Check ingest status |
| `GET` | `/api/v1/data-sources` | List configured data feeds |
| `POST` | `/api/v1/email-ingest/rules` | Configure email ingestion rules |

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/analyze/{rfp_id}` | Deep Read analysis |
| `GET` | `/api/v1/analyze/{rfp_id}/matrix` | Get compliance matrix |
| `POST` | `/api/v1/analyze/{rfp_id}/filter` | Run Killer Filter |

### Draft & Proposals
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/draft/{requirement_id}` | Generate section |
| `POST` | `/api/v1/draft/proposals/{id}/generate-all` | Batch generate |
| `POST` | `/api/v1/draft/refresh-cache` | Refresh AI cache |
| `POST` | `/api/v1/draft/proposals/{id}/outline` | Generate annotated outline |
| `GET` | `/api/v1/draft/proposals/{id}/sections` | List proposal sections |
| `PATCH` | `/api/v1/draft/sections/{id}` | Update section content |

### Capture Planning
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/capture` | List capture items |
| `POST` | `/api/v1/capture` | Create capture item |
| `POST` | `/api/v1/capture/{id}/bid-decision` | Score bid/no-bid |
| `POST` | `/api/v1/capture/{id}/gate-review` | Submit gate review |
| `GET` | `/api/v1/capture/timeline` | Pipeline timeline overview |

### Contracts
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/contracts` | List contracts |
| `POST` | `/api/v1/contracts` | Create contract |
| `GET` | `/api/v1/contracts/{id}/clins` | List contract line items |
| `GET` | `/api/v1/contracts/{id}/deliverables` | List deliverables |
| `POST` | `/api/v1/contracts/{id}/status-reports` | Submit status report |

### Reviews
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/reviews` | Create color team review |
| `POST` | `/api/v1/reviews/{id}/comments` | Add review comment |
| `PATCH` | `/api/v1/reviews/{id}/complete` | Complete review with score |

### Knowledge Base
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/documents` | Upload document |
| `GET` | `/api/v1/documents` | List documents |
| `DELETE` | `/api/v1/documents/{id}` | Remove document |

### Collaboration
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/collaboration/workspaces` | Create workspace |
| `POST` | `/api/v1/collaboration/workspaces/{id}/invite` | Invite member |
| `GET` | `/api/v1/collaboration/workspaces/{id}/inbox` | Workspace inbox |

### Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/export/proposals/{id}/docx` | Export as DOCX |
| `POST` | `/api/v1/export/proposals/{id}/pdf` | Export as PDF |
| `GET` | `/api/v1/export/rfps/{id}/compliance-matrix/xlsx` | Export matrix |

### Intelligence & Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/analytics/dashboard` | Usage metrics |
| `GET` | `/api/v1/signals` | Market signals |
| `GET` | `/api/v1/forecasts/pipeline` | Pipeline forecast |
| `GET` | `/api/v1/revenue/pipeline` | Revenue pipeline |
| `GET` | `/api/v1/benchmark` | Competitive benchmarks |

### Enterprise
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/audit/events` | Audit log |
| `POST` | `/api/v1/scim/v2/Users` | SCIM provisioning |
| `POST` | `/api/v1/secrets` | Store encrypted secret |
| `GET` | `/api/v1/integrations` | List integrations |
| `POST` | `/api/v1/webhooks/subscriptions` | Subscribe to events |

### Snapshots
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/rfps/{id}/snapshots` | Snapshot history |
| `GET` | `/api/v1/rfps/{id}/snapshots/diff` | Diff two snapshots |

Full interactive documentation available at `/docs` when the API is running.

---

## AI Architecture

### Context Caching

Instead of traditional vector search, GovTech Sniper uses Gemini's 1M token context window with the Context Caching API:

```
Knowledge Base Documents
    |
    v
Gemini Context Cache (60-min TTL)
    |
    v
Section Generation with Cached Context
    |
    v
Citation-Backed Proposal Content
```

This eliminates the need for a vector database while providing full document context and accurate page-level citations.

### Citation Enforcement

Every AI prompt includes strict citation rules. Generated content must reference source documents:

```
[[Source: Past_Performance.pdf, Page 12]]
```

Citations are parsed, validated against uploaded documents, and tracked for analytics.

---

## Development

### Local Setup (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install && npm run dev
```

**Celery Worker:**
```bash
celery -A app.tasks.celery_app worker -Q celery,ingest,analysis,generation,documents,periodic,maintenance --loglevel=info
```

### Git Hooks

```bash
cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

Pre-commit runs ruff (lint + format) on Python and tsc on TypeScript staged files.

### Linting

```bash
# Python
ruff check backend/app/           # Lint
ruff check --fix backend/app/     # Auto-fix
ruff format backend/app/          # Format

# TypeScript
cd frontend && npx tsc --noEmit   # Type check
cd frontend && npm run lint       # ESLint
```

### Database Migrations

```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### E2E Smoke Test

```bash
python scripts/e2e_smoke.py
```

Or via Docker:
```bash
./scripts/run_e2e.sh
```

### Load Testing

```bash
python scripts/load_test.py
```

---

## CI/CD Pipeline

GitHub Actions runs on every push with 4 jobs:

| Job | Checks |
|-----|--------|
| **backend-tests** | ruff lint, ruff format, pytest |
| **frontend-tests** | tsc, ESLint, Vitest, npm audit |
| **security-scan** | pip-audit, bandit SAST, git secret scan |
| **e2e-smoke** | Docker compose stack, health checks, smoke tests |

---

## Roadmap

- [x] JWT authentication and user management
- [x] PDF upload and text extraction
- [x] Proposal export (DOCX/PDF)
- [x] Deep Read compliance matrix extraction
- [x] AI proposal generation with citations
- [x] Team collaboration and commenting
- [x] Analytics dashboard
- [x] Audit logging
- [x] SCIM provisioning and SSO
- [x] Secrets vault
- [x] Capture pipeline management
- [x] Budget intelligence
- [x] Color team reviews (Pink/Red/Gold)
- [x] Contract lifecycle management
- [x] Teaming partner discovery board
- [x] Workflow automation engine
- [x] Multi-channel notifications
- [x] Word add-in integration
- [x] Salesforce and SharePoint sync
- [x] Market signals and pipeline forecasting
- [x] Revenue pipeline tracking
- [x] Email-based RFP ingestion
- [x] CI/CD with security scanning
- [ ] Subscription and billing integration (Stripe)
- [ ] Advanced win/loss analytics
- [ ] Template marketplace (backend ready, UI in progress)
- [ ] Mobile application

---

## Security

- All secrets loaded from environment variables
- Runtime validation: `SECRET_KEY` cannot be default in production
- JWT authentication with token rotation
- Sensitive export/share step-up verification only accepts `X-Step-Up-Code` header (query-string MFA codes are rejected)
- AES-256 encryption for stored secrets
- CORS restricted by environment
- API rate limiting per subscription tier
- Upload size enforcement (configurable, default 50MB)
- SCIM provisioning for enterprise identity management
- Audit logging for compliance tracking
- WebSocket diagnostics endpoints require authenticated requests (`/api/v1/ws/diagnostics*`)
- RFP snapshot diff/amendment-impact routes enforce owner scoping checks
- Email ingest duplicate suppression is scoped per ingest configuration (`config_id + message_id`)
- RFP/Contract/Knowledge-Base classification fields are wired through API schemas for policy-aware workflows
- SQL injection prevention via parameterized queries
- Security scanning in CI (pip-audit, bandit, secret detection)

---

## License

Proprietary. All rights reserved.
