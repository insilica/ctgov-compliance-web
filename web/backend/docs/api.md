# Backend API Contract

The backend Flask application now lives entirely under `web/backend/`:

- `web/backend/main.py` – ASGI entry point (`uvicorn web.backend.main:app --reload`)
- `web/backend/api/` – Flask blueprints, request handlers, and response schema
  definitions.
- `web/backend/services/` – Domain/business logic that powers the routes.
- `web/backend/repositories/` – Database access helpers and query builders.

## Running the backend

```bash
cp .env.example .env
source .env            # or export the vars manually
./scripts/dev_backend.sh
```

`dev_backend.sh` simply invokes `flask --app web.app run`, but you can also run
the service via ASGI with `uvicorn web.backend.main:app`.

## Internal response models

Pydantic models (defined in `web/backend/api/schema.py`) document the contract
between repositories/services and the HTTP transport layer. The currently
implemented models are:

| Model | Purpose |
| --- | --- |
| `HealthResponse` | Canonical JSON payload for `/health`. |
| `AutocompleteResponse` | Typed list of suggestions for all autocomplete endpoints. |
| `TrialSummary` | Normalizes trial data returned to CSV export, reports, and dashboards. |

These models provide a single source of truth for field names and types so that
`QueryManager` can evolve independently of any specific transport format.

## HTTP surface area

The OpenAPI summary lives at `web/shared/contracts/openapi.yaml`. Handlers are
grouped by concern:

| Blueprint | Module | Routes |
| --- | --- | --- |
| `auth` | `web/backend/api/auth.py` | `/login`, `/register`, password reset flows, session management. |
| `routes` | `web/backend/api/routes.py` | Dashboards, autocomplete APIs, CSV export, and printable reports. |

Every route should either return a Pydantic model instance (serialized through
`model_dump`) or delegate to a service that eventually does so. When adding new
routes, update both this document and the OpenAPI spec so frontend generators
stay in sync.
