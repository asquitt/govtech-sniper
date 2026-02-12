# Decision Log

## Overview
This document records significant architectural, technical, and product decisions made for the GovTech Sniper platform. Each decision includes context, rationale, alternatives considered, and current status.

## Decision Template

```markdown
### [Decision ID] - [Short Title]
- **Date**: YYYY-MM-DD
- **Decision**: [What was decided]
- **Rationale**: [Why this decision was made]
- **Alternatives Considered**: [What else was evaluated]
- **Owner**: [Decision maker or accountable party]
- **Status**: [Proposed | Accepted | Deprecated | Superseded]
- **Superseded By**: [Decision ID if deprecated]
```

## Decisions

### D-001 - Adopted DataClassification Enum for Data Governance
- **Date**: 2026-02-10
- **Decision**: Implement `DataClassification` enum with levels: PUBLIC, INTERNAL, FCI, CUI
- **Rationale**: Government contractors handle sensitive data (CUI/FCI). Explicit classification enables policy-driven access control and audit compliance. Enum provides type-safe enforcement across backend models and API responses.
- **Alternatives Considered**:
  - String labels (rejected: error-prone, no compile-time checks)
  - Boolean flags (rejected: doesn't scale beyond 2-3 sensitivity levels)
  - Role-based only (rejected: roles ≠ data sensitivity)
- **Owner**: Security Team
- **Status**: Accepted
- **Implementation**: `backend/app/models/organization.py` - `DataClassification` enum

### D-002 - Policy Engine Uses Role-Based Rule Matrix
- **Date**: 2026-02-10
- **Decision**: Authorization logic centralized in policy engine with role × action × resource rules
- **Rationale**: Declarative rules are auditable, testable, and easier to extend than imperative checks scattered across routes. Supports compliance requirements for access control documentation.
- **Alternatives Considered**:
  - Inline `if user.role == "admin"` checks (rejected: brittle, hard to audit)
  - ABAC with complex attributes (rejected: over-engineering for MVP scope)
  - External policy service (rejected: adds latency and operational complexity)
- **Owner**: Backend Team
- **Status**: Accepted
- **Implementation**: `backend/app/services/policy_engine.py`

### D-003 - SLO Targets Set at 99%+ Success for Critical Flows
- **Date**: 2026-02-12
- **Decision**: Establish SLO targets for 4 critical flows:
  - Ingest: 99.5% success, p95 < 30s
  - Analyze: 99% success, p95 < 60s
  - Draft: 99% success, p95 < 120s
  - Export: 99.5% success, p95 < 15s
- **Rationale**: Enterprise customers expect reliable performance. These targets balance ambitious quality with realistic operational constraints. 99%+ aligns with industry standards for B2B SaaS.
- **Alternatives Considered**:
  - 95% targets (rejected: too low for paid customers)
  - 99.9% targets (rejected: requires significant infra investment)
  - No formal SLOs (rejected: can't manage what you don't measure)
- **Owner**: Platform Team
- **Status**: Accepted
- **Implementation**: `backend/app/services/slo_service.py`

### D-004 - Gemini Context Caching for Repeated Solicitation Analysis
- **Date**: 2026-02-05
- **Decision**: Use Gemini 1.5's context caching API to cache parsed solicitation documents for 1 hour
- **Rationale**: Reduces API costs by ~80% for multi-section analysis. Solicitation documents (50-200 pages) are analyzed 4-6 times per proposal (compliance, outline, section drafts). Caching TTL of 1 hour balances cost savings with freshness.
- **Alternatives Considered**:
  - No caching (rejected: prohibitive API costs at scale)
  - Local embedding cache (rejected: context caching is simpler, official support)
  - 24-hour TTL (rejected: stale data risk if solicitation updated)
- **Owner**: AI/ML Team
- **Status**: Accepted
- **Implementation**: `backend/app/services/gemini_service.py`

### D-005 - FastAPI + SQLModel for Backend Stack
- **Date**: 2025-12-15
- **Decision**: Use FastAPI (web framework) + SQLModel (ORM) + PostgreSQL (database)
- **Rationale**: FastAPI provides async support, automatic OpenAPI docs, and Pydantic validation. SQLModel unifies SQLAlchemy models with Pydantic schemas, reducing boilerplate. PostgreSQL offers JSONB for flexible metadata storage.
- **Alternatives Considered**:
  - Django (rejected: too heavyweight, ORM not async-native)
  - Flask (rejected: lacks async, manual validation setup)
  - SQLAlchemy Core (rejected: SQLModel reduces duplication)
- **Owner**: Backend Team
- **Status**: Accepted

### D-006 - Next.js 14 App Router for Frontend
- **Date**: 2025-12-15
- **Decision**: Use Next.js 14 with App Router + TypeScript + shadcn/ui
- **Rationale**: App Router enables server components for faster initial loads. Built-in API routes simplify BFF pattern. shadcn/ui provides accessible, customizable components. TypeScript enforces API contract alignment with backend.
- **Alternatives Considered**:
  - React SPA (rejected: worse SEO, slower initial load)
  - Next.js Pages Router (rejected: App Router is future direction)
  - Vue/Svelte (rejected: team expertise in React)
- **Owner**: Frontend Team
- **Status**: Accepted

---

## Decision Review Process

### When to Log a Decision
- Architectural choices affecting multiple components
- Technology or vendor selections
- Security/compliance policy changes
- API contract changes with backward compatibility impact
- Performance or reliability trade-offs

### Review Cadence
- Decisions reviewed quarterly for relevance
- Deprecated decisions moved to "Superseded" status
- Major decisions presented in architecture review meetings

## References
- [Risk Register](./risk-register.md)
- [KPI Baseline](./kpi-baseline.md)
- [Tech Debt Tracker](../TECH_DEBT.md)
