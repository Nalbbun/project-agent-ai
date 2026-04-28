from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import ensure_project_access, get_accessible_project_ids, get_current_user, get_db_session, require_roles
from app.models.approval import RunApproval
from app.models.artifact import Artifact
from app.models.project import Project
from app.models.project_access_request import ProjectAccessRequest
from app.models.project_knowledge import ProjectKnowledge
from app.models.project_membership import ProjectMembership
from app.models.project_membership_invite import ProjectMembershipInvite
from app.models.run import OrchestrationRun
from app.models.user_account import UserAccount
from app.schemas.project import (
    ProjectAccessRequestCreate,
    ProjectAccessRequestDecision,
    ProjectAccessRequestRead,
    ProjectCreate,
    ProjectKnowledgeCreate,
    ProjectKnowledgeRead,
    ProjectMembershipCreate,
    ProjectMembershipInviteCreate,
    ProjectMembershipInviteRead,
    ProjectMembershipRead,
    ProjectRead,
    ProjectSummaryRead,
)
from app.services.vector_store import VectorStoreService

router = APIRouter(tags=["projects"])


def _project_access_role(session: Session, user: UserAccount, project_uuid: UUID) -> str | None:
    if user.role == "admin":
        return "owner"
    membership = session.exec(
        select(ProjectMembership)
        .where(ProjectMembership.project_id == project_uuid)
        .where(ProjectMembership.user_id == user.id)
    ).first()
    return membership.access_role if membership else None


