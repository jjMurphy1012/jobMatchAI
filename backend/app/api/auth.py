from urllib.parse import quote

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import InMemoryRateLimiter
from app.core.security import generate_refresh_token
from app.models.models import User
from app.services.auth_service import auth_service

router = APIRouter()
auth_rate_limiter = InMemoryRateLimiter()


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str | None
    avatar_url: str | None
    role: str
    is_disabled: bool


class LogoutResponse(BaseModel):
    message: str


def _frontend_error_redirect(error_code: str) -> str:
    return f"{settings.FRONTEND_URL}/login?error={quote(error_code)}"


@router.get("/google/login")
async def start_google_login(request: Request):
    auth_rate_limiter.enforce(
        request=request,
        bucket="google_login",
        limit=settings.AUTH_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )
    state = generate_refresh_token()
    response = RedirectResponse(auth_service.build_google_login_url(state), status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=settings.OAUTH_STATE_COOKIE_NAME,
        value=state,
        max_age=10 * 60,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path="/",
    )
    return response


@router.get("/google/callback")
async def complete_google_login(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    stored_state: str | None = Cookie(default=None, alias=settings.OAUTH_STATE_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    auth_rate_limiter.enforce(
        request=request,
        bucket="google_callback",
        limit=settings.AUTH_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )
    if not code or not state or not stored_state or stored_state != state:
        response = RedirectResponse(_frontend_error_redirect("oauth_state_mismatch"), status_code=status.HTTP_302_FOUND)
        auth_service.clear_auth_cookies(response)
        return response

    try:
        token_payload = await auth_service.exchange_code_for_tokens(code)
        profile = await auth_service.fetch_google_profile(token_payload["access_token"])
        if not profile.email_verified:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google account email is not verified.")
        user = await auth_service.upsert_google_user(db, profile)
        bundle = await auth_service.create_session(db, user, request)
        response = RedirectResponse(f"{settings.FRONTEND_URL}/auth/callback", status_code=status.HTTP_302_FOUND)
        auth_service.set_auth_cookies(response, bundle)
        response.delete_cookie(settings.OAUTH_STATE_COOKIE_NAME, domain=settings.AUTH_COOKIE_DOMAIN, path="/")
        return response
    except HTTPException as exc:
        response = RedirectResponse(_frontend_error_redirect(exc.detail), status_code=status.HTTP_302_FOUND)
        auth_service.clear_auth_cookies(response)
        return response
    except httpx.HTTPError:
        response = RedirectResponse(_frontend_error_redirect("google_exchange_failed"), status_code=status.HTTP_302_FOUND)
        auth_service.clear_auth_cookies(response)
        return response


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return CurrentUserResponse.model_validate(current_user)


@router.post("/refresh", response_model=CurrentUserResponse)
async def refresh_session(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing.")
    bundle = await auth_service.rotate_refresh_session(db, refresh_token, request)
    auth_service.set_auth_cookies(response, bundle)
    return CurrentUserResponse.model_validate(bundle.user)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.revoke_refresh_session(db, refresh_token)
    auth_service.clear_auth_cookies(response)
    return LogoutResponse(message="Logged out.")
