from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.models import User

router = APIRouter()


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str | None
    avatar_url: str | None
    role: str
    is_disabled: bool
    created_at: str | None
    last_login_at: str | None


class UpdateRoleRequest(BaseModel):
    role: str


def serialize_user(user: User) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        role=user.role,
        is_disabled=user.is_disabled,
        created_at=user.created_at.isoformat() if isinstance(user.created_at, datetime) else None,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [serialize_user(user) for user in result.scalars().all()]


@router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
async def update_user_role(
    user_id: str,
    payload: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    if payload.role not in {"admin", "user"}:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.id == current_admin.id and payload.role != "admin":
        raise HTTPException(status_code=400, detail="You cannot remove your own admin role.")

    user.role = payload.role
    await db.flush()
    return serialize_user(user)
