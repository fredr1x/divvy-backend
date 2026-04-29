from datetime import datetime

from app.models import RefreshToken, AuditLog
from app.models.enums import ActionType, ActionStatus
from app.schemas import UserRead, UserUpdate
from app.services.audit.audit_logs_service import create_log
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.scalar(select(User).where(User.id == user_id))


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email))


async def get_user_by_google_sub(db: AsyncSession, google_sub: str) -> User | None:
    return await db.scalar(select(User).where(User.google_sub == google_sub))


async def create_user_local(
    db: AsyncSession,
    email: str,
    password: str,
    first_name: str | None,
    last_name: str | None,
) -> User:
    user = User(
        email=email,
        first_name=first_name or "",
        last_name=last_name or "",
        password=hash_password(password),
        auth_provider="local",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def create_google_user(
    db: AsyncSession,
    email: str,
    google_sub: str,
    first_name: str | None,
    last_name: str | None,
) -> User:
    user = User(
        email=email,
        first_name=first_name or "",
        last_name=last_name or "",
        password=None,
        auth_provider="google",
        google_sub=google_sub,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def set_verified_to_user(
    db: AsyncSession,
    user: User,
):
    user.is_verified=True
    await db.flush()
    await db.refresh(user)


async def update_user(
    ip_address: str,
    payload: UserUpdate,
    current_user: User,
    db: AsyncSession,
) -> UserRead:

    old_values = [UserRead.model_validate(current_user).model_dump(mode="json")]

    updated_fields = payload.dict(exclude_unset=True)
    for field, value in updated_fields.items():
        setattr(current_user, field, value)

    new_values = [UserRead.model_validate(current_user).model_dump(mode="json")]

    await create_log(
        db,
        AuditLog(
            user_id=current_user.id,
            ip_address=ip_address,
            action_type=ActionType.UPDATE,
            entity_id=current_user.id,
            entity_name="USER",
            old_values=old_values,
            new_values=new_values,
            action_status=ActionStatus.SUCCESS,
        ),
        message="User account has been updated successfully"
    )

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    return UserRead.model_validate(current_user)


async def delete_user_account(
        ip_address: str,
        db: AsyncSession,
        current_user: User,
):
    if not current_user.is_active:
        return

    current_user.is_active = False
    db.add(current_user)

    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.utcnow())
    )

    await create_log(
        db,
        AuditLog(
            user_id=current_user.id,
            ip_address=ip_address,
            action_type=ActionType.DELETE,
            entity_id=current_user.id,
            entity_name="USER",
            action_status=ActionStatus.SUCCESS,
        ),
        "User account has been deactivated successfully"
    )

    await db.commit()
    await db.refresh(current_user)
