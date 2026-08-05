# 🚀 AutoFlow AI

> Build, compile, and run AI automation workflows from plain-English prompts.

AutoFlow AI is a metadata-driven automation platform. Describe what you want in
natural language, and the AI planner turns it into a structured workflow plan;
the prompt compiler lowers it to an executable workflow specification; and the
workflow runtime executes it — all orchestrated through a 26-connector
integration framework and a metadata-driven event bus.

The entire backend is **generated from YAML metadata** (see
`scripts/generators/FROZEN.md` for the frozen generator list).

---

## ✨ Features

- **AI Planner** — 11-stage pipeline (intent → entities → tasks → discovery →
  capability matching → constraints → graph → validation → optimizer →
  estimators → plan) with provider abstraction (OpenAI / Anthropic / Gemini /
  DeepSeek / OpenRouter) and deterministic offline fallback.
- **Prompt Compiler** — plan → AST → IR → workflow specification v1, with
  condition/loop/variable support, versioning, and serialization (JSON/YAML/
  binary).
- **Workflow Runtime** — executor, scheduler, worker pool, locks, monitor,
  checkpoints, retry policies and execution states.
- **Connector Framework** — 26 connectors (Slack, GitHub, Notion, Stripe,
  PostgreSQL, Redis, …) with OAuth2/API-key/Bearer/JWT/Basic auth, webhook and
  polling triggers, retry, circuit breaking, rate limiting, and observability.
- **Event Bus** — metadata-configured publish/subscribe with persistence,
  replay, retry with backoff, dead-lettering, versioning, and idempotency.
- **REST API** — FastAPI with 130+ routes, JWT auth (bcrypt + HS256), scoped
  authorization, multi-tenant isolation, rate limiting, security headers, and
  audit logging.
- **React frontend** — Next.js 15 App Router, Tailwind, TanStack Query, Zustand,
  framer-motion, and a visual XYFlow workflow builder.
- **Metadata-driven generators** — `scripts/generate.py` regenerates backend
  modules from `metadata/**/*.yaml`; every generator is validated by a pipeline.

---

## 🏗 Architecture

```
                        ┌──────────────────────┐
                        │   Next.js frontend    │   :3000
                        │ (builder / dashboard) │
                        └──────────┬───────────┘
                                   │ REST (JWT)
                        ┌──────────▼───────────┐
                        │   FastAPI backend    │   :8000
                        └──────────┬───────────┘
        ┌──────────────────────────┼───────────────────────────┐
        ▼              ▼           ▼           ▼               ▼
   AI Planner    Prompt Compiler  Runtime    Connectors     Event Bus
   (metadata/   (metadata/       (metadata/ (metadata/      (metadata/
    ai)          compiler)        runtime)   connectors)     events)
        └──────────────────────────┼───────────────────────────┘
                                   ▼
                     ┌──────────────────────────┐
                     │  PostgreSQL  +   Redis    │
                     └──────────────────────────┘
```

Modules in `backend/app/`:

| Module | Purpose |
|--------|---------|
| `ai/` | Planner pipeline + LLM providers |
| `compiler/` | Plan → AST → IR → WorkflowSpecification |
| `runtime/` | Executor, scheduler, workers, monitors |
| `connectors/` | 26-connector framework (auth, triggers, actions, resilience) |
| `events/` | Metadata-driven event bus + handlers |
| `middleware/` | 15-middleware stack (request ID → compression) |
| `api/v1/` | Routers, dependencies, pagination |
| `models|schemas|services|repositories/` | CRUD layers (generated) |
| `core/` | Config, database, cache, security |

---

## 🚀 Getting Started

