from __future__ import annotations

from typing import Any


def simulate(role: str, user_request: str, context: dict[str, Any]) -> dict[str, Any]:
    if role == "manager":
        return {
            "execution_plan": [
                {"step": 1, "agent": "pm", "task": "요구사항 구조화"},
                {"step": 2, "agent": "architect", "task": "시스템 설계"},
                {"step": 3, "agent": "dev-fe", "task": "프론트엔드 구현 설계"},
                {"step": 4, "agent": "dev-be", "task": "백엔드 구현 설계"},
                {"step": 5, "agent": "dev-db", "task": "DB 설계/마이그레이션"},
                {"step": 6, "agent": "qa", "task": "품질 검증"},
                {"step": 7, "agent": "secops", "task": "보안 검토"},
            ],
            "missing_info_questions": [
                "우선 지원할 플랫폼은 웹만 포함하는가?",
                "인증 체계는 자체 로그인인가 SSO 연동인가?",
            ],
            "merge_strategy": [
                "PM 산출물을 Architect 입력으로 전달",
                "Architect 결과를 Dev-FE/BE/DB에 병렬 전달",
                "QA/SecOps 결과를 최종 Manager 병합 단계에서 요약",
            ],
            "final_summary": "Manager planning completed",
        }
    if role == "pm":
        return {
            "summary": f"{user_request} 요구 분석",
            "functional_requirements": [
                "사용자 요청 등록",
                "진행 상태 조회",
                "역할별 산출물 생성",
                "최종 결과 통합",
            ],
            "non_functional_requirements": [
                "역할별 패키지 분리",
                "단계별 이력 저장",
                "재실행 가능 구조",
                "JSON 중심 구조화 출력",
            ],
            "questions": [
                "실행 결과를 파일로도 패키징할지?",
                "RAG는 초기 버전에서 필수인지?",
            ],
            "acceptance_criteria": [
                "Manager가 단계별 agent를 순서대로 호출할 수 있어야 한다",
                "각 단계 결과가 DB에 저장되어야 한다",
            ],
        }
    if role == "architect":
        return {
            "architecture_style": "modular monolith with agent router",
            "components": [
                {"name": "frontend-console", "responsibility": "run 생성/조회 및 단계 모니터링"},
                {"name": "orchestrator-api", "responsibility": "run 생성/상태 전이/agent 호출"},
                {"name": "agent-router", "responsibility": "role → endpoint/model/adapter 라우팅"},
                {"name": "postgres", "responsibility": "run/step/event/artifact 저장"},
            ],
            "apis": [
                {"method": "POST", "path": "/api/runs", "purpose": "새 실행 생성"},
                {"method": "POST", "path": "/api/runs/{run_id}/execute", "purpose": "전체 단계 실행"},
                {"method": "GET", "path": "/api/runs/{run_id}", "purpose": "실행 상세 조회"},
            ],
            "database": {
                "entities": ["project", "agent_catalog", "orchestration_run", "orchestration_step", "orchestration_event", "artifact"]
            },
            "sequence": [
                "manager plan",
                "pm requirements",
                "architect design",
                "dev parallel planning",
                "qa review",
                "secops review",
                "manager merge",
            ],
            "adrs": [
                "학습 패키지와 운영 패키지를 분리한다",
                "런타임은 OpenAI-compatible endpoint를 기본 프로토콜로 사용한다",
            ],
        }
    if role == "dev-fe":
        return {
            "deliverables": [
                "DashboardPage",
                "RunsPage",
                "RunDetailPage",
                "AgentCatalogPage",
            ],
            "files": [
                {"path": "src/pages/DashboardPage.tsx", "summary": "요약 카드와 최근 실행 목록"},
                {"path": "src/pages/RunDetailPage.tsx", "summary": "단계 타임라인과 step 결과 표시"},
            ],
            "risks": ["긴 JSON 출력 렌더링 성능", "실시간 갱신 미구현"],
            "next_inputs": ["BE API contract 확정", "UI 권한 정책"],
        }
    if role == "dev-be":
        return {
            "deliverables": ["FastAPI app", "OrchestratorService", "AgentRouter", "Run API"],
            "files": [
                {"path": "app/services/orchestrator.py", "summary": "단계 생성 및 실행 로직"},
                {"path": "app/api/routes/runs.py", "summary": "run CRUD 및 execute/retry API"},
            ],
            "risks": ["실제 모델 응답 포맷 변동", "retry 정책 단순화"],
            "next_inputs": ["Tool Runner API", "Artifact Storage 정책"],
        }
    if role == "dev-db":
        return {
            "ddl": [
                "project",
                "agent_catalog",
                "orchestration_run",
                "orchestration_step",
                "orchestration_event",
                "artifact",
            ],
            "indexes": [
                "idx_orchestration_step_run_seq",
                "idx_orchestration_event_run",
                "idx_artifact_run",
            ],
            "migration": {"tool": "init sql", "file": "db/init/001_schema.sql"},
        }
    if role == "qa":
        return {
            "verdict": "pass",
            "test_cases": [
                {"title": "run 생성", "result": "pass"},
                {"title": "execute 후 step 상태 전이", "result": "pass"},
                {"title": "retry API", "result": "pass"},
            ],
            "gaps": ["실제 모델 연동 E2E 테스트 필요"],
            "actions": ["pytest 기반 단위 테스트 추가", "simulation_mode 회귀 테스트 추가"],
        }
    if role == "secops":
        return {
            "verdict": "pass",
            "findings": [
                {"severity": "medium", "issue": "초기 버전은 인증이 없음", "recommendation": "JWT 또는 SSO 추가"},
                {"severity": "low", "issue": "CORS 허용 범위가 로컬 기준", "recommendation": "운영에서 allowlist 제한"},
            ],
            "hardening_actions": [
                "backend 인증/인가 추가",
                "secret manager 연동",
                "tool runner sandbox 분리",
            ],
        }
    return {"message": f"No simulator for role={role}"}
