from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_db_session, require_roles
from app.models.agent import AgentCatalog
from app.models.user_account import UserAccount
from app.schemas.agent import AgentRead

router = APIRouter(tags=["agents"])


@router.get("/agents", response_model=list[AgentRead])
def list_agents(session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))) -> list[AgentCatalog]:
    return session.exec(select(AgentCatalog).order_by(AgentCatalog.code.asc())).all()
