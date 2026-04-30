from datetime import datetime, timedelta
from fastapi import HTTPException, BackgroundTasks
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.email.email_service import send_invite_email
from app.models import Group, User, UserGroup
from app.models.enums import GroupRole
from app.schemas import UserGroupAddMemberByEmail
from app.schemas.user import UserRead
from app.schemas.user_group import UserGroupRead
from starlette.responses import HTMLResponse


async def get_group_by_id(
        db: AsyncSession,
        id: int
) -> Group:
    statement = select(Group).where(Group.id == id)
    group = await db.scalar(statement)

    if not group:
        raise HTTPException(status_code=404, detail=f"Group with id {id} not found")

    return group


async def get_group_members(
        db: AsyncSession,
        id: int
) -> list[UserRead]:
    statement = (select(User)
                 .join(UserGroup, UserGroup.user_id == User.id)
                 .where(UserGroup.group_id == id, UserGroup.is_active))

    return list((await db.scalars(statement)).all())


async def invite_to_group_by_email(
    db: AsyncSession,
    payload: UserGroupAddMemberByEmail,
    current_user: User,
    background_tasks: BackgroundTasks,
) -> UserGroupRead:

    email = payload.email
    group_id = payload.group_id
    select_group = select(Group).where(Group.id == group_id)
    group = await db.scalar(select_group)

    if not group:
        raise HTTPException(status_code=404, detail=f"Group with id {group_id} not found")

    select_user_query = select(User).where(User.email == email)
    user_to_add = await db.scalar(select_user_query)

    if not user_to_add:
        raise HTTPException(status_code=404, detail=f"User with email {email} not found")

    select_for_existence = select(UserGroup).where(UserGroup.group_id == group_id).where(UserGroup.user_id == user_to_add.id)
    user_exists = await db.scalar(select_for_existence)

    if user_exists:
        if user_exists.is_active:
            raise HTTPException(status_code=409, detail=f"User with email {email} already member of group {group_id}")
        invite_token = create_invitation_token(user_exists.id)
        invite_link = build_invitation_link(invite_token)
        background_tasks.add_task(send_invite_email, email, group.name, invite_link)
        return UserGroupRead.model_validate(user_exists)

    select_user_group_query = (select(UserGroup)
                                .join(User, User.id == UserGroup.user_id)
                                .where(UserGroup.group_id == group_id)
                                .where(User.id == current_user.id))

    user_group = await db.scalar(select_user_group_query)

    if not user_group:
        raise HTTPException(status_code=404, detail=f"User group information for user {current_user} and for group {group_id} not found")

    user_group_to_save = UserGroup(
        group_id=group_id,
        user_id=user_to_add.id,
        group_role=GroupRole.MEMBER,
        is_active=False,
    )

    db.add(user_group_to_save)
    await db.flush()
    await db.refresh(user_group_to_save)

    invite_token = create_invitation_token(user_group_to_save.id)
    invite_link = build_invitation_link(invite_token)
    background_tasks.add_task(send_invite_email, email, group.name, invite_link)

    return UserGroupRead.model_validate(user_group_to_save)


async def join_by_invitation_link(
    db: AsyncSession,
    link: str,
) -> HTMLResponse:

    try:
        token = extract_link(link)
        user_group_id = decode_invitation_token(token)

        existing_member = await db.scalar(
            select(UserGroup).where(UserGroup.id == user_group_id)
        )
        if not existing_member:
            raise HTTPException(status_code=404, detail="Invitation not found")

        if existing_member.is_active:
            return return_success_html_response(UserGroupRead.model_validate(existing_member))

        existing_member.is_active = True
        await db.flush()
        await db.refresh(existing_member)
        return return_success_html_response(UserGroupRead.model_validate(existing_member))

    except HTTPException as e:
        return return_failed_html_response(e)


async def is_member_of_group(
        db: AsyncSession,
        group_id: int,
        user_id: int
) -> bool:
    find_by_user_id_and_group_id = (select(UserGroup)
                                    .where(UserGroup.group_id == group_id,
                                                       UserGroup.user_id == user_id))

    user_group = await db.scalar(find_by_user_id_and_group_id)

    if not user_group:
        return False

    return True

def extract_link(link: str) -> str:
    token = link.strip()
    if "/invite/" in token:
        token = token.rsplit("/invite/", 1)[-1]
    if not token:
        raise HTTPException(status_code=400, detail="Invitation link is required")
    return token


def create_invitation_token(user_group_id: int) -> str:
    expires_at = datetime.now() + timedelta(days=7)
    payload = {
        "type": "invite",
        "ugid": user_group_id,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_invitation_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation link") from exc

    if payload.get("type") != "invite":
        raise HTTPException(status_code=400, detail="Invalid invitation token type")

    ugid = payload.get("ugid")
    if not ugid:
        raise HTTPException(status_code=400, detail="Invalid invitation token payload")

    return int(ugid)


def build_invitation_link(token: str) -> str:
    backend_domain = (settings.BACKEND_DOMAIN or "localhost:8001").strip().rstrip("/")
    if not backend_domain.startswith(("http://", "https://")):
        backend_domain = f"http://{backend_domain}"
    return f"{backend_domain}/user-groups/invite/{token}"


def return_failed_html_response(exc: HTTPException) -> HTMLResponse:
    return HTMLResponse(
        content=f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="UTF-8" />
              <meta name="viewport" content="width=device-width, initial-scale=1.0" />
              <title>Invitation Error</title>
            </head>
            <body style="margin:0;background:#fff7ed;font-family:Arial,sans-serif;color:#7c2d12;">
              <div style="max-width:560px;margin:64px auto;padding:0 20px;">
                <div style="background:#fff;border:1px solid #fdba74;border-radius:12px;padding:32px;text-align:center;">
                  <h1 style="margin:0 0 12px;font-size:26px;color:#9a3412;">Invitation Failed</h1>
                  <p style="margin:0;font-size:16px;">{exc.detail}</p>
                </div>
              </div>
            </body>
            </html>
            """,
        status_code=exc.status_code,
    )


def return_success_html_response(user_group: UserGroupRead) -> HTMLResponse:
    return HTMLResponse(
        content=f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="UTF-8" />
              <meta name="viewport" content="width=device-width, initial-scale=1.0" />
              <title>Invitation Accepted</title>
            </head>
            <body style="margin:0;background:#f6f7fb;font-family:Arial,sans-serif;color:#1f2937;">
              <div style="max-width:560px;margin:64px auto;padding:0 20px;">
                <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:32px;text-align:center;">
                  <h1 style="margin:0 0 12px;font-size:26px;color:#111827;">You're in</h1>
                  <p style="margin:0 0 20px;font-size:16px;color:#4b5563;">
                    Invitation accepted successfully. You are now a member of the group.
                  </p>
                  <div style="font-size:13px;color:#6b7280;background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:12px;">
                    membership_id: {user_group.id} | group_id: {user_group.group_id}
                  </div>
                </div>
              </div>
            </body>
            </html>
            """,
        status_code=200,
    )
