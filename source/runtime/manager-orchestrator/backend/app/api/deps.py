from __future__ import annotations

from typing import Callable, Iterable
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Query, status
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.project_membership import ProjectMembership
from app.models.user_account import UserAccount
from app.services.auth import AuthService

ACCESS_LEVELS = {"viewer": 10, "reviewer": 20, "editor": 30, "owner": 40}
ROLE_TO_PROJECT_ACCESS = {
    "viewer": "viewer",
    "reviewer": "reviewer",
    "operator": "editor",
    "admin": "owner",
}


def get_db_session(session: Session = Depends(get_session)) -> Session:
    return session


def _extract_bearer_token(authorization: str | None, access_token: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    if access_token:
        return access_token.strip()
    return None


def get_current_user(
    authorization: str | None = Header(default=None),
    access_token: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
) -> UserAccount:
    token = _extract_bearer_token(authorization, access_token)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return AuthService(session).resolve_token(token)


def require_roles(*roles: str) -> Callable:
    def _dependency(user: UserAccount = Depends(get_current_user)) -> UserAccount:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user
    return _dependency


def _has_project_access(session: Session, user: UserAccount, project_id: UUID, minimum_access_role: str = "viewer") -> bool:
    if user.role == "admin":
        return True
    membership = session.exec(
        select(ProjectMembership)
        .where(ProjectMembership.project_id == project_id)
        .where(ProjectMembership.user_id == user.id)
    ).first()
    if not membership:
        return False
    return ACCESS_LEVELS.get(membership.access_role, 0) >= ACCESS_LEVELS.get(minimum_access_role, 0)


def ensure_project_access(session: Session, user: UserAccount, project_id: UUID, minimum_access_role: str = "viewer") -> None:
    if not _has_project_access(session, user, project_id, minimum_access_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project access denied")


def get_accessible_project_ids(session: Session, user: UserAccount, minimum_access_role: str = "viewer") -> list[UUID]:
    if user.role == "admin":
        return []
    memberships = session.exec(select(ProjectMembership).where(ProjectMembership.user_id == user.id)).all()
    min_level = ACCESS_LEVELS.get(minimum_access_role, 0)
    return [membership.project_id for membership in memberships if ACCESS_LEVELS.get(membership.access_role, 0) >= min_level]


def require_project_access(minimum_access_role: str = "viewer") -> Callable:
    def _dependency(
        project_id: str,
        session: Session = Depends(get_db_session),
        user: UserAccount = Depends(get_current_user),
    ) -> UserAccount:
        ensure_project_access(session, user, UUID(project_id), minimum_access_role)
        return user
    return _dependency
