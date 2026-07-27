# Environment Variables

This project has two services:
- Backend: FastAPI
- Frontend: Vite build served behind Nginx on Railway

The frontend does not need an API URL override in the current deployment shape. It calls `/api/...`, and Nginx proxies those requests to the backend with `BACKEND_URL`.

## Backend Required

| Variable | Required | Example | Notes |
|---|---:|---|---|
| `DATABASE_URL` | yes | `postgresql+asyncpg://postgres.xxx:...@aws-...pooler.supabase.com:5432/postgres` | Must use asyncpg driver prefix. |
| `JWT_SECRET_KEY` | yes | long random string | Required when `DEBUG=false`. |
| `OPENAI_API_KEY` | yes | `sk-...` | Needed for extraction, embeddings, matching, cover letters. |
| `FRONTEND_URL` | yes | `https://your-frontend.up.railway.app` | Used by auth redirects and app links. |
| `BACKEND_CORS_ORIGINS` | yes | `https://your-frontend.up.railway.app` | Comma-separated origins. |

## Backend Auth

| Variable | Default | Notes |
|---|---|---|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access cookie lifetime. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh cookie lifetime. |
| `AUTH_COOKIE_DOMAIN` | empty | Usually empty on Railway. |
| `AUTH_COOKIE_SECURE` | `false` | Use `true` in production HTTPS. |
| `AUTH_COOKIE_SAMESITE` | `lax` | Keep `lax` for same-site frontend proxy flow. |
| `ACCESS_COOKIE_NAME` | `jobmatch_access_token` | Cookie name. |
| `REFRESH_COOKIE_NAME` | `jobmatch_refresh_token` | Cookie name. |
| `OAUTH_STATE_COOKIE_NAME` | `jobmatch_oauth_state` | Google OAuth CSRF state cookie. |
| `AUTH_RATE_LIMIT_MAX_REQUESTS` | `10` | Login/register rate limit. |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window. |
| `GOOGLE_CLIENT_ID` | empty | Required for Google OAuth. |
| `GOOGLE_CLIENT_SECRET` | empty | Required for Google OAuth. |
| `GOOGLE_REDIRECT_URI` | local callback | Must match Google Console exactly. |
| `ADMIN_EMAILS` | empty | Comma-separated emails promoted/treated as admins. |

## Backend Storage

| Variable | Default | Notes |
|---|---|---|
| `STORAGE_BACKEND` | `local` | Use `supabase` in production. |
| `LOCAL_STORAGE_DIR` | `uploads` | Local development only. |
| `SUPABASE_URL` | empty | Required for Supabase Storage. |
| `SUPABASE_SERVICE_ROLE_KEY` | empty | Required for server-side Storage access. |
| `SUPABASE_RESUME_BUCKET` | `resumes` | Bucket for resume files. |
| `SUPABASE_SIGNED_URL_TTL_SECONDS` | `3600` | Download link TTL. |

## Matching

| Variable | Default | Notes |
|---|---:|---|
| `MATCH_THRESHOLD` | `70` | Initial minimum match score. |
| `MIN_THRESHOLD` | `30` | Lowest adaptive threshold. |
| `THRESHOLD_STEP` | `5` | Adaptive threshold decrement. |
| `TARGET_JOBS` | `10` | Desired saved matches. |
| `MATCH_LLM_RERANK_LIMIT` | `20` | Max candidates sent to LLM reranker. |
| `MATCH_LLM_BATCH_SIZE` | `10` | Jobs per LLM ranking batch. |

## Scheduler

| Variable | Default | Notes |
|---|---:|---|
| `ENABLE_SCHEDULER` | `false` | Keep false on web service. Enable on exactly one worker. |
| `PUSH_HOUR` | `7` | Hour of the daily match run and digest email. |
| `PUSH_MINUTE` | `0` | Minute of the daily match run. |
| `TIMEZONE` | `America/New_York` | Scheduler timezone, also used for digest idempotency dates. |

## Email Notifications

| Variable | Default | Notes |
|---|---:|---|
| `EMAIL_NOTIFICATIONS_ENABLED` | `false` | Master switch. When false, sends are recorded as `skipped`. |
| `SENDGRID_API_KEY` | none | SendGrid API key with Mail Send permission. |
| `SENDGRID_FROM_EMAIL` | none | Verified sender address. Required to send. |
| `SENDGRID_FROM_NAME` | `JobMatchAI` | Display name on outgoing mail. |
| `SENDGRID_API_BASE_URL` | `https://api.sendgrid.com` | Override for testing. |
| `SENDGRID_SANDBOX_MODE` | `false` | Validate requests without delivering mail. |
| `SENDGRID_TIMEOUT_SECONDS` | `15.0` | Per-request HTTP timeout. |
| `EMAIL_MAX_ATTEMPTS` | `3` | Attempts before a send is marked failed. |
| `EMAIL_RETRY_BACKOFF_SECONDS` | `1.0` | Base delay for exponential backoff. |
| `EMAIL_DIGEST_MAX_MATCHES` | `5` | Matches listed in one digest email. |

Per-user opt-in lives on the career profile (`reminder_enabled`, `reminder_email`);
`reminder_email` falls back to the account email when unset.

## Optional / Legacy

| Variable | Notes |
|---|---|
| `RAPIDAPI_KEY` | Legacy fallback path only. |
| `LINKEDIN_EMAIL` / `LINKEDIN_PASSWORD` | Legacy, no longer required for primary flow. |

## Frontend

| Variable | Required | Notes |
|---|---:|---|
| `BACKEND_URL` | production yes | Backend public URL used by Nginx `/api` proxy. |
| `PORT` | Railway sets | Nginx listen port. |

`VITE_API_URL` is not required by the current frontend code.
