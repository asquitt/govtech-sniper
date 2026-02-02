# RFP Sniper - Backend API

A FastAPI backend for automating government contract proposal writing using Google Gemini AI.

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- SAM.gov API Key ([Get one here](https://sam.gov/content/entity-registration)) (optional if MOCK_SAM_GOV=true)
- Google Gemini API Key ([Get one here](https://makersuite.google.com/app/apikey))

### 1. Set Environment Variables

Create a `.env` file in the project root:

```bash
SAM_GOV_API_KEY=your_sam_gov_api_key
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=your_random_secret_key_min_32_chars
MOCK_SAM_GOV=true
MOCK_SAM_GOV_VARIANT=v1
SAM_DOWNLOAD_ATTACHMENTS=true
SAM_MAX_ATTACHMENTS=10
```
Set `MOCK_SAM_GOV=true` to use deterministic mock opportunities and skip external SAM.gov calls (handy for E2E runs).
Use `MOCK_SAM_GOV_VARIANT` to generate mock payload changes for snapshot diff testing.

### 2. Start the Stack

```bash
docker-compose up -d
```

This starts:
- **FastAPI** at http://localhost:8000
- **PostgreSQL** at localhost:5432
- **Redis** at localhost:6379
- **Celery Worker** for background tasks
- **Celery Beat** for scheduled tasks
- **Flower** (Celery monitoring) at http://localhost:5555

### 3. Access the API

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/          # API endpoints
│   │       ├── ingest.py    # SAM.gov ingestion
│   │       ├── analyze.py   # RFP analysis
│   │       ├── draft.py     # Proposal generation
│   │       ├── rfps.py      # RFP CRUD
│   │       ├── documents.py # Knowledge Base
│   │       └── health.py    # Health checks
│   ├── models/              # SQLModel database models
│   │   ├── user.py
│   │   ├── rfp.py
│   │   ├── proposal.py
│   │   └── knowledge_base.py
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic
│   │   ├── ingest_service.py    # SAM.gov API client
│   │   ├── filters.py           # Killer Filter (Gemini Flash)
│   │   └── gemini_service.py    # Gemini Pro integration
│   ├── tasks/               # Celery background tasks
│   │   ├── celery_app.py
│   │   ├── ingest_tasks.py
│   │   ├── analysis_tasks.py
│   │   └── generation_tasks.py
│   ├── config.py            # Settings management
│   ├── database.py          # Database connection
│   └── main.py              # FastAPI entry point
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🔌 API Endpoints

### Ingestion
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ingest/sam` | Trigger SAM.gov opportunity search |
| GET | `/api/v1/ingest/sam/status/{task_id}` | Check ingest task status |
| POST | `/api/v1/ingest/sam/quick-search` | Synchronous search (preview) |

### SAM.gov Ingest Enhancements
- Each ingest stores a raw snapshot in `sam_opportunity_snapshots` to support change tracking.
- When `SAM_DOWNLOAD_ATTACHMENTS=true`, the worker downloads opportunity attachments and extracts PDF text.
- Use `SAM_MAX_ATTACHMENTS` to cap downloads per opportunity.
- When `MOCK_SAM_GOV=true`, you can pass `mock_variant` as a query param to create deterministic changes for snapshot diffs.

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/analyze/{rfp_id}` | Start Deep Read analysis |
| GET | `/api/v1/analyze/{rfp_id}/matrix` | Get compliance matrix |
| POST | `/api/v1/analyze/{rfp_id}/filter` | Run Killer Filter |

### Draft Generation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/draft/proposals` | Create new proposal |
| POST | `/api/v1/draft/{requirement_id}` | Generate section draft |
| POST | `/api/v1/draft/proposals/{id}/generate-all` | Generate all sections |

### RFPs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/rfps` | List RFPs |
| GET | `/api/v1/rfps/{id}` | Get RFP details |
| POST | `/api/v1/rfps` | Create RFP manually |
| GET | `/api/v1/rfps/{id}/snapshots` | List SAM.gov snapshot history |
| GET | `/api/v1/rfps/{id}/snapshots/diff` | Diff latest two snapshots |

### Knowledge Base
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/documents` | List documents |
| POST | `/api/v1/documents` | Upload document |
| DELETE | `/api/v1/documents/{id}` | Delete document |

## 🧠 Core Concepts

### The Killer Filter
Uses **Gemini 1.5 Flash** (fast, cheap) to quickly qualify/disqualify RFPs:
- Checks NAICS codes, set-asides, clearance levels
- Runs rule-based pre-filter first (free)
- Only calls AI for edge cases
- Cost: ~$0.00001875 per 1K tokens

### Deep Read Analysis
Uses **Gemini 1.5 Pro** (powerful, expensive) to extract compliance requirements:
- Parses full RFP document
- Identifies mandatory vs evaluated requirements
- Categorizes by type (Technical, Past Performance, etc.)
- Generates compliance matrix

### RAG with Context Caching
Instead of vector search, we leverage Gemini's massive context window:
1. User uploads Knowledge Base documents (resumes, past performance)
2. Documents are cached using Gemini's Context Caching API
3. Generation prompts reference the cached context
4. AI generates text with embedded citations: `[[Source: file.pdf, Page 12]]`

### Citation Engine
Every generated assertion must cite sources:
```
We have 5 years of Agile experience [[Source: Past_Perf_2022.pdf, Page 12]].
```

The frontend parses these markers to create clickable source links.

## 🔧 Development

### Run Locally (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/rfpsniper
export REDIS_URL=redis://localhost:6379/0
export SAM_GOV_API_KEY=your_key
export MOCK_SAM_GOV=true
export SAM_DOWNLOAD_ATTACHMENTS=true
export SAM_MAX_ATTACHMENTS=10
export GEMINI_API_KEY=your_key
export DEBUG=true

# Run the API
uvicorn app.main:app --reload

# Run Celery worker (in another terminal)
celery -A app.tasks.celery_app worker --loglevel=info
```

### Run Tests

```bash
pytest tests/ -v
```

### E2E Smoke Test

Run a quick end-to-end flow (ingest -> analyze -> draft -> export) once the stack is up:

```bash
python scripts/e2e_smoke.py
```

If you're running via Docker, prefer the helper script from the repo root:

```bash
./scripts/run_e2e.sh
```
The script uses `COMPOSE_PROJECT_NAME=govtech-sniper` by default; override it if you use a different Compose project name.
It also runs `./scripts/compose_guard.sh` to scope commands and warn when other Compose projects are running.

For Docker setups where the host cannot reach the API or you want deterministic ingest, run inside the API
container and enable mock SAM.gov:

```bash
docker compose exec -T api /bin/sh -c "MOCK_SAM_GOV=true RFP_SKIP_SAM_INGEST=false python /app/scripts/e2e_smoke.py"
```

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## 📊 Monitoring

- **Flower Dashboard**: http://localhost:5555 (Celery task monitoring)
- **Health Check**: http://localhost:8000/health/ready (full system status)

## 🔐 Security Notes

- API keys are loaded from environment variables, never committed
- JWT authentication should be implemented before production
- CORS is restricted to localhost in development
- Rate limiting should be added for production

## 📝 License

Proprietary - All rights reserved.
