from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import ensure_project_access, get_current_user, get_db_session
from app.models.artifact import Artifact
from app.models.run import OrchestrationRun
from app.models.user_account import UserAccount
from app.schemas.run import ArtifactRead
from app.services.vector_store import VectorStoreService

router = APIRouter(tags=["artifacts"])


@router.get("/runs/{run_id}/artifacts", response_model=list[ArtifactRead])
def list_artifacts(run_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> list[Artifact]:
    run_uuid = UUID(run_id)
    run = session.get(OrchestrationRun, run_uuid)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.project_id:
        ensure_project_access(session, user, run.project_id, "viewer")
    return session.exec(
        select(Artifact)
        .where(Artifact.run_id == run_uuid)
        .order_by(Artifact.created_at.asc())
    ).all()


@router.post("/runs/{run_id}/artifacts/reindex")
def reindex_run_artifacts(run_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> dict:
    run_uuid = UUID(run_id)
    run = session.get(OrchestrationRun, run_uuid)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.project_id:
        ensure_project_access(session, user, run.project_id, "editor")
    artifacts = session.exec(select(Artifact).where(Artifact.run_id == run_uuid)).all()
    vector = VectorStoreService()
    for artifact in artifacts:
        vector.upsert_artifact(artifact, project_id=run.project_id)
    return {"message": "Artifacts reindexed", "artifact_count": len(artifacts)}


@router.get("/artifacts/{artifact_id}", response_model=ArtifactRead)
def get_artifact(artifact_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> Artifact:
    artifact = session.get(Artifact, UUID(artifact_id))
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    run = session.get(OrchestrationRun, artifact.run_id)
    if run and run.project_id:
        ensure_project_access(session, user, run.project_id, "viewer")
    return artifact
