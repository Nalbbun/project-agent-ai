from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlmodel import Session, select

from app.api.deps import get_current_user, get_db_session, require_roles
from app.models.user_account import UserAccount
from app.schemas.auth import LoginRequest, LoginResponse, UserRead
from app.services.auth import AuthService

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, session: Session = Depends(get_db_session)) -> LoginResponse:
    user, db_session = AuthService(session).authenticate(payload.username, payload.password)
    return LoginResponse(access_token=db_session.token, expires_at=db_session.expires_at, user=UserRead.model_validate(user, from_attributes=True))


@router.get("/auth/me", response_model=UserRead)
def me(user: UserAccount = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user, from_attributes=True)


@router.get("/auth/users", response_model=list[UserRead])
def list_users(session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator"))) -> list[UserRead]:
    rows = session.exec(select(UserAccount).order_by(UserAccount.username.asc())).all()
    return [UserRead.model_validate(row, from_attributes=True) for row in rows]


@router.post("/auth/logout")
def logout(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_db_session),
    user: UserAccount = Depends(get_current_user),
) -> dict:
    token = authorization.split(" ", 1)[1].strip() if authorization else ""
    AuthService(session).logout(token)
    return {"message": f"Logged out {user.username}"}
