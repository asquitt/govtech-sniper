# 🎯 RFP Sniper

**AI-Powered Government Contract Proposal Automation**

RFP Sniper is a B2B SaaS platform that automates the process of finding, analyzing, and writing proposals for US Government contracts. It leverages Google Gemini 1.5 Pro's massive context window to generate compliant responses with strict citation tracking.

---

## 🚀 Features

### 📡 SAM.gov Integration
- Automated opportunity ingestion from SAM.gov API
- Scheduled scanning for new opportunities
- NAICS code and set-aside filtering
- Versioned opportunity snapshots for change tracking
- Optional attachment downloads with PDF text extraction

### 🔍 The Killer Filter
- AI-powered qualification screening using **Gemini 1.5 Flash**
- Rule-based pre-filtering for instant disqualification
- Checks NAICS codes, security clearances, set-asides

### 📋 Deep Read Analysis
- Full RFP parsing with **Gemini 1.5 Pro** (1M token context)
- Automatic compliance matrix extraction
- Requirement categorization (Mandatory/Evaluated/Optional)

### ✍️ AI Proposal Writer
- RAG-powered section generation with citations
- **Context Caching API** for Knowledge Base documents
- Every claim must cite sources: `[[Source: filename.pdf, Page X]]`

### 📊 Citation Engine
- Automatic source tracking and verification
- Interactive citation viewer with tooltips
- Document usage analytics

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS |
| **UI Components** | Shadcn/ui, Radix Primitives, Lucide Icons |
| **Backend** | Python 3.12, FastAPI (Async), Pydantic v2 |
| **Database** | PostgreSQL 16, SQLModel/SQLAlchemy |
| **Queue** | Redis + Celery (background tasks) |
| **AI** | Google Gemini 1.5 Pro/Flash via `google-generativeai` SDK |
| **Infrastructure** | Docker & Docker Compose |

---

## 📁 Project Structure

```
GovTech Sniper/
├── docker-compose.yml          # Full stack orchestration
├── README.md                   # This file
│
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── main.py             # FastAPI entry point
│   │   ├── config.py           # Settings management
│   │   ├── database.py         # Async DB connection
│   │   ├── models/             # SQLModel ORM models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   │   ├── ai_engine.py    # Core AI service
│   │   │   ├── ingest_service.py
│   │   │   ├── filters.py      # Killer Filter
│   │   │   └── pdf_processor.py
│   │   ├── tasks/              # Celery tasks
│   │   └── api/routes/         # API endpoints
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                   # Next.js Frontend
│   ├── src/
│   │   ├── app/                # App Router pages
│   │   │   ├── (dashboard)/    # Dashboard layout
│   │   │   │   ├── opportunities/
│   │   │   │   ├── analysis/
│   │   │   │   └── knowledge-base/
│   │   ├── components/
│   │   │   ├── ui/             # Base UI components
│   │   │   ├── layout/         # Sidebar, Header
│   │   │   └── analysis/       # Analysis-specific
│   │   ├── hooks/              # React Query hooks
│   │   ├── lib/                # Utilities, API client
│   │   └── types/              # TypeScript definitions
│   ├── Dockerfile
│   └── package.json
│
└── uploads/                    # Knowledge Base documents
```

---

## 🏃 Quick Start

### Prerequisites

