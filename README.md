# Airline Synthetic Data Platform

Production-ready FastAPI backend to generate, validate, store, and expose synthetic airline business datasets with deterministic relational integrity and optional LLM enrichment.

## Overview

- Deterministic generator controls IDs, foreign keys, references, and constraints.
- Optional LLM enrichment is limited to narrative/textual fields.
- Full validation pipeline includes schema, duplicates, referential integrity, business rules, and realism score.
- Secure REST APIs with JWT scopes, rate limiting, audit/correlation logging, and Redis cache.

## Architecture (Text Diagram)

```text
Client
  |
  v
FastAPI API Layer (auth, scopes, rate-limit, pagination)
  |
  +--> Dataset Service
  |      |
  |      +--> Generation Pipeline
  |      |      -> Catalogs
  |      |      -> Deterministic ID + Data Generation
  |      |      -> Optional LLM Text Enrichment
  |      |      -> Validation + Repair
  |      |
  |      +--> SQLAlchemy Persistence (PostgreSQL)
  |
  +--> Query Services (aircraft/flight/booking/manage-travel/irop)
         |
         +--> Redis Cache
```

## Tech Stack

- Python 3.11+
- FastAPI + Pydantic v2
- SQLAlchemy 2.x + Alembic
- PostgreSQL
- Redis
- Pytest
- Ruff
- Mypy
- Docker + Docker Compose

## Setup

1. Copy environment variables:
```bash
cp .env.example .env
```

2. Start dependencies and API:
```bash
docker compose up --build
```
The API is exposed on `http://127.0.0.1:18000` in the Docker setup.

3. Run migrations:
```bash
alembic upgrade head
```

## Run Locally Without Docker

1. Create a virtual environment and install:
```bash
pip install -e ".[dev]"
```

2. Set env vars from `.env.example`.

3. Run API:
```bash
uvicorn app.main:app --reload
```

## Environment Variables

See `.env.example`. Important values:
- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `RATE_LIMIT_REQUESTS`
- `RATE_LIMIT_WINDOW_SECONDS`
- `OPENAI_API_KEY` (optional)

## Authentication

Token endpoint:

```bash
curl -X POST "http://localhost:18000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"
```

Use returned token:
```bash
Authorization: Bearer <access_token>
```

Scopes:
- `dataset:read`
- `dataset:generate`
- `validation:read`
- `admin`

## Generate Dataset

```bash
curl -X POST "http://localhost:18000/api/v1/generation/jobs" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "record_count": 75,
    "enable_llm_enrichment": false,
    "dataset_version": "v20260601"
  }'
```

## API Examples

Get flights:
```bash
curl "http://localhost:18000/api/v1/flights?dataset_version=v20260601&page=1&page_size=25" \
  -H "Authorization: Bearer <token>"
```

Search flights:
```bash
curl -X POST "http://localhost:18000/api/v1/flights/search" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_version": "v20260601",
    "origin": "MAA",
    "destination": "DXB",
    "page": 1,
    "page_size": 10
  }'
```

Get booking by PNR:
```bash
curl "http://localhost:18000/api/v1/bookings/AB12CD?dataset_version=v20260601" \
  -H "Authorization: Bearer <token>"
```

Get manage travel by PNR:
```bash
curl "http://localhost:18000/api/v1/manage-travel/AB12CD?dataset_version=v20260601" \
  -H "Authorization: Bearer <token>"
```

Get IROPs for flight:
```bash
curl "http://localhost:18000/api/v1/flights/FLT-20260601-AI450-06010001/irops?dataset_version=v20260601" \
  -H "Authorization: Bearer <token>"
```

## Validation

Validation report endpoint:
```bash
curl "http://localhost:18000/api/v1/datasets/v20260601/validation-report" \
  -H "Authorization: Bearer <token>"
```

Expected structure:
```json
{
  "schema_valid": true,
  "business_rules_valid": true,
  "duplicates_found": 0,
  "referential_errors": [],
  "business_rule_errors": [],
  "realism_score": 95,
  "warnings": []
}
```

## CLI Generation

```bash
python -m app.cli generate --record-count 75 --dataset-version v20260601
```

## Testing and Quality

Run formatting/lint/tests:
```bash
ruff check .
mypy app
pytest
```

## AWS Deployment

For EC2 + Docker Compose + Nginx production steps, see:

- `DEPLOY_AWS_EC2.md`

## Design Decisions

- Deterministic controls all PK/FK and relationships to guarantee referential integrity.
- LLM enrichment is sandboxed to textual fields only and cannot mutate structural data.
- Validation gates are explicit and modular:
  - JSON Schema
  - Duplicate checks
  - Referential checks
  - Business rules
  - Realism scoring
- Cache keys are stable and version-scoped.
- App runs fully without external LLM access using `MockLLMClient`.
