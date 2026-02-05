# GovTech Sniper

**AI-Powered Government Contract Proposal Automation**

GovTech Sniper is a B2B SaaS platform that automates the process of finding, analyzing, and writing proposals for US Government contracts. It leverages Google Gemini 1.5 Pro's massive context window to generate compliant proposal responses with strict citation tracking.

---

## Overview

Government contractors spend weeks responding to a single RFP. GovTech Sniper reduces that to hours. The platform ingests opportunities from SAM.gov, qualifies them against your company profile, extracts compliance requirements, and generates citation-backed proposal sections using your knowledge base.

---

## Core Capabilities

### SAM.gov Integration
- Automated opportunity ingestion from the SAM.gov API
- Scheduled scanning via Celery Beat for new opportunities
- NAICS code, set-aside, and keyword filtering
- Versioned opportunity snapshots with change tracking
- Attachment downloads with PDF text extraction

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

### AI Proposal Writer
- RAG-powered section generation with Gemini Context Caching
- Strict citation enforcement: `[[Source: filename.pdf, Page X]]`
- Knowledge base documents cached for repeated use
- Per-section generation with word count tracking

### Citation Engine
- Automatic source tracking and verification
- Page-level citation parsing and validation
- Document usage analytics (times cited, last cited)

### Capture Management
- Full capture pipeline tracking from identification to submission
- Custom fields, win probability scoring, and team assignments
- Contact and relationship management per opportunity
- Budget intelligence and competitive landscape tracking

### Enterprise Features
- JWT authentication with role-based access control
- SCIM provisioning and SSO integration
- Secrets vault with AES-256 encryption
- Audit logging for compliance
- Team collaboration with commenting and notifications
- API rate limiting by subscription tier

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS |
| UI | Shadcn/ui, Radix Primitives, Lucide Icons |
| Backend | Python 3.12, FastAPI (async), Pydantic v2 |
| Database | PostgreSQL 16, SQLModel/SQLAlchemy, Alembic |
| Queue/Cache | Redis 7, Celery 5.4, Celery Beat |
| AI | Google Gemini 1.5 Pro/Flash, Context Caching API |
| Observability | Sentry, Structlog, Prometheus |
| Infrastructure | Docker, Docker Compose |

---

## Project Structure

```
govtech-sniper/
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── tasks/
│   │   ├── api/routes/
│   │   └── observability/
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/(dashboard)/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── types/
│   ├── Dockerfile
│   └── package.json
├── scripts/
│   ├── e2e_smoke.py
│   └── load_test.py
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

### Ingestion
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/ingest/sam` | Trigger SAM.gov search |
| `GET` | `/api/v1/ingest/sam/status/{task_id}` | Check ingest status |

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/analyze/{rfp_id}` | Deep Read analysis |
| `GET` | `/api/v1/analyze/{rfp_id}/matrix` | Get compliance matrix |
| `POST` | `/api/v1/analyze/{rfp_id}/filter` | Run Killer Filter |

### Draft Generation
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/draft/{requirement_id}` | Generate section |
| `POST` | `/api/v1/draft/proposals/{id}/generate-all` | Batch generate |
| `POST` | `/api/v1/draft/refresh-cache` | Refresh AI cache |

### Knowledge Base
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/documents` | Upload document |
| `GET` | `/api/v1/documents` | List documents |
| `DELETE` | `/api/v1/documents/{id}` | Remove document |

### Capture and Contracts
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/capture` | List capture items |
| `POST` | `/api/v1/capture` | Create capture item |
| `GET` | `/api/v1/contracts` | List contracts |
| `POST` | `/api/v1/contracts` | Create contract |

### Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/export/proposals/{id}/docx` | Export as DOCX |
| `POST` | `/api/v1/export/proposals/{id}/pdf` | Export as PDF |
| `GET` | `/api/v1/export/rfps/{id}/compliance-matrix/xlsx` | Export matrix |

### Enterprise
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/analytics/dashboard` | Usage metrics |
| `GET` | `/api/v1/audit/events` | Audit log |
| `POST` | `/api/v1/scim/v2/Users` | SCIM provisioning |
| `POST` | `/api/v1/secrets` | Store encrypted secret |

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
celery -A app.tasks.celery_app worker --loglevel=info
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
- [ ] Subscription and billing integration (Stripe)
- [ ] Slack and Teams notifications
- [ ] Advanced win/loss analytics
- [ ] Template marketplace
- [ ] Mobile application

---

## Security

- All secrets loaded from environment variables
- JWT authentication with token rotation
- AES-256 encryption for stored secrets
- CORS restricted by environment
- API rate limiting per subscription tier
- SCIM provisioning for enterprise identity management
- Audit logging for compliance tracking
- SQL injection prevention via parameterized queries

---

## License

Proprietary. All rights reserved.
