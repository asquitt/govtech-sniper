# Deployment Playbook

Production deployment guide for the Orbitr (GovTech Sniper) platform.

---

## Prerequisites

| Requirement | Minimum |
|---|---|
| VPS / Cloud Instance | 4 GB RAM, 2 vCPU, 40 GB SSD |
| Docker Engine | 24+ |
| Docker Compose | v2 (bundled with Docker Engine) |
| Domain | A record pointing to the server IP |
| Ports | 80 and 443 open to the internet |

---

## 1. Initial Server Setup

```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in

# Clone the repo
git clone https://github.com/asquitt/govtech-sniper.git
cd govtech-sniper

# Create .env from template
cp .env.example .env
```

---

## 2. Required Environment Variables

Edit `.env` and set these values. **The stack will not run safely without them.**

| Variable | How to Generate |
|---|---|
| `SECRET_KEY` | `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | `openssl rand -hex 16` |
| `FLOWER_PASSWORD` | Pick a strong password |
| `DOMAIN` | Your domain, e.g. `app.orbitr.io` |

---

## 3. Optional Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini AI features | (disabled) |
| `SAM_GOV_API_KEY` | SAM.gov opportunity ingestion | (disabled) |
| `STRIPE_SECRET_KEY` | Billing | (disabled) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification | (disabled) |
| `RESEND_API_KEY` | Transactional email | (disabled) |
| `SENTRY_DSN` | Error tracking | (disabled) |
| `EMAIL_ENABLED` | Enable outbound email | `false` |
| `RETENTION_DAYS` | DB backup retention | `7` |
| `BACKUP_CRON` | Backup schedule (cron syntax) | `0 3 * * *` (daily 3 AM UTC) |

---

## 4. Start the Production Stack

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

This starts 9 services: api, celery_worker, celery_beat, postgres, redis, flower, frontend, caddy, backup.

Caddy automatically provisions a Let's Encrypt TLS certificate for your `DOMAIN`.

---

## 5. Run Database Migrations

```bash
docker compose exec api alembic upgrade head
```

---

## 6. Verify Deployment

```bash
# Health checks
curl https://your-domain.com/health/live    # → {"status":"ok"}
curl https://your-domain.com/health/ready   # → {"status":"ok","database":"ok","redis":"ok"}

# All services healthy
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Flower dashboard (requires FLOWER_USER/FLOWER_PASSWORD)
# Accessible at https://your-domain.com:5555 (or through SSH tunnel)
```

---

## 7. Routine Operations

### Deploy Updates

```bash
git pull origin main
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec api alembic upgrade head
```

### View Logs

```bash
# All services
docker compose logs -f --tail 50

# Specific service
docker compose logs api --tail 100
docker compose logs celery_worker --tail 100
```

### Manual Backup

```bash
docker compose exec backup /usr/local/bin/backup.sh
ls -la backups/
```

### Restore from Backup

```bash
# WARNING: This drops and recreates the database
docker compose run --rm backup /usr/local/bin/restore.sh /backups/rfpsniper_YYYYMMDD_HHMMSS.sql.gz
docker compose exec api alembic upgrade head   # Re-apply any newer migrations
```

---

## 8. Rotating Secrets

### Rotate SECRET_KEY

> **Warning:** Rotating SECRET_KEY invalidates all active JWT sessions. Users will need to log in again.

```bash
# Generate new key
openssl rand -hex 32
# Update SECRET_KEY in .env
# Restart api + worker
docker compose restart api celery_worker
```

### Rotate POSTGRES_PASSWORD

```bash
# 1. Update password in PostgreSQL
docker compose exec postgres psql -U rfpsniper -c "ALTER USER rfpsniper PASSWORD 'new_password';"
# 2. Update POSTGRES_PASSWORD in .env
# 3. Restart all services that connect to postgres
docker compose restart api celery_worker celery_beat backup
```

### Rotate API Keys (Gemini, SAM.gov, Stripe, Resend)

```bash
# 1. Generate new key in the provider's dashboard
# 2. Update the key in .env
# 3. Restart the service that uses it
docker compose restart api celery_worker
```

---

## 9. Monitoring

| Endpoint | Purpose |
|---|---|
| `/health/live` | Liveness probe (API is running) |
| `/health/ready` | Readiness probe (DB + Redis connected) |
| Flower dashboard | Celery task monitoring (port 5555) |
| Sentry | Error tracking (if `SENTRY_DSN` is set) |

### Docker Health Status

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
# All services should show "healthy"
```

---

## 10. Troubleshooting

### Service Won't Start

```bash
# Check logs for the failing service
docker compose logs <service> --tail 50
# Common causes: missing env vars, port conflicts, failed health checks
```

### Database Connection Issues

```bash
# Verify postgres is healthy
docker compose exec postgres pg_isready -U rfpsniper
# Check if migrations are current
docker compose exec api alembic current
```

### Worker Stuck / Not Processing Tasks

```bash
# Check worker health
docker compose exec celery_worker celery -A app.tasks.celery_app inspect active
# Restart worker
docker compose restart celery_worker
```

### Disk Full

```bash
# Check disk usage
df -h
# Prune Docker artifacts
docker system prune -f
# Check backup sizes
du -sh backups/*
```

### TLS Certificate Issues

```bash
# Caddy auto-renews certificates. If issues arise:
docker compose logs caddy --tail 50
# Ensure ports 80/443 are open and DOMAIN resolves to this server
```

---

## Architecture

```
                    ┌──────────────────┐
                    │    Internet       │
                    └────────┬─────────┘
                             │ :80/:443
                    ┌────────▼─────────┐
                    │     Caddy        │ ← auto TLS
                    │  (reverse proxy) │
                    └───┬──────────┬───┘
                        │          │
              /api/*    │          │  /*
              /health/* │          │
              /ws/*     │          │
                 ┌──────▼──┐  ┌───▼───────┐
                 │   API   │  │  Frontend  │
                 │ FastAPI  │  │  Next.js   │
                 └──┬───┬──┘  └───────────┘
                    │   │
           ┌────────┘   └────────┐
           │                     │
    ┌──────▼──────┐    ┌────────▼────────┐
    │  PostgreSQL  │    │     Redis       │
    │  (pgvector)  │    │ (broker+cache)  │
    └──────┬──────┘    └────────┬────────┘
           │                    │
    ┌──────▼──────┐    ┌───────▼─────────┐
    │   Backup    │    │  Celery Worker  │
    │  (pg_dump)  │    │  Celery Beat    │
    └─────────────┘    │  Flower         │
                       └─────────────────┘
```
