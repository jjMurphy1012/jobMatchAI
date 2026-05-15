# Railway Deployment

Current production shape:
- Backend Railway service from `/backend`
- Frontend Railway service from `/frontend`
- Supabase Postgres with pgvector
- Supabase Storage for resumes

The backend Dockerfile runs Alembic automatically before Uvicorn starts:

```bash
alembic -c alembic.ini upgrade head
```

## 1. Supabase Setup

Create a Supabase project.

Enable pgvector:

```sql
create extension if not exists vector;
```

Create a private Storage bucket:

```text
resumes
```

Copy:
- Project URL
- Service role key
- Database connection string

Use the Session Pooler or direct connection string with SQLAlchemy asyncpg prefix:

```text
postgresql+asyncpg://...
```

If Supabase gives:

```text
postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres
```

convert it to:

```text
postgresql+asyncpg://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres
```

For pooler usernames such as `postgres.projectref`, keep the username exactly as Supabase provides it.

## 2. Backend Service

Railway:

1. New service from GitHub repo.
2. Root directory: `backend`.
3. Generate public domain.
4. Add variables.

Required variables:

```bash
DATABASE_URL=postgresql+asyncpg://...
JWT_SECRET_KEY=<long-random-secret>
OPENAI_API_KEY=sk-...
FRONTEND_URL=https://your-frontend.up.railway.app
BACKEND_CORS_ORIGINS=https://your-frontend.up.railway.app
```

Production recommended:

```bash
DEBUG=false
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax
STORAGE_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_RESUME_BUCKET=resumes
ADMIN_EMAILS=you@example.com
```

Google OAuth:

```bash
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://your-frontend.up.railway.app/api/auth/google/callback
```

Do not set `ENABLE_SCHEDULER=true` on the web service.

## 3. Frontend Service

Railway:

1. New service from same GitHub repo.
2. Root directory: `frontend`.
3. Generate public domain.
4. Add variables:

```bash
BACKEND_URL=https://your-backend.up.railway.app
```

The frontend calls `/api/...`; Nginx proxies to `BACKEND_URL`.

## 4. Verify Deployment

Backend health:

```text
https://your-backend.up.railway.app/health
```

Backend logs should include:

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO:     Uvicorn running on http://0.0.0.0:...
```

Confirm Alembic version in Supabase:

```sql
select version_num from alembic_version;
```

Frontend:

```text
https://your-frontend.up.railway.app
```

## 5. Post-Deploy Checklist

1. Register or Google-login as the admin email.
2. Confirm `/api/auth/me` succeeds in browser app.
3. Upload a PDF resume.
4. Fill Career Profile.
5. Admin: add Greenhouse source, for example:

```text
company_name=Airbnb
board_token=airbnb
source_type=greenhouse
```

6. Admin: click Sync.
7. User: click Run Match.
8. Open a match and generate cover letter on demand.
9. Admin: import/publish interview experiences.
10. Confirm related interview prep appears on matching jobs.

## Troubleshooting

### Supabase project paused

Resume the Supabase project from the Supabase dashboard. Railway backend logs may show DNS or tenant errors while the project is paused.

### Pooler tenant/user not found

Use the exact Supabase pooler username. For pooler URLs this often looks like:

```text
postgres.<project-ref>
```

### Backend starts but DB is old

Check:

```sql
select version_num from alembic_version;
```

If needed, run from local project with Railway CLI:

```bash
cd backend
npx @railway/cli run alembic -c alembic.ini upgrade head
```

### Google login redirect mismatch

The value in Google Console must exactly match:

```text
GOOGLE_REDIRECT_URI
```

Recommended:

```text
https://your-frontend-domain/api/auth/google/callback
```

### Resume upload fails

Check:
- `STORAGE_BACKEND=supabase`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_RESUME_BUCKET`
- Bucket exists in Supabase Storage.

### Match fails

Check:
- `OPENAI_API_KEY`
- Resume exists and was processed
- Career Profile exists
- At least one active company source has synced opportunities
- Supabase has `vector` extension enabled

### Greenhouse sync has no embeddings

Sync can still succeed if embedding generation fails. Verify `OPENAI_API_KEY`; then re-run source sync.
