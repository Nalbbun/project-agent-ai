from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml
from sqlmodel import Session, select

from app.core.config import get_settings
from app.db.session import engine
from app.models.agent import AgentCatalog
from app.models.user_account import UserAccount
from app.services.auth import hash_password

settings = get_settings()


def seed_agents_from_yaml() -> None:
    config_path = Path(settings.agent_config_path)
    if config_path.exists():
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        agents = config.get("agents", [])
        with Session(engine) as session:
            for item in agents:
                existing = session.exec(select(AgentCatalog).where(AgentCatalog.code == item["code"])).first()
                normalized = {
                    "name": item["name"],
                    "role": item["role"],
                    "endpoint": settings.router_base_url if settings.use_router else item["endpoint"],
                    "model": settings.router_model_name if settings.use_router else item["model"],
                    "adapter": item.get("adapter"),
                    "prompt_key": item["prompt_key"],
                    "transport": item.get("transport", "router" if settings.use_router else "direct"),
                    "router_role": item.get("router_role", item["role"]),
                    "request_timeout_seconds": item.get("request_timeout_seconds", settings.default_timeout_seconds),
                    "max_retries": item.get("max_retries", settings.max_step_retry_count),
                    "active": item.get("active", True),
                }
                if existing:
                    for key, value in normalized.items():
                        setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                else:
                    session.add(AgentCatalog(code=item["code"], **normalized))
            session.commit()
    seed_default_users()


def seed_default_users() -> None:
    if not settings.auth_seed_users_enabled:
        return
    defaults = [
        ("admin", "Administrator", "admin", settings.auth_admin_password),
        ("operator", "Operator", "operator", settings.auth_operator_password),
        ("reviewer", "Reviewer", "reviewer", settings.auth_reviewer_password),
        ("viewer", "Viewer", "viewer", settings.auth_viewer_password),
    ]
    with Session(engine) as session:
        for username, display_name, role, password in defaults:
            existing = session.exec(select(UserAccount).where(UserAccount.username == username)).first()
            if existing:
                continue
            session.add(UserAccount(username=username, display_name=display_name, role=role, password_hash=hash_password(password), is_active=True))
        session.commit()
