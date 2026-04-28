from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlmodel import Session, select

from app.api.routes import agents, approvals, artifacts, auth, dashboard, foundation, projects, runs, workers
from app.core.config import get_settings
from app.db.session import engine, wait_for_db
from app.models.run import OrchestrationRun
from app.services.seed import seed_agents_from_yaml
from app.services.vector_store import VectorStoreService
from app.services.worker_service import WorkerService

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_db()
    settings.artifact_path.mkdir(parents=True, exist_ok=True)
    seed_agents_from_yaml()
    if settings.vector_store_enabled:
        VectorStoreService().ensure_collections()
    yield


app = FastAPI(title=settings.app_name, version="0.5.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health/live")
def health_live() -> dict:
    return {"status": "ok", "simulation_mode": settings.simulation_mode}


@app.get("/health/ready")
def health_ready() -> dict:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    vector_status = VectorStoreService().health()
    worker_summary = {"worker_count": 0, "active_worker_count": 0, "stale_worker_count": 0}
    run_summary = {"stale_running_runs": 0}
    with Session(engine) as session:
        worker_summary = WorkerService(session).summarize()
        stale_cutoff = datetime.utcnow() - timedelta(seconds=settings.run_stale_after_seconds)
        stale_runs = session.exec(select(OrchestrationRun).where(OrchestrationRun.queue_status == "running").where(OrchestrationRun.updated_at < stale_cutoff)).all()
        run_summary = {"stale_running_runs": len(stale_runs)}
    return {
        "status": "ready",
        "simulation_mode": settings.simulation_mode,
        "job_mode": settings.job_mode,
        "router_base_url": settings.router_base_url,
        "artifact_dir": str(settings.artifact_path),
        "vector_store": vector_status,
        "workers": worker_summary,
        "runs": run_summary,
        "auth_enabled": settings.auth_enabled,
        "approval_enabled": settings.approval_enabled,
    }


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "simulation_mode": settings.simulation_mode,
        "vector_store": VectorStoreService().health(),
        "auth_enabled": settings.auth_enabled,
        "approval_enabled": settings.approval_enabled,
    }


app.include_router(auth.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(foundation.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(runs.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(workers.router, prefix="/api")
app.include_router(artifacts.router, prefix="/api")
