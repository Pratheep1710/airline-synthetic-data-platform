# Airline Synthetic Data Platform
## Technical and Business Flow Document

## 1. Purpose and Scope
This document defines the end-to-end business and technical flow of the Airline Synthetic Data Platform, from dataset generation request through validation, persistence, and API consumption.

It covers:
- Business lifecycle and stakeholder value flow
- Technical stage-by-stage processing flow
- Technology mapping per stage
- Security, validation, caching, and observability controls
- Deployment and operational runbook context

---

## 2. Business Context and Objectives
The platform exists to generate realistic synthetic airline datasets for:
- Product engineering and QA
- Data science experimentation
- API integration testing
- Operational simulation and reporting

Primary business requirements:
- Data must be realistic and logically consistent
- Data must maintain strict relational integrity
- IDs and references must be deterministic and controlled by code
- LLM usage must be optional and strictly limited to non-structural text enrichment
- All dataset access must be secure and auditable

---

## 3. Stakeholders and Responsibilities
- Product Owner: Defines business realism expectations and use-case priorities
- Backend Engineering: Implements generation, validation, persistence, and APIs
- QA/Validation Team: Verifies rule correctness and API contracts
- Security/Platform Team: Oversees auth, scope boundaries, and runtime posture
- Data Consumers: Use dataset/versioned APIs for testing and analytics

---

## 4. Business Process Flow (High-Level)
1. User authenticates and receives scoped JWT.
2. User requests dataset generation (`record_count`, optional LLM enrichment).
3. Platform creates a generation job and executes the deterministic generation pipeline.
4. Platform validates generated data using schema, duplicate, referential, business, and realism checks.
5. Platform stores generated entities and validation report under a dataset version.
6. User and downstream systems consume versioned APIs with pagination/filtering.
7. Cached read paths improve performance.
8. Audit and correlation metadata support traceability.

---

## 5. Technical Architecture Flow
```text
Client (Swagger/cURL/Service)
   |
   v
FastAPI API Layer (routing, auth dependency, rate limit dependency)
   |
   +--> DatasetService
   |      |
   |      +--> GenerationPipeline
   |      |      1) Catalog load
   |      |      2) Deterministic IDs
   |      |      3) Aircraft generation
   |      |      4) Flight generation
   |      |      5) Booking generation
   |      |      6) Manage-travel generation
   |      |      7) IROP generation
   |      |      8) Optional LLM enrichment
   |      |      9) Validation
   |      |     10) Deterministic repair loop
   |      |
   |      +--> SQLAlchemy Session (SQLite/PostgreSQL)
   |
   +--> Domain Read Services (aircraft, flight, booking, MT, IROP)
          |
          +--> Redis Cache (or in-memory fallback)
```

---

## 6. Stage-by-Stage Flow with Technology Mapping

| Stage | Business Purpose | Technical Action | Technology |
|---|---|---|---|
| 0. API Entry | Accept generation request | Validate payload, auth, scope checks, rate-limit checks | FastAPI, Pydantic v2, OAuth2PasswordBearer, JWT, custom rate limiter |
| 1. Job Creation | Track request lifecycle | Create `DatasetGenerationJob` with status `RUNNING` | SQLAlchemy 2.x models/repositories |
| 2. Catalog Loading | Guarantee realistic baseline | Load airports, routes, seat maps, baggage rules, meals, SSR | Python in-memory catalogs (`app/generation/catalogs.py`) |
| 3. Deterministic ID Generation | Prevent key chaos | Generate AC/FLT/BKG/PNR/MT/IROP IDs in deterministic patterns | Custom ID generator (`id_generator.py`) |
| 4. Aircraft Generation | Build fleet inventory | Generate unique aircraft records with type/seat_map/status | Deterministic generator + SQLAlchemy models |
| 5. Flight Generation | Build sellable schedule | Assign valid aircraft, route, times, inventories, statuses; avoid overlap | Deterministic scheduling logic + timezone handling |
| 6. Booking Generation | Build demand layer | Generate PNR bookings only on sellable flights, assign valid seats | Deterministic logic + seat-map pools + inventory controls |
| 7. Manage Travel Generation | Simulate post-booking actions | Generate seats/bags/meals/hotel/car only for valid booking states | Deterministic logic + business constraints |
| 8. IROP Generation | Simulate disruptions | Generate delay/cancel/diversion events referencing valid flights | Event-type logic + operational messaging fields |
| 9. Optional LLM Enrichment | Improve textual realism | Enrich names/messages/notes only; no PK/FK/seat/time edits | Abstract LLM client + mock fallback + optional OpenAI client |
| 10. Validation | Ensure trustworthiness | Execute schema, duplicate, referential, business, realism validators | `jsonschema`, custom validators, validation report dataclass |
| 11. Repair Loop | Auto-correct deterministic failures | Repair deterministic rule breaks; text-only message improvement | Pipeline repair logic |
| 12. Persistence & Completion | Publish dataset version | Commit entities + validation report, mark job status | SQLAlchemy transaction, dataset service |
| 13. Cache Invalidation | Avoid stale reads | Invalidate dataset-version cache prefix | Redis cache client |
| 14. Retrieval APIs | Serve consumers | Paginated/filterable query APIs by entity/version | FastAPI routes + service/repository pattern + cache |

---

## 7. Dataset Dependency Order (Implemented Flow)
1. Airport catalog  
2. Aircraft type catalog  
3. Seat map catalog  
4. Baggage rule catalog  
5. Available aircrafts  
6. Available flights  
7. Bookings  
8. Manage travel  
9. IROPs  