- Docker & Docker Compose v2
- SAM.gov API Key ([Register here](https://sam.gov/content/entity-registration)) (optional if MOCK_SAM_GOV=true)
- Google Gemini API Key ([Get here](https://makersuite.google.com/app/apikey))

### 1. Clone & Configure

```bash
cd "GovTech Sniper"

# Create environment file
cat > .env << EOF
SAM_GOV_API_KEY=your_sam_gov_api_key
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=$(openssl rand -hex 32)
MOCK_SAM_GOV=true
MOCK_SAM_GOV_VARIANT=v1
SAM_DOWNLOAD_ATTACHMENTS=true
SAM_MOCK_ATTACHMENTS_DIR=/app/fixtures/sam_attachments
SAM_MAX_ATTACHMENTS=10
SAM_CIRCUIT_BREAKER_ENABLED=true
SAM_CIRCUIT_BREAKER_COOLDOWN_SECONDS=900
SAM_CIRCUIT_BREAKER_MAX_SECONDS=3600
EOF
```
Set `MOCK_SAM_GOV=true` to run with deterministic mock opportunities and avoid external SAM.gov calls.
Use `MOCK_SAM_GOV_VARIANT` to generate mock payload changes for snapshot diff testing.
Use `SAM_DOWNLOAD_ATTACHMENTS` and `SAM_MAX_ATTACHMENTS` to control automatic attachment ingestion.
Use `SAM_MOCK_ATTACHMENTS_DIR` to enable attachment ingestion in mock mode using local fixtures.
Circuit breaker settings:
- `SAM_CIRCUIT_BREAKER_ENABLED` toggles rate-limit circuit breaking.
- `SAM_CIRCUIT_BREAKER_COOLDOWN_SECONDS` controls how long we stop hitting SAM.gov after a 429.
- `SAM_CIRCUIT_BREAKER_MAX_SECONDS` caps the cooldown window.

### 2. Start the Stack

```bash
docker-compose up -d
```

This starts:
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| Flower (Celery) | http://localhost:5555 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### 3. Verify Health

```bash
curl http://localhost:8000/health/ready
```

---

## 🔌 API Endpoints

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
| `DELETE` | `/api/v1/documents/{id}` | Delete document |

### RFP Snapshotting
- `GET /api/v1/rfps/{id}/snapshots` lists SAM.gov snapshot history (use `include_raw=true` for raw payloads).
- `GET /api/v1/rfps/{id}/snapshots/diff` diffs the latest two snapshots or accepts `from_snapshot_id` + `to_snapshot_id`.

### Ingestion Details
- Each ingest stores a raw opportunity snapshot in `sam_opportunity_snapshots` for change tracking.
- When `SAM_DOWNLOAD_ATTACHMENTS=true`, attachments are downloaded and PDFs are text-extracted.
- Use `SAM_MAX_ATTACHMENTS` to cap downloads per opportunity.
- When `MOCK_SAM_GOV=true`, you can pass `mock_variant` to `/api/v1/ingest/sam` to generate deterministic changes for snapshot diffs.

---

## 🧠 AI Architecture

### Context Caching (The Secret Sauce)

Instead of traditional vector search, we leverage Gemini's **1M token context window**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Gemini Context Cache                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Resume.pdf  │ │ PastPerf.pdf│ │ Certs.pdf   │  ...       │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│                         ↓                                    │
│              Cached for 60 minutes                           │
│                         ↓                                    │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ "Generate response to requirement X using cached docs" ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Benefits:**
- No vector database required
- Full document context available
- Accurate page-level citations
- 60-minute cache reduces API costs

### Citation Enforcement

Every AI prompt includes strict citation rules:

```
CRITICAL: Every factual claim MUST be cited using:
[[Source: Filename.pdf, Page X]]

Example: "We have 5 years of Agile experience 
[[Source: Past_Performance.pdf, Page 12]]."
```

---

## 🎨 Frontend Features

### Opportunities Page
- Data table with status badges
- Deadline urgency indicators
- Qualification score display
- SAM.gov sync integration

### Analysis View (Split Screen)
- **Left Panel**: Compliance Matrix checklist
- **Right Panel**: AI-generated draft preview
- Click requirement → Generate response
- Real-time citation highlighting

### Citation Viewer Component
- Parses `[[Source: ...]]` patterns
- Interactive hover tooltips
- Click to view source document
- Citation summary panel

---

## 🔧 Development

### Run Locally (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/rfpsniper
export REDIS_URL=redis://localhost:6379/0
export GEMINI_API_KEY=your_key

uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
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

---

## E2E Smoke Test

Run a quick end-to-end flow (ingest -> analyze -> draft -> export) once the stack is up.

```bash
# From repo root, with backend deps installed
python scripts/e2e_smoke.py
```

If you're running via Docker, prefer the helper script (runs inside the API container):

```bash
./scripts/run_e2e.sh
```
The script uses `COMPOSE_PROJECT_NAME=govtech-sniper` by default; override it if you use a different Compose project name.
It also runs `./scripts/compose_guard.sh` to scope commands and warn when other Compose projects are running.

Optional env overrides:
```bash
export RFP_API_URL=http://localhost:8000
export RFP_TEST_EMAIL=e2e@example.com
export RFP_TEST_PASSWORD=TestPassword123!
export RFP_TEST_KEYWORDS=software
export RFP_SKIP_SAM_INGEST=true
```

If you're running via Docker and prefer deterministic ingest without calling SAM.gov, set `MOCK_SAM_GOV=true`
in your `.env` and restart the stack. You can also run the script inside the API container (helpful when host
networking to the API port is blocked):

```bash
docker compose exec -T api /bin/sh -c "MOCK_SAM_GOV=true RFP_SKIP_SAM_INGEST=false python /app/scripts/e2e_smoke.py"
```

If you mapped the API to a non-default host port (for example `API_PORT=8001`), set:
```bash
export RFP_API_URL=http://localhost:8001
```

---

## 📈 Roadmap

- [ ] JWT Authentication & User Management
- [ ] PDF upload and text extraction
- [ ] Proposal export (DOCX/PDF)
- [ ] Multi-user collaboration
- [ ] Subscription/billing integration
- [ ] Advanced analytics dashboard
- [ ] Slack/Teams notifications

---

## 🔐 Security Notes

- API keys loaded from environment variables only
- CORS restricted to localhost in development
- JWT auth to be implemented before production
- Rate limiting for external API calls
- Secrets never logged or exposed

---

## 📄 License

Proprietary - All rights reserved.

---

<div align="center">
  <strong>Built with ❤️ for GovTech</strong>
  <br>
  <sub>Powered by Google Gemini 1.5 Pro</sub>
</div>