def _summary(session: Session, user: UserAccount, project_uuid: UUID) -> ProjectSummaryRead:
    return ProjectSummaryRead(
        project_id=project_uuid,
        knowledge_count=len(session.exec(select(ProjectKnowledge).where(ProjectKnowledge.project_id == project_uuid)).all()),
        membership_count=len(session.exec(select(ProjectMembership).where(ProjectMembership.project_id == project_uuid)).all()),
        run_count=len(session.exec(select(OrchestrationRun).where(OrchestrationRun.project_id == project_uuid)).all()),
        waiting_approval_count=len(session.exec(select(RunApproval).join(OrchestrationRun, RunApproval.run_id == OrchestrationRun.id).where(OrchestrationRun.project_id == project_uuid).where(RunApproval.status == "pending")).all()),
        my_access_role=_project_access_role(session, user, project_uuid),
        pending_invite_count=len(session.exec(select(ProjectMembershipInvite).where(ProjectMembershipInvite.project_id == project_uuid).where(ProjectMembershipInvite.status == "pending")).all()),
        pending_request_count=len(session.exec(select(ProjectAccessRequest).where(ProjectAccessRequest.project_id == project_uuid).where(ProjectAccessRequest.status == "pending")).all()),
    )


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator", "reviewer", "viewer"))) -> list[Project]:
    if user.role == "admin":
        return session.exec(select(Project).order_by(Project.created_at.desc())).all()
    allowed = set(get_accessible_project_ids(session, user, "viewer"))
    return [project for project in session.exec(select(Project).order_by(Project.created_at.desc())).all() if project.id in allowed]


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, session: Session = Depends(get_db_session), user: UserAccount = Depends(require_roles("admin", "operator"))) -> Project:
    project = Project(name=payload.name, description=payload.description, updated_at=datetime.utcnow())
    session.add(project)
    session.commit()
    session.refresh(project)
    session.add(ProjectMembership(project_id=project.id, user_id=user.id, access_role="owner", granted_by_user_id=user.id))
    session.commit()
    return project


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> Project:
    project_uuid = UUID(project_id)
    project = session.get(Project, project_uuid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    ensure_project_access(session, user, project_uuid, "viewer")
    return project


@router.get("/projects/{project_id}/summary", response_model=ProjectSummaryRead)
def get_project_summary(project_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> ProjectSummaryRead:
    project_uuid = UUID(project_id)
    project = session.get(Project, project_uuid)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    ensure_project_access(session, user, project_uuid, "viewer")
    return _summary(session, user, project_uuid)


@router.get("/projects/{project_id}/memberships", response_model=list[ProjectMembershipRead])
def list_project_memberships(project_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> list[ProjectMembership]:
    project_uuid = UUID(project_id)
    if not session.get(Project, project_uuid):
        raise HTTPException(status_code=404, detail="Project not found")
    ensure_project_access(session, user, project_uuid, "viewer")
    return session.exec(select(ProjectMembership).where(ProjectMembership.project_id == project_uuid).order_by(ProjectMembership.created_at.asc())).all()


@router.post("/projects/{project_id}/memberships", response_model=ProjectMembershipRead, status_code=status.HTTP_201_CREATED)
def create_project_membership(project_id: str, payload: ProjectMembershipCreate, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> ProjectMembership:
    project_uuid = UUID(project_id)
    if not session.get(Project, project_uuid):
        raise HTTPException(status_code=404, detail="Project not found")
    ensure_project_access(session, user, project_uuid, "owner")
    existing = session.exec(select(ProjectMembership).where(ProjectMembership.project_id == project_uuid).where(ProjectMembership.user_id == payload.user_id)).first()
    if existing:
        existing.access_role = payload.access_role
        existing.granted_by_user_id = user.id
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    item = ProjectMembership(project_id=project_uuid, user_id=payload.user_id, access_role=payload.access_role, granted_by_user_id=user.id)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/projects/{project_id}/memberships/{membership_id}")
def delete_project_membership(project_id: str, membership_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> dict:
    project_uuid = UUID(project_id)
    ensure_project_access(session, user, project_uuid, "owner")
    item = session.get(ProjectMembership, UUID(membership_id))
    if not item or item.project_id != project_uuid:
        raise HTTPException(status_code=404, detail="Membership not found")
    session.delete(item)
    session.commit()
    return {"message": "Membership removed"}


@router.get("/projects/my-invites", response_model=list[ProjectMembershipInviteRead])
def my_invites(session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> list[ProjectMembershipInvite]:
    return session.exec(select(ProjectMembershipInvite).where(ProjectMembershipInvite.invited_user_id == user.id).order_by(ProjectMembershipInvite.created_at.desc())).all()


@router.get("/projects/{project_id}/invites", response_model=list[ProjectMembershipInviteRead])
def list_project_invites(project_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> list[ProjectMembershipInvite]:
    project_uuid = UUID(project_id)
    ensure_project_access(session, user, project_uuid, "owner")
    return session.exec(select(ProjectMembershipInvite).where(ProjectMembershipInvite.project_id == project_uuid).order_by(ProjectMembershipInvite.created_at.desc())).all()


@router.post("/projects/{project_id}/invites", response_model=ProjectMembershipInviteRead, status_code=status.HTTP_201_CREATED)
def create_project_invite(project_id: str, payload: ProjectMembershipInviteCreate, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> ProjectMembershipInvite:
    project_uuid = UUID(project_id)
    if not session.get(Project, project_uuid):
        raise HTTPException(status_code=404, detail="Project not found")
    ensure_project_access(session, user, project_uuid, "owner")
    existing_membership = session.exec(select(ProjectMembership).where(ProjectMembership.project_id == project_uuid).where(ProjectMembership.user_id == payload.invited_user_id)).first()
    if existing_membership:
        raise HTTPException(status_code=409, detail="User is already a project member")
    invite = session.exec(select(ProjectMembershipInvite).where(ProjectMembershipInvite.project_id == project_uuid).where(ProjectMembershipInvite.invited_user_id == payload.invited_user_id).where(ProjectMembershipInvite.status == "pending")).first()
    if invite:
        invite.access_role = payload.access_role
        invite.note = payload.note
        invite.invited_by_user_id = user.id
        session.add(invite)
        session.commit()
        session.refresh(invite)
        return invite
    invite = ProjectMembershipInvite(project_id=project_uuid, invited_user_id=payload.invited_user_id, access_role=payload.access_role, invited_by_user_id=user.id, note=payload.note)
    session.add(invite)
    session.commit()
    session.refresh(invite)
    return invite


@router.post("/projects/invites/{invite_id}/accept", response_model=ProjectMembershipInviteRead)
def accept_invite(invite_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> ProjectMembershipInvite:
    invite = session.get(ProjectMembershipInvite, UUID(invite_id))
    if not invite or invite.invited_user_id != user.id:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.status != "pending":
        raise HTTPException(status_code=409, detail="Invite already handled")
    membership = session.exec(select(ProjectMembership).where(ProjectMembership.project_id == invite.project_id).where(ProjectMembership.user_id == user.id)).first()
    if membership:
        membership.access_role = invite.access_role
        membership.granted_by_user_id = invite.invited_by_user_id
        session.add(membership)
    else:
        session.add(ProjectMembership(project_id=invite.project_id, user_id=user.id, access_role=invite.access_role, granted_by_user_id=invite.invited_by_user_id))
    invite.status = "accepted"
    invite.responded_at = datetime.utcnow()
    session.add(invite)
    session.commit()
    session.refresh(invite)
    return invite


@router.post("/projects/invites/{invite_id}/decline", response_model=ProjectMembershipInviteRead)
def decline_invite(invite_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> ProjectMembershipInvite:
    invite = session.get(ProjectMembershipInvite, UUID(invite_id))
    if not invite or invite.invited_user_id != user.id:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.status != "pending":
        raise HTTPException(status_code=409, detail="Invite already handled")
    invite.status = "declined"
    invite.responded_at = datetime.utcnow()
    session.add(invite)
    session.commit()
    session.refresh(invite)
    return invite


@router.get("/projects/access-requests/mine", response_model=list[ProjectAccessRequestRead])
def my_access_requests(session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> list[ProjectAccessRequest]:
    return session.exec(select(ProjectAccessRequest).where(ProjectAccessRequest.requested_by_user_id == user.id).order_by(ProjectAccessRequest.created_at.desc())).all()


@router.get("/projects/{project_id}/access-requests", response_model=list[ProjectAccessRequestRead])
def list_access_requests(project_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> list[ProjectAccessRequest]:
    project_uuid = UUID(project_id)
    ensure_project_access(session, user, project_uuid, "owner")
    return session.exec(select(ProjectAccessRequest).where(ProjectAccessRequest.project_id == project_uuid).order_by(ProjectAccessRequest.created_at.desc())).all()


@router.post("/projects/{project_id}/access-requests", response_model=ProjectAccessRequestRead, status_code=status.HTTP_201_CREATED)
def create_access_request(project_id: str, payload: ProjectAccessRequestCreate, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> ProjectAccessRequest:
    project_uuid = UUID(project_id)
    if not session.get(Project, project_uuid):
        raise HTTPException(status_code=404, detail="Project not found")
    existing_membership = session.exec(select(ProjectMembership).where(ProjectMembership.project_id == project_uuid).where(ProjectMembership.user_id == user.id)).first()
    if existing_membership:
        raise HTTPException(status_code=409, detail="Already a project member")
    request = session.exec(select(ProjectAccessRequest).where(ProjectAccessRequest.project_id == project_uuid).where(ProjectAccessRequest.requested_by_user_id == user.id).where(ProjectAccessRequest.status == "pending")).first()
    if request:
        request.requested_role = payload.requested_role
        request.note = payload.note
        session.add(request)
        session.commit()
        session.refresh(request)
        return request
    request = ProjectAccessRequest(project_id=project_uuid, requested_by_user_id=user.id, requested_role=payload.requested_role, note=payload.note)
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


@router.post("/projects/access-requests/{request_id}/approve", response_model=ProjectAccessRequestRead)
def approve_access_request(request_id: str, payload: ProjectAccessRequestDecision, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> ProjectAccessRequest:
    request = session.get(ProjectAccessRequest, UUID(request_id))
    if not request:
        raise HTTPException(status_code=404, detail="Access request not found")
    ensure_project_access(session, user, request.project_id, "owner")
    request.status = "approved"
    request.reviewed_by_user_id = user.id
    request.reviewed_at = datetime.utcnow()
    request.note = payload.note
    session.add(request)
    membership = session.exec(select(ProjectMembership).where(ProjectMembership.project_id == request.project_id).where(ProjectMembership.user_id == request.requested_by_user_id)).first()
    if membership:
        membership.access_role = payload.access_role
        membership.granted_by_user_id = user.id
        session.add(membership)
    else:
        session.add(ProjectMembership(project_id=request.project_id, user_id=request.requested_by_user_id, access_role=payload.access_role, granted_by_user_id=user.id))
    session.commit()
    session.refresh(request)
    return request


@router.post("/projects/access-requests/{request_id}/reject", response_model=ProjectAccessRequestRead)
def reject_access_request(request_id: str, payload: ProjectAccessRequestDecision, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> ProjectAccessRequest:
    request = session.get(ProjectAccessRequest, UUID(request_id))
    if not request:
        raise HTTPException(status_code=404, detail="Access request not found")
    ensure_project_access(session, user, request.project_id, "owner")
    request.status = "rejected"
    request.reviewed_by_user_id = user.id
    request.reviewed_at = datetime.utcnow()
    request.note = payload.note
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


@router.get("/projects/{project_id}/knowledge", response_model=list[ProjectKnowledgeRead])
def list_project_knowledge(project_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> list[ProjectKnowledge]:
    project_uuid = UUID(project_id)
    if not session.get(Project, project_uuid):
        raise HTTPException(status_code=404, detail="Project not found")
    ensure_project_access(session, user, project_uuid, "viewer")
    return session.exec(select(ProjectKnowledge).where(ProjectKnowledge.project_id == project_uuid).order_by(ProjectKnowledge.created_at.desc())).all()


@router.post("/projects/{project_id}/knowledge", response_model=ProjectKnowledgeRead, status_code=status.HTTP_201_CREATED)
def create_project_knowledge(project_id: str, payload: ProjectKnowledgeCreate, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> ProjectKnowledge:
    project_uuid = UUID(project_id)
    if not session.get(Project, project_uuid):
        raise HTTPException(status_code=404, detail="Project not found")
    ensure_project_access(session, user, project_uuid, "editor")
    item = ProjectKnowledge(project_id=project_uuid, title=payload.title, content=payload.content, source_type=payload.source_type, tags=payload.tags, summary=payload.summary)
    session.add(item)
    session.commit()
    session.refresh(item)
    VectorStoreService().upsert_project_knowledge(item)
    return item


@router.post("/projects/{project_id}/knowledge/reindex")
def reindex_project_knowledge(project_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> dict:
    project_uuid = UUID(project_id)
    if not session.get(Project, project_uuid):
        raise HTTPException(status_code=404, detail="Project not found")
    ensure_project_access(session, user, project_uuid, "editor")
    vector = VectorStoreService()
    docs = session.exec(select(ProjectKnowledge).where(ProjectKnowledge.project_id == project_uuid)).all()
    for doc in docs:
        vector.upsert_project_knowledge(doc)
    artifacts = session.exec(select(Artifact).join(OrchestrationRun, Artifact.run_id == OrchestrationRun.id).where(OrchestrationRun.project_id == project_uuid)).all()
    for artifact in artifacts:
        vector.upsert_artifact(artifact, project_id=project_uuid)
    return {"message": "Project knowledge reindexed", "knowledge_count": len(docs), "artifact_count": len(artifacts)}


@router.get("/projects/{project_id}/knowledge/{knowledge_id}", response_model=ProjectKnowledgeRead)
def get_project_knowledge(project_id: str, knowledge_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> ProjectKnowledge:
    project_uuid = UUID(project_id)
    ensure_project_access(session, user, project_uuid, "viewer")
    item = session.get(ProjectKnowledge, UUID(knowledge_id))
    if not item or item.project_id != project_uuid:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    return item


@router.delete("/projects/{project_id}/knowledge/{knowledge_id}")
def delete_project_knowledge(project_id: str, knowledge_id: str, session: Session = Depends(get_db_session), user: UserAccount = Depends(get_current_user)) -> dict:
    project_uuid = UUID(project_id)
    ensure_project_access(session, user, project_uuid, "editor")
    item = session.get(ProjectKnowledge, UUID(knowledge_id))
    if not item or item.project_id != project_uuid:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    VectorStoreService().delete_project_knowledge(item.id)
    session.delete(item)
    session.commit()
    return {"message": "Knowledge deleted"}
