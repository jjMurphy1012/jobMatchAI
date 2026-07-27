# JobMatchAI

AI-assisted job matching for resume-driven job search. The app stores resumes in Supabase Storage, keeps structured career profile data, syncs real company jobs from Greenhouse into PostgreSQL, ranks opportunities with pgvector + OpenAI, and supports interview prep content managed by admins.

## Current Features

- Google OAuth login
- Email registration and login
- Cookie-based access and refresh sessions
- `admin` and `user` roles
- Resume upload, replace, download, and delete
- Supabase Storage resume backend
- Career Profile free-text input with AI field extraction
- Manual Match refresh
- Greenhouse company source configuration and sync
- Opportunity storage in PostgreSQL
- pgvector embeddings for resumes and opportunities
- Structured prefilter + vector recall + batched LLM reranking
- Match list/detail with skill fit and apply state
- Application tracker with a dated stage timeline, manual entries, one-click tracking from a match, stage/type/region filters, and CSV export
- Cover letter generation on demand
- Daily Tasks based on current matches
- Daily match digest emails via SendGrid, with delivery logs and once-per-day idempotency
- Interview Prep library
- Admin user management
- Admin email delivery log and test send
- Admin Greenhouse source management
- Admin interview experience CRUD, review workflow, JSON import, filters

## Main User Flow

1. User signs in with Google or email.
2. User uploads a PDF resume.
3. User fills Career Profile in natural language.
4. Admin configures Greenhouse company sources and syncs jobs.
5. User clicks `Run Match`.
6. Backend ranks synced opportunities and creates matches/tasks.
7. User opens a match, reviews fit, related interview prep, and generates a cover letter only when needed.

## Tech Stack

Backend:
- FastAPI
- SQLAlchemy async
- Alembic
- PostgreSQL + pgvector
- Supabase Storage
- OpenAI embeddings and GPT ranking
- LangChain / LangGraph

Frontend:
- React
- TypeScript
- Vite
- Tailwind CSS
- React Router

Infrastructure:
- Railway backend and frontend services
- Supabase Postgres and Storage
- GitHub auto-deploy

## Local Development

Backend:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Local URLs:
- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/health`
- Backend docs: `http://localhost:8000/docs`

## Required Environment

Minimum backend variables:

```bash
DATABASE_URL=postgresql+asyncpg://...
JWT_SECRET_KEY=change-this
OPENAI_API_KEY=sk-...
FRONTEND_URL=http://localhost:5173
BACKEND_CORS_ORIGINS=http://localhost:5173
```

Recommended production variables:

```bash
STORAGE_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_RESUME_BUCKET=resumes
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://your-frontend-domain/api/auth/google/callback
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax
ADMIN_EMAILS=admin@example.com
```

Full reference:
- [Environment Variables](docs/ENVIRONMENT.md)
- [Auth Setup](docs/AUTH.md)
- [Railway Deployment](RAILWAY_DEPLOYMENT.md)

## OpenAI Key

Yes, the backend needs `OPENAI_API_KEY` for the full product:
- Resume embedding
- Career Profile extraction
- Opportunity embedding during Greenhouse sync
- Match LLM reranking
- Cover letter generation

Without a key, auth and basic CRUD may still start, but resume processing, sync embeddings, matching, and cover letters will fail or degrade.

## Database Migrations

Alembic is used for schema management.

Local:

```bash
cd backend
alembic -c alembic.ini upgrade head
```

Railway:
- The backend Dockerfile runs `alembic -c alembic.ini upgrade head` before Uvicorn starts.
- You can confirm current DB revision in Supabase:

```sql
select version_num from alembic_version;
```

## Greenhouse Sync

Admins configure company sources in Admin:
- `source_type`: `greenhouse`
- `company_name`: display name
- `board_token`: Greenhouse board token, for example `airbnb`

Sync behavior:
- Fetches Greenhouse Job Board API
- Upserts jobs into `opportunities`
- Marks missing jobs closed
- Stores sync logs
- Generates opportunity embeddings when possible

## Matching Pipeline

Current pipeline:

1. Load latest resume and Career Profile effective fields.
2. Load open synced opportunities.
3. Use structured filters for company exclusions, internship intent, keywords, location, and remote preference.
4. Use resume embedding to recall opportunity embeddings.
5. Rank candidates and keep a bounded top-N.
6. Batch LLM rerank candidates.
7. Save `UserJobMatch` rows and Daily Tasks.
8. Generate cover letter only when user clicks `Generate`.

Default knobs:

```bash
MATCH_THRESHOLD=70
MIN_THRESHOLD=30
THRESHOLD_STEP=5
TARGET_JOBS=10
MATCH_LLM_RERANK_LIMIT=20
MATCH_LLM_BATCH_SIZE=10
```

## API Overview

Auth:
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/auth/refresh`
- `GET /api/auth/me`
- `GET /api/auth/google/login`
- `GET /api/auth/google/callback`

Applications:
- `GET /api/applications`
- `GET /api/applications/export`
- `POST /api/applications`
- `PATCH /api/applications/{id}`
- `DELETE /api/applications/{id}`
- `POST /api/applications/{id}/events`
- `DELETE /api/applications/{id}/events/{event_id}`

Resume:
- `GET /api/resume`
- `POST /api/resume`
- `DELETE /api/resume`

Career Profile:
- `GET /api/preferences`
- `POST /api/preferences`
- `POST /api/preferences/analyze`
- `PATCH /api/preferences/fields`

Matches:
- `GET /api/jobs`
- `GET /api/jobs/{id}`
- `POST /api/jobs/refresh`
- `POST /api/jobs/{id}/cover-letter`
- `PUT /api/jobs/{id}/apply`

Interview Prep:
- `GET /api/interview-experiences`

Admin:
- `GET /api/admin/users`
- `PATCH /api/admin/users/{id}/role`
- `GET /api/admin/company-sources`
- `POST /api/admin/company-sources`
- `PATCH /api/admin/company-sources/{id}`
- `PATCH /api/admin/company-sources/{id}/deactivate`
- `POST /api/admin/company-sources/{id}/sync`
- `GET /api/admin/source-sync-runs`
- `GET /api/admin/interview-experiences`
- `POST /api/admin/interview-experiences`
- `POST /api/admin/interview-experiences/import`
- `PATCH /api/admin/interview-experiences/{id}`
- `PATCH /api/admin/interview-experiences/{id}/status`
- `DELETE /api/admin/interview-experiences/{id}`

## Scheduler

Scheduler is intentionally disabled by default:

```bash
ENABLE_SCHEDULER=false
```

Only enable it on a dedicated scheduler/worker instance later:

```bash
ENABLE_SCHEDULER=true
```

Do not enable scheduler on every web replica.

## Status

Completed:
- P0 infrastructure and profile refactor
- P1 Auth/RBAC/stability
- P2 core data model and IA
- P2.5 frontend visual consistency
- P3 Greenhouse integration
- P4 matching pipeline upgrade
- P5 interview prep workflow, filters, match association, import

Deferred:
- Forgot Password
- Email verification strategy
- Dedicated scheduler/worker
- Redis/arq evaluation
- Monitoring, audit logs, email notifications
