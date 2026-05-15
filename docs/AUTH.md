# Auth Setup

The app supports:
- Google OAuth
- Email registration/login
- Access + refresh cookie sessions
- `admin` and `user` roles
- Login/register rate limiting

## Cookie Session Model

On login, the backend sets:
- `jobmatch_access_token`
- `jobmatch_refresh_token`

The frontend calls APIs with `credentials: include`. When an API returns `401`, the frontend attempts `POST /api/auth/refresh` once and retries the request.

Production settings should include:

```bash
JWT_SECRET_KEY=<long-random-secret>
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax
```

Usually leave `AUTH_COOKIE_DOMAIN` empty on Railway unless frontend/backend are intentionally sharing a parent custom domain.

## Google OAuth

Google Console setup:

1. Create OAuth client.
2. Application type: Web application.
3. Add authorized redirect URI:

```text
https://your-frontend-domain/api/auth/google/callback
```

4. Set backend variables:

```bash
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://your-frontend-domain/api/auth/google/callback
FRONTEND_URL=https://your-frontend-domain
```

Why frontend domain for callback:
- The deployed frontend proxies `/api/auth/google/callback` to the backend.
- Cookies stay aligned with the browser-facing origin.

## Email Login

Endpoints:
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/auth/refresh`
- `GET /api/auth/me`

Forgot Password and email verification are not implemented yet.

## Admin Role

Admins can:
- Manage users
- Configure Greenhouse company sources
- Sync opportunities
- Manage interview experiences

Admin bootstrap options:
- Set `ADMIN_EMAILS=admin@example.com,other@example.com`
- Or promote a user from Admin UI using an existing admin account.

Protection rules:
- Admin cannot remove their own admin role.
- Disabled users cannot use protected routes.

## Rate Limiting

Auth endpoints use in-process rate limiting:

```bash
AUTH_RATE_LIMIT_MAX_REQUESTS=10
AUTH_RATE_LIMIT_WINDOW_SECONDS=60
```

This is acceptable for a single web instance. If the app scales horizontally, replace it with Redis-backed rate limiting.
