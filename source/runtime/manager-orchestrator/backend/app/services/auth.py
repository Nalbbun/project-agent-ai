from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from hmac import compare_digest

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.config import get_settings
from app.models.auth_session import AuthSession
from app.models.user_account import UserAccount

settings = get_settings()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, expected = stored.split("$", 2)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()
    return compare_digest(digest, expected)


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def authenticate(self, username: str, password: str) -> tuple[UserAccount, AuthSession]:
        user = self.session.exec(select(UserAccount).where(UserAccount.username == username)).first()
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        expires_at = datetime.utcnow() + timedelta(hours=settings.auth_session_hours)
        token = secrets.token_urlsafe(32)
        db_session = AuthSession(user_id=user.id, token=token, expires_at=expires_at, last_seen_at=datetime.utcnow())
        self.session.add(db_session)
        self.session.commit()
        self.session.refresh(db_session)
        return user, db_session

    def logout(self, token: str) -> None:
        db_session = self.session.exec(select(AuthSession).where(AuthSession.token == token)).first()
        if db_session and not db_session.revoked_at:
            db_session.revoked_at = datetime.utcnow()
            self.session.add(db_session)
            self.session.commit()

    def resolve_token(self, token: str) -> UserAccount:
        db_session = self.session.exec(select(AuthSession).where(AuthSession.token == token)).first()
        if not db_session or db_session.revoked_at or db_session.expires_at < datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
        user = self.session.get(UserAccount, db_session.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
        db_session.last_seen_at = datetime.utcnow()
        self.session.add(db_session)
        self.session.commit()
        return user
