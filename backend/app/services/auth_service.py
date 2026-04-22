from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import (
    TokenValidationError,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_token,
)
from app.models.models import AuthAccount, User, UserSession

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


@dataclass
class GoogleProfile:
    sub: str
    email: str
    name: Optional[str]
    picture: Optional[str]
    email_verified: bool


@dataclass
class AuthSessionBundle:
    access_token: str
    refresh_token: str
    session: UserSession
    user: User


class AuthService:
    """Google OAuth + application session management."""

    def ensure_google_oauth_configured(self) -> None:
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth is not configured.",
            )

    def build_google_login_url(self, state: str) -> str:
        self.ensure_google_oauth_configured()
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "include_granted_scopes": "true",
            "prompt": "select_account",
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> dict:
        self.ensure_google_oauth_configured()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
        response.raise_for_status()
        return response.json()

    async def fetch_google_profile(self, access_token: str) -> GoogleProfile:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        response.raise_for_status()
        payload = response.json()
        return GoogleProfile(
            sub=payload["sub"],
            email=payload["email"].lower(),
            name=payload.get("name"),
            picture=payload.get("picture"),
            email_verified=bool(payload.get("email_verified")),
        )

    async def upsert_google_user(self, db: AsyncSession, profile: GoogleProfile) -> User:
        now = datetime.now(timezone.utc)
        auth_account_result = await db.execute(
            select(AuthAccount)
            .options(selectinload(AuthAccount.user))
            .where(
                AuthAccount.provider == "google",
                AuthAccount.provider_sub == profile.sub,
            )
        )
        auth_account = auth_account_result.scalar_one_or_none()

        if auth_account:
            user = auth_account.user
        else:
            user_result = await db.execute(select(User).where(User.email == profile.email))
            user = user_result.scalar_one_or_none()
            if not user:
                user = User(
                    email=profile.email,
                    role="admin" if profile.email in settings.admin_emails else "user",
                )
                db.add(user)
                await db.flush()

            auth_account = AuthAccount(
                user_id=user.id,
                provider="google",
                provider_sub=profile.sub,
                provider_email=profile.email,
            )
            db.add(auth_account)

        if user.is_disabled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled.")

        user.email = profile.email
        user.name = profile.name
        user.avatar_url = profile.picture
        user.last_login_at = now
        auth_account.provider_email = profile.email
        auth_account.last_login_at = now
        await db.flush()
        return user

    async def create_session(self, db: AsyncSession, user: User, request: Request) -> AuthSessionBundle:
        now = datetime.now(timezone.utc)
        refresh_token = generate_refresh_token()
        session = UserSession(
            user_id=user.id,
            refresh_token_hash=hash_token(refresh_token),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            last_used_at=now,
        )
        db.add(session)
        await db.flush()
        access_token = create_access_token(
            payload={
                "sub": user.id,
                "sid": session.id,
                "role": user.role,
                "email": user.email,
            },
            secret_key=settings.JWT_SECRET_KEY,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return AuthSessionBundle(
            access_token=access_token,
            refresh_token=refresh_token,
            session=session,
            user=user,
        )

    async def rotate_refresh_session(
        self,
        db: AsyncSession,
        refresh_token: str,
        request: Request,
    ) -> AuthSessionBundle:
        session = await self.get_session_by_refresh_token(db, refresh_token)
        now = datetime.now(timezone.utc)
        if not session or session.revoked_at or session.expires_at <= now:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session is invalid.")
        if session.user.is_disabled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled.")

        session.revoked_at = now
        await db.flush()
        return await self.create_session(db, session.user, request)

    async def revoke_refresh_session(self, db: AsyncSession, refresh_token: Optional[str]) -> None:
        if not refresh_token:
            return
        session = await self.get_session_by_refresh_token(db, refresh_token)
        if not session or session.revoked_at:
            return
        session.revoked_at = datetime.now(timezone.utc)
        await db.flush()

    async def get_session_by_refresh_token(
        self,
        db: AsyncSession,
        refresh_token: str,
    ) -> Optional[UserSession]:
        result = await db.execute(
            select(UserSession)
            .options(selectinload(UserSession.user))
            .where(UserSession.refresh_token_hash == hash_token(refresh_token))
        )
        return result.scalar_one_or_none()

    async def get_user_from_access_token(self, db: AsyncSession, token: str) -> User:
        try:
            payload = decode_access_token(token, settings.JWT_SECRET_KEY)
        except TokenValidationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

        user_id = payload.get("sub")
        session_id = payload.get("sid")
        if not user_id or not session_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token.")

        result = await db.execute(
            select(UserSession)
            .options(selectinload(UserSession.user))
            .where(UserSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session or session.user_id != user_id or session.revoked_at:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is no longer active.")
        if session.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")
        if session.user.is_disabled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled.")

        session.last_used_at = datetime.now(timezone.utc)
        await db.flush()
        return session.user

    def set_auth_cookies(self, response: Response, bundle: AuthSessionBundle) -> None:
        cookie_kwargs = {
            "httponly": True,
            "secure": settings.AUTH_COOKIE_SECURE,
            "samesite": settings.AUTH_COOKIE_SAMESITE,
            "domain": settings.AUTH_COOKIE_DOMAIN,
            "path": "/",
        }
        response.set_cookie(
            key=settings.ACCESS_COOKIE_NAME,
            value=bundle.access_token,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            **cookie_kwargs,
        )
        response.set_cookie(
            key=settings.REFRESH_COOKIE_NAME,
            value=bundle.refresh_token,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            **cookie_kwargs,
        )

    def clear_auth_cookies(self, response: Response) -> None:
        cookie_kwargs = {
            "domain": settings.AUTH_COOKIE_DOMAIN,
            "path": "/",
        }
        response.delete_cookie(settings.ACCESS_COOKIE_NAME, **cookie_kwargs)
        response.delete_cookie(settings.REFRESH_COOKIE_NAME, **cookie_kwargs)
        response.delete_cookie(settings.OAUTH_STATE_COOKIE_NAME, **cookie_kwargs)


auth_service = AuthService()
