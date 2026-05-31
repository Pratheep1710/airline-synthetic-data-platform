# Airline Synthetic Data Platform

Production-oriented FastAPI platform for generating, validating, storing, and serving realistic synthetic airline datasets. The project is designed for engineering teams that need trusted airline domain data for API testing, QA automation, product demos, data science experiments, and operational simulations without using real passenger or production data.

The platform combines deterministic data generation with optional LLM-based text enrichment. Structural fields such as primary keys, foreign keys, schedules, PNRs, inventory, and seat assignments are always code-controlled so generated datasets remain reproducible and relationally consistent.

## Table of Contents

- [What This Project Does](#what-this-project-does)
- [Core Capabilities](#core-capabilities)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Domain Data Model](#domain-data-model)
- [End-to-End Data Flow](#end-to-end-data-flow)
- [Generation and Validation Pipeline](#generation-and-validation-pipeline)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Authentication and Authorization](#authentication-and-authorization)
- [API Guide](#api-guide)
- [CLI Usage](#cli-usage)
- [Testing and Code Quality](#testing-and-code-quality)
- [Operational Notes](#operational-notes)
- [Design Principles](#design-principles)
- [Roadmap Ideas](#roadmap-ideas)

## What This Project Does

Airline systems are highly relational: aircraft operate flights, flights sell seats, bookings create PNRs, manage-travel records depend on valid bookings, and disruption events must reference existing operational flights. This platform generates that connected data as versioned datasets and exposes it through secure, paginated REST APIs.

Typical use cases include:

- Backend and frontend integration testing against realistic airline APIs.
- QA scenarios for bookings, flight search, manage-travel flows, and irregular operations.
- Demo environments that need consistent non-production airline data.
- Data science experimentation where relational integrity matters.
- Contract testing for consumers that depend on versioned airline domain data.

## Core Capabilities

- Deterministic synthetic data generation for aircraft, flights, bookings, manage-travel records, and IROPs.
- Dataset versioning so consumers can query a stable snapshot with `dataset_version`.
- Optional LLM enrichment for non-structural text fields such as passenger names and customer-facing disruption messages.
- Validation pipeline covering JSON Schema, duplicates, referential integrity, business rules, and realism scoring.
- Secure REST APIs with JWT bearer tokens and route-level scopes.
- Rate limiting backed by Redis with an in-memory fallback.
- Redis-backed response caching with dataset-version scoped keys.
- SQLAlchemy persistence with Alembic migrations.
- Docker Compose stack for API, PostgreSQL, and Redis.
- Local development mode with SQLite fallback.

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Uvicorn |
| Language | Python 3.11+ |
| Validation and settings | Pydantic v2, pydantic-settings, jsonschema |
| Persistence | SQLAlchemy 2.x, Alembic |
| Databases | PostgreSQL for Docker/production-style runtime, SQLite for simple local development |
| Cache and rate limiting | Redis with in-memory fallback |
| Auth | OAuth2 password flow, JWT, scoped authorization |
| Testing | Pytest, pytest-asyncio, httpx |
| Quality | Ruff, Mypy |
| Packaging | pyproject.toml, setuptools |
| Deployment | Docker, Docker Compose, Nginx config under `deployment/nginx` |

## System Architecture

```mermaid
flowchart TB
    Client[Client, Swagger UI, cURL, service consumer]
    API[FastAPI API Layer]
    Auth[JWT auth, scopes, rate limit]
    DatasetService[DatasetService]
    Pipeline[GenerationPipeline]
    Generator[DeterministicDataGenerator]
    LLM[Optional LLM enrichment]
    Validators[Validation stack]
    DB[(PostgreSQL or SQLite)]
    Cache[(Redis or in-memory cache)]
    ReadServices[Domain read services]

    Client --> API
    API --> Auth
    Auth --> DatasetService
    DatasetService --> Pipeline
    Pipeline --> Generator
    Generator --> LLM
    Generator --> Validators
    Validators --> Pipeline
    Pipeline --> DB
    DatasetService --> Cache
    API --> ReadServices
    ReadServices --> Cache
    ReadServices --> DB
```

## Domain Data Model

```mermaid
erDiagram
    AIRCRAFT ||--o{ FLIGHT : operates
    FLIGHT ||--o{ BOOKING : sells
    BOOKING ||--o| MANAGE_TRAVEL : manages
    FLIGHT ||--o{ IROP : disrupts
    DATASET_GENERATION_JOB ||--o{ AIRCRAFT : publishes
    DATASET_GENERATION_JOB ||--o{ FLIGHT : publishes
    DATASET_GENERATION_JOB ||--o{ BOOKING : publishes
    DATASET_GENERATION_JOB ||--o{ MANAGE_TRAVEL : publishes
    DATASET_GENERATION_JOB ||--o{ IROP : publishes

    AIRCRAFT {
        string aircraft_id PK
        string dataset_version
        string tail_number
        string aircraft_type
        string seat_map_id
        string status
    }

    FLIGHT {
        string flight_id PK
        string dataset_version
        string aircraft_id FK
        string origin
        string destination
        datetime departure_time_utc
        datetime arrival_time_utc
        string selling_status
        string operational_status
    }

    BOOKING {
        string booking_id PK
        string dataset_version
        string pnr UK
        string flight_id FK
        int passenger_count
        string booking_status
    }

    MANAGE_TRAVEL {
        string manage_travel_id PK
        string dataset_version
        string pnr FK
        json selected_seats
        json extra_bags
        json meals
    }

    IROP {
        string irop_id PK
        string dataset_version
        string flight_id FK
        string event_type
        string severity
        string customer_message
    }

    DATASET_GENERATION_JOB {
        string job_id PK
        string dataset_version
        string status
        string validation_status
        json validation_errors
    }
```

## End-to-End Data Flow

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI
    participant Auth as Auth and Rate Limit
    participant Service as DatasetService
    participant Pipeline as GenerationPipeline
    participant Generator as Deterministic Generator
    participant Validation as Validators
    participant DB as Database
    participant Cache as Cache

    User->>API: POST /api/v1/auth/token
    API-->>User: JWT bearer token
    User->>API: POST /api/v1/generation/jobs
    API->>Auth: Verify token scope and rate limit
    Auth-->>API: Allowed
    API->>Service: Create generation job
    Service->>DB: Insert RUNNING job
    Service->>Pipeline: Run dataset generation
    Pipeline->>Generator: Generate aircraft, flights, bookings, manage-travel, IROPs
    Generator-->>Pipeline: Generated records
    Pipeline->>Validation: Validate schema, duplicates, references, business rules, realism
    Validation-->>Pipeline: Validation report
    Pipeline->>DB: Persist entities in dependency order
    Service->>DB: Mark job COMPLETED or FAILED
    Service->>Cache: Invalidate dataset-version cache prefix
    API-->>User: Job response with dataset_version and validation status
    User->>API: GET versioned read endpoints
    API->>Cache: Check cached response
    API->>DB: Query if cache miss
    API-->>User: Paginated dataset response
```

## Generation and Validation Pipeline

Generation is intentionally ordered so downstream entities always reference records that already exist.

```mermaid
flowchart LR
    A[Catalogs: airports, routes, seat maps, baggage, meals] --> B[Aircraft]
    B --> C[Flights]
    C --> D[Bookings and PNRs]
    D --> E[Manage Travel]
    C --> F[IROPs]
    D --> G[Optional text enrichment]
    E --> G
    F --> G
    G --> H[JSON Schema validation]
    H --> I[Duplicate validation]
    I --> J[Referential validation]
    J --> K[Business rule validation]
    K --> L[Realism scoring]
    L --> M{Valid?}
    M -- Yes --> N[Persist dataset]
    M -- No --> O[Deterministic repair loop]
    O --> H
```

Validation stages:

| Stage | Purpose | Implementation |
|---|---|---|
| JSON Schema | Confirms entity shapes and data types | `app/validation/schema_validator.py`, `json_schemas/*.schema.json` |
| Duplicate checks | Detects repeated IDs and PNRs | `app/validation/duplicate_validator.py` |
| Referential integrity | Verifies relationships across generated entities | `app/validation/referential_validator.py` |
| Business rules | Enforces domain-specific airline constraints | `app/validation/business_validator.py` |
| Realism score | Scores generated data quality from 0 to 100 | `app/validation/realism_validator.py` |
| Repair loop | Corrects deterministic failures where possible | `app/generation/pipeline.py` |

## Project Structure

```text
.
|-- app/
|   |-- api/                  # FastAPI routers and dependencies
|   |-- core/                 # config, security, logging, cache, rate limiting
|   |-- db/                   # SQLAlchemy models, sessions, repositories
|   |-- generation/           # deterministic generator, catalogs, pipeline, LLM enrichment
|   |-- schemas/              # Pydantic response/request schemas
|   |-- services/             # domain service layer
|   |-- tests/                # pytest suite
|   `-- validation/           # schema, duplicate, referential, business, realism validators
|-- alembic/                  # database migration environment and revisions
|-- deployment/nginx/         # production-facing Nginx sample config
|-- json_schemas/             # JSON Schema contracts for generated entities
|-- docker-compose.yml        # API + PostgreSQL + Redis runtime
|-- docker-compose.prod.yml   # production override placeholder
|-- Dockerfile                # API image definition
|-- pyproject.toml            # package metadata and dev tooling config
`-- TECHNICAL_AND_BUSINESS_FLOW.md
```

## Getting Started

### Option 1: Run with Docker Compose

Prerequisites:

- Docker
- Docker Compose v2

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Start PostgreSQL and Redis:

```bash
docker compose up -d postgres redis
```

3. Build the API image and run database migrations:

```bash
docker compose run --rm api alembic upgrade head
```

4. Start the API:

```bash
docker compose up api
```

5. Open the service:

```text
API:        http://127.0.0.1:18000
Health:     http://127.0.0.1:18000/health
Swagger UI: http://127.0.0.1:18000/docs
OpenAPI:    http://127.0.0.1:18000/api/v1/openapi.json
```

The Docker Compose file maps host port `18000` to container port `8000`.

### Option 2: Run Locally Without Docker

Prerequisites:

- Python 3.11+
- Optional Redis if you want external caching locally

1. Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

2. Install the project with development dependencies:

```bash
pip install -e ".[dev]"
```

3. Copy environment values:

```bash
cp .env.example .env
```

For simple local development, you may use the built-in SQLite default:

```env
DATABASE_URL=sqlite+pysqlite:///./airline_synth.db
REDIS_URL=redis://localhost:6379/0
```

If Redis is unavailable, the application falls back to an in-memory cache.

4. Run migrations:

```bash
alembic upgrade head
```

5. Start the API:

```bash
uvicorn app.main:app --reload
```

Local default URL:

```text
http://127.0.0.1:8000
```

## Configuration

Configuration is loaded from environment variables using `pydantic-settings`. See `.env.example` for a complete template.

| Variable | Purpose | Example |
|---|---|---|
| `APP_NAME` | FastAPI application title | `Airline Synthetic Data Platform` |
| `ENVIRONMENT` | Runtime mode: `development`, `test`, or `production` | `development` |
| `DEBUG` | Development debug toggle | `true` |
| `API_V1_PREFIX` | Versioned API prefix | `/api/v1` |
| `SECRET_KEY` | JWT signing secret | `change-this-in-production` |
| `ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime | `60` |
| `DATABASE_URL` | SQLAlchemy database URL | `postgresql+psycopg://airline:airline@postgres:5432/airline_synth` |
| `REDIS_URL` | Redis cache URL | `redis://redis:6379/0` |
| `DEFAULT_DATASET_RECORD_COUNT` | Default generation size | `75` |
| `DEFAULT_PAGE_SIZE` | Default list page size | `25` |
| `MAX_PAGE_SIZE` | Maximum list page size | `100` |
| `RATE_LIMIT_REQUESTS` | Requests per window | `120` |
| `RATE_LIMIT_WINDOW_SECONDS` | Rate limit window length | `60` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | `http://localhost:3000,http://localhost:5173` |
| `OPENAI_API_KEY` | Optional LLM enrichment key | empty by default |

For production, rotate `SECRET_KEY`, use managed PostgreSQL and Redis where possible, set `ENVIRONMENT=production`, and keep secrets out of source control.

## Authentication and Authorization

The API uses OAuth2 password flow to issue JWT bearer tokens.

Token endpoint:

```bash
curl -X POST "http://127.0.0.1:18000/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"
```

Use the returned token:

```http
Authorization: Bearer <access_token>
```

Built-in development users:

| User | Password | Scopes |
|---|---|---|
| `reader` | `reader` | `dataset:read` |
| `generator` | `generator` | `dataset:read`, `dataset:generate`, `validation:read` |
| `admin` | `admin` | `dataset:read`, `dataset:generate`, `validation:read`, `admin` |
| `gen_only_user` | `GenOnly@123` | `dataset:generate` |
| `read_only_user` | `ReadOnly@123` | `dataset:read`, `validation:read` |

Available scopes:

| Scope | Allows |
|---|---|
| `dataset:read` | Read generated datasets and entity APIs |
| `dataset:generate` | Create dataset generation jobs |
| `validation:read` | Read validation reports |
| `admin` | Reserved administrative access |

The current user store is intentionally simple and in-memory for development. Replace it with an identity provider or persistent user store before using the service as a real production authentication boundary.

## API Guide

All main APIs are mounted under `/api/v1`.

### Generate a Dataset

```bash
curl -X POST "http://127.0.0.1:18000/api/v1/generation/jobs" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "record_count": 75,
    "enable_llm_enrichment": false,
    "dataset_version": "v20260601"
  }'
```

Notes:

- `record_count` must be between `1` and `5000`.
- `dataset_version` is optional. If omitted, the service generates a timestamp-based version.
- Reusing an existing `dataset_version` returns `409 Conflict`.
- Dataset generation runs behind a process-level async lock to avoid concurrent generation collisions.

Example response:

```json
{
  "job_id": "JOB-123456ABCD",
  "dataset_version": "v20260601",
  "status": "COMPLETED",
  "validation_status": "PASSED",
  "requested_counts": {
    "available_aircrafts": 75,
    "available_flights": 75,
    "bookings": 75,
    "manage_travel": 75,
    "irops": 75
  },
  "validation_errors": {
    "schema_valid": true,
    "business_rules_valid": true,
    "duplicates_found": 0,
    "referential_errors": [],
    "business_rule_errors": [],
    "realism_score": 95,
    "warnings": []
  },
  "created_at": "2026-06-01T00:00:00Z",
  "completed_at": "2026-06-01T00:00:02Z"
}
```

### Check a Generation Job

```bash
curl "http://127.0.0.1:18000/api/v1/generation/jobs/JOB-123456ABCD" \
  -H "Authorization: Bearer <token>"
```

### List Published Datasets

```bash
curl "http://127.0.0.1:18000/api/v1/datasets" \
  -H "Authorization: Bearer <token>"
```

### Read a Validation Report

```bash
curl "http://127.0.0.1:18000/api/v1/datasets/v20260601/validation-report" \
  -H "Authorization: Bearer <token>"
```

### Query Aircraft

```bash
curl "http://127.0.0.1:18000/api/v1/aircrafts?dataset_version=v20260601&page=1&page_size=25" \
  -H "Authorization: Bearer <token>"
```

```bash
curl "http://127.0.0.1:18000/api/v1/aircrafts/<aircraft_id>?dataset_version=v20260601" \
  -H "Authorization: Bearer <token>"
```

### Query Flights

List flights:

```bash
curl "http://127.0.0.1:18000/api/v1/flights?dataset_version=v20260601&page=1&page_size=25" \
  -H "Authorization: Bearer <token>"
```

Filter flights:

```bash
curl "http://127.0.0.1:18000/api/v1/flights?dataset_version=v20260601&origin=MAA&destination=DXB" \
  -H "Authorization: Bearer <token>"
```

Search flights:

```bash
curl -X POST "http://127.0.0.1:18000/api/v1/flights/search" \
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

Get one flight:

```bash
curl "http://127.0.0.1:18000/api/v1/flights/<flight_id>?dataset_version=v20260601" \
  -H "Authorization: Bearer <token>"
```

### Query Bookings and Manage Travel

```bash
curl "http://127.0.0.1:18000/api/v1/bookings/AB12CD?dataset_version=v20260601" \
  -H "Authorization: Bearer <token>"
```

```bash
curl "http://127.0.0.1:18000/api/v1/manage-travel/AB12CD?dataset_version=v20260601" \
  -H "Authorization: Bearer <token>"
```

### Query IROPs

List IROPs:

```bash
curl "http://127.0.0.1:18000/api/v1/irops?dataset_version=v20260601&page=1&page_size=25" \
  -H "Authorization: Bearer <token>"
```

Get one IROP:

```bash
curl "http://127.0.0.1:18000/api/v1/irops/<irop_id>?dataset_version=v20260601" \
  -H "Authorization: Bearer <token>"
```

List disruptions for a flight:

```bash
curl "http://127.0.0.1:18000/api/v1/flights/<flight_id>/irops?dataset_version=v20260601" \
  -H "Authorization: Bearer <token>"
```

### Pagination and Sorting

List endpoints support common query parameters:

| Parameter | Description |
|---|---|
| `dataset_version` | Restricts reads to a generated dataset snapshot |
| `page` | 1-based page number |
| `page_size` | Number of items per page, capped by `MAX_PAGE_SIZE` |
| `sort_by` | Field to sort by, where supported by the repository |
| `sort_dir` | `asc` or `desc` |

## CLI Usage

Generate a dataset from the command line:

```bash
python -m app.cli generate --record-count 75 --dataset-version v20260601
```

Enable optional LLM text enrichment:

```bash
python -m app.cli generate --record-count 75 --dataset-version v20260601 --enable-llm-enrichment
```

The CLI uses the same `DatasetService` and `GenerationPipeline` as the API.

## Testing and Code Quality

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Run linting:

```bash
ruff check .
```

Run static type checks:

```bash
mypy app
```

The test suite covers API contracts, security behavior, caching, generation pipeline behavior, duplicate validation, referential integrity, and business rules.

## Operational Notes

### Database Migrations

Alembic is configured through `alembic.ini` and `alembic/`.

```bash
alembic upgrade head
```

In `development` and `test` environments, the FastAPI lifespan also creates tables automatically for convenience. In production-style deployments, rely on migrations.

### Caching

Read paths use cache keys scoped by dataset version, such as:

```text
dataset:<dataset_version>:...
```

After a dataset generation job completes, the service invalidates that dataset-version cache prefix to avoid stale reads.

### Rate Limiting

Rate limiting is applied as a FastAPI dependency on API routes. Redis is used when available; otherwise the app falls back to in-memory counters.

### Logging and Correlation IDs

Each request receives or propagates an `X-Correlation-ID`. Responses include the same header, and request completion is logged with method, path, status code, and client metadata.

### Error Handling

Production mode hides internal exception details and returns a generic `500` response. Development mode returns exception details to speed up debugging.

## Design Principles

1. Structural data is deterministic.

   IDs, relationships, PNRs, schedules, inventory, and seat assignments are generated by code, not by an LLM.

2. LLM enrichment is optional and non-authoritative.

   LLM output can improve textual realism, but it cannot control foreign keys, primary keys, dates, seats, or inventory.

3. Generated data must be versioned.

   Consumers should query datasets through `dataset_version` to get stable and repeatable results.

4. Validation is part of generation, not an afterthought.

   Each generated dataset receives a stored validation report for traceability.

5. The API should remain usable when optional infrastructure is unavailable.

   SQLite and in-memory cache fallbacks make local development simple.

## Roadmap Ideas

- Replace development-only users with a persistent identity provider.
- Move long-running generation jobs to a background queue such as Celery or RQ.
- Add idempotency keys for generation requests.
- Add job cancellation and retry APIs.
- Export Prometheus or OpenTelemetry metrics.
- Add richer scenario templates for weather, crew, maintenance, and airport disruption simulations.
- Add downloadable dataset exports in CSV, JSONL, or Parquet formats.
