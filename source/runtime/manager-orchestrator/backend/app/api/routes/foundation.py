from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_db_session, require_roles
from app.models.user_account import UserAccount
from app.schemas.foundation import FoundationGuardSnapshot
from app.services.foundation_guard import FoundationGuardService

router = APIRouter(tags=["foundation"])


@router.get("/foundation/guard", response_model=FoundationGuardSnapshot)
def get_foundation_guard(
    session: Session = Depends(get_db_session),
    _: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer")),
) -> FoundationGuardSnapshot:
    return FoundationGuardService(session).snapshot()

