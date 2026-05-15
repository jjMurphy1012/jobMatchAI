# Railway Quick Start

Use this when deploying a fresh environment.

## Services

Create two Railway services:

1. Backend
   - GitHub repo
   - Root directory: `backend`
2. Frontend
   - Same GitHub repo
   - Root directory: `frontend`

Use Supabase for Postgres and Storage.

## Supabase

Run once in Supabase SQL Editor:

```sql
create extension if not exists vector;
```

Create Storage bucket:

```text
resumes
```

## Backend Variables

```bash
DATABASE_URL=postgresql+asyncpg://...
JWT_SECRET_KEY=<long-random-secret>
OPENAI_API_KEY=sk-...
FRONTEND_URL=https://your-frontend.up.railway.app
BACKEND_CORS_ORIGINS=https://your-frontend.up.railway.app

STORAGE_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_RESUME_BUCKET=resumes

AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax
ADMIN_EMAILS=you@example.com
```

Optional Google OAuth:

```bash
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://your-frontend.up.railway.app/api/auth/google/callback
```

## Frontend Variables

```bash
BACKEND_URL=https://your-backend.up.railway.app
```

## Verify

Backend:

```text
https://your-backend.up.railway.app/health
```

Supabase:

```sql
select version_num from alembic_version;
```

App:

1. Open frontend URL.
2. Register/login.
3. Upload resume.
4. Fill Career Profile.
5. Admin adds Greenhouse source and syncs.
6. User runs Match.

Full details: [Railway Deployment](RAILWAY_DEPLOYMENT.md)