This order is enforced by generator orchestration so downstream entities always reference already-created upstream entities.

---

## 8. Data Integrity and Control Boundaries
### Deterministic/Code-Controlled Fields
- Primary keys (`aircraft_id`, `flight_id`, `booking_id`, `manage_travel_id`, `irop_id`)
- Foreign/reference keys (`flight.aircraft_id`, `booking.flight_id`, `manage_travel.pnr`, `irop.flight_id`)
- PNR generation
- Seat assignments
- Inventory counts
- Schedule ordering and duration structure

### LLM-Allowlisted Fields
- Passenger first/last names
- Customer-facing disruption messages
- Operational notes
- Recovery actions
- Select hotel/car descriptive metadata

### LLM-Blocked Fields
- All IDs, PK/FK fields, PNR, seat numbers
- Inventory values
- Flight timing structure/order
- Controlled airport/route code space

---

## 9. Validation and Quality Gate Flow
Validation executes in this sequence:
1. JSON Schema validation (entity-level shape/type constraints)
2. Duplicate validation (ID/PNR uniqueness checks)
3. Referential integrity validation (FK-like cross-entity checks)
4. Business rule validation (time, duration, overlap, seat, baggage, overbooking, event consistency)
5. Realism scoring (0–100 heuristic quality score)

Output contract:
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

Pass/fail business decision:
- Job is functionally successful when generation completes and report is stored.
- Validation status is `PASSED` only when core checks pass and duplicates are zero.

---

## 10. Security Flow
### Authentication
- OAuth2 password flow token endpoint: `/api/v1/auth/token`
- JWT bearer token validation on protected endpoints

### Authorization Scopes
- `dataset:read`
- `dataset:generate`
- `validation:read`
- `admin`

### Enforcement
- All `/api/v1` routes are protected except `/health`.
- Route-level scope dependencies gate access.
- Rate limiting is applied via dependency middleware.
- Correlation ID is attached per request for traceability.

---

## 11. API Consumption Flow
1. Authenticate and obtain access token.
2. Create dataset job.
3. Poll job status or list datasets.
4. Query versioned entity endpoints with pagination/filtering/sorting.
5. Retrieve validation report for governance and confidence.

Pagination controls:
- `page`, `page_size`, `sort_by`, `sort_dir`
- Default page size: 25
- Maximum page size: 100

---

## 12. Caching Flow
### Cache Targets
- Aircraft list/detail
- Flight list/search/detail
- Booking by PNR
- IROPs by flight/detail
- Validation report

### Key Design
- Stable, dataset-version scoped keys
- Filter-sensitive hash keying for flight search

### Invalidation
- Triggered after successful dataset generation completion
- Prefix invalidation per dataset version

Fallback mode:
- If Redis is unavailable, in-memory fallback cache is used so app remains functional.

---

## 13. Persistence and Transaction Flow
Storage layer:
- SQLAlchemy ORM models
- Repository abstraction for CRUD/list patterns
- Alembic migrations for schema evolution

Transaction behavior:
- Job and entity writes occur in transactional unit
- On failure, status is updated to `FAILED` with error payload
- On success, status and validation metadata are committed

---

## 14. Observability and Error Handling
- Structured JSON logging with request correlation ID
- Secure production error responses (no stack trace leakage in production mode)
- Explicit HTTP status codes (`401`, `403`, `404`, `409`, `422`, `429`, `500`)
- Validation and business failures captured in report for auditability

---

## 15. Deployment Topologies
### Local (No Docker, No Postgres)
- SQLite (`sqlite+pysqlite:///./airline_synth.db`)
- Optional Redis, with in-memory fallback
- Fast iteration path for development

### Containerized
- FastAPI + PostgreSQL + Redis via Docker Compose
- Internal hostnames (`postgres`, `redis`) valid only inside Docker network

### Production Target Pattern
- PostgreSQL primary datastore
- Redis for cache and burst-read performance
- Environment-managed secrets and keys

---

## 16. Operational Runbooks (Practical)
### Run Flow
1. Configure `.env`
2. Start dependencies
3. Run migrations
4. Start API
5. Authenticate
6. Generate dataset
7. Query versioned endpoints

### Common Failure Patterns
- `401 Not authenticated`: token missing/expired
- `403 Missing scope`: wrong user scope for endpoint
- SQLite lock/integrity issues under rapid retries: restart app and ensure one active generation per process
- Docker hostname resolution from host: use `localhost` outside containers

---

## 17. Compliance with Core Design Principle
The platform architecture enforces this principle:
- Relational structure and referential correctness are code-owned and deterministic.
- LLM is enrichment-only and non-authoritative for structural integrity.

This ensures:
- Reproducibility
- Data quality confidence
- Safe AI integration without relational drift

---

## 18. Current Implementation Mapping (File-Level)
- API routes: `app/api/*.py`
- Core platform controls: `app/core/*.py`
- Models/session/repositories: `app/db/*.py`
- Deterministic generation: `app/generation/*.py`
- Validation stack: `app/validation/*.py`
- Domain services: `app/services/*.py`
- Schemas: `app/schemas/*.py`
- JSON schemas: `json_schemas/*.schema.json`
- Migrations: `alembic/*`
- Tests: `app/tests/*`

---

## 19. Recommended Next Enhancements
- Move demo in-memory users to persistent identity provider
- Add background job queue (Celery/RQ) for long-running generation requests
- Add idempotency key support for generation API
- Add explicit job cancellation endpoint
- Add metrics export (Prometheus/OpenTelemetry) for SLO tracking