### Option A — Docker (recommended)

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000 (docs at http://localhost:8000/docs)
- Postgres: `localhost:5432` · Redis: `localhost:6379`

### Option B — Local development

**Backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env          # then edit values
uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

The frontend uses **mock data by default** (`NEXT_PUBLIC_MOCK=true`). Point it at
the real API with:

```bash
cp .env.example frontend/.env.local   # then set NEXT_PUBLIC_MOCK=false
```

---

## 🔐 Authentication

Real JWT authentication backed by bcrypt password hashing:

- `POST /api/v1/auth/register` · `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh` · `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me` · `POST /api/v1/auth/password-change`
- `POST /api/v1/auth/password-reset` (generates a signed token; email delivery
  requires wiring a provider)
- `GET /api/v1/auth/oauth/{provider}` returns `501` until OAuth client
  credentials are configured.

All protected routes accept `Authorization: Bearer <token>`.

---

## 🧠 AI Pipeline

```
User prompt → Intent → Entities → Tasks → Connector discovery →
Capability matching → Constraints → Graph (DAG) → Validation → Optimization →
Plan → Compiler → WorkflowSpecification → Runtime DAG → Execution
```

With no LLM provider configured, the planner falls back to deterministic
heuristics so the full pipeline works offline (used by the test suite).

---

## 🧪 Testing & Validation

Backend (all tests run from the repo root; `pytest.ini` already sets
`pythonpath = backend`):

```bash
python -m pytest -q                       # 830 tests (137 DB-dependent skips)
```

Per-domain validation pipelines:

```bash
python scripts/validate_events.py         # event bus (9 steps)
python scripts/validate_runtime.py        # runtime (11 steps)
python scripts/validate_connectors.py     # connectors (11 steps)
python scripts/validate_ai_planner.py     # planner (11 steps)
python scripts/validate_compiler.py       # compiler (12 steps)
```

Frontend:

```bash
cd frontend
npx tsc --noEmit                          # typecheck
npx eslint .                              # lint
npm run build                             # production build
```

Metadata validation (whole tree):

```bash
python -c "import sys; sys.path.insert(0,'.'); \
from scripts.generators.common.metadata_loader import MetadataLoader; \
from scripts.generators.common.metadata_validator import MetadataValidator; \
m = MetadataLoader('metadata').load_all(); v = MetadataValidator(m); \
v.validate_all(); print(v.errors or 'metadata OK')"
```

---

## ⚙️ Code Generation

All backend modules are generated from `metadata/**/*.yaml`:

```bash
python scripts/generate.py --list            # available generators
python scripts/generate.py backend --dry-run # preview
python scripts/generate.py backend --force   # regenerate
```

Frozen generators (do not modify without re-running their validation pipeline):
`services`, `middleware`, `event_bus`, `runtime`, `connectors`, `ai`, `compiler`.
See `scripts/generators/FROZEN.md`.

---

## 🔑 Environment Variables

See `.env.example` for the complete list. Key variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `DATABASE_URL` | Async PostgreSQL DSN | local `autoflow` db |
| `REDIS_URL` | Redis for cache/celery | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing secret | dev value (change in prod!) |
| `ENVIRONMENT` / `DEBUG` / `LOG_LEVEL` | Runtime mode | development / true / DEBUG |
| `OPENAI_API_KEY` … `OPENROUTER_API_KEY` | LLM providers (optional) | — |
| `SENTRY_DSN` | Error tracking (optional) | — |
| `NEXT_PUBLIC_API_URL` | Frontend → backend base URL | `http://localhost:8000/api/v1` |
| `NEXT_PUBLIC_MOCK` | Frontend mock-data mode | `true` |

---

## 📖 Documentation

- `docs/ai_planner.md` · `docs/compiler.md` · `docs/runtime.md` ·
  `docs/connectors.md` · `docs/events.md` · `docs/middleware.md` ·
  `docs/frontend.md`
- `METADATA_GUIDE.md` — metadata authoring guide
- `scripts/generators/FROZEN.md` — frozen generator status
- Interactive API docs: `/docs` (Swagger) · `/redoc`

---

## 🚢 Deployment

- **Docker**: `docker compose up --build` (Postgres + Redis + backend + frontend).
- **Backend**: build `backend/` with its `Dockerfile`; run migrations (the app
  auto-creates tables at startup via `Base.metadata.create_all` — introduce
  Alembic migrations before heavy production use).
- **Frontend**: deploy `frontend/` to Vercel (`npm run build`), setting
  `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_MOCK=false`.
- **CI**: `.github/workflows/ci.yml` runs backend tests + validations and
  frontend typecheck/lint/build on every push.

---

## 📄 License

MIT
