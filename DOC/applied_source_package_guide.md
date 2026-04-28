# 적용 전체 소스 패키지 가이드 (6대 필수 항목 매핑)

요청하신 6개 필수 항목 기준으로 현재 `source/runtime/manager-orchestrator`와 `source/runtime/work_proxy_deploy`가 어디에 반영되어 있는지 매핑하고,
바로 전달 가능한 전체 소스 패키지 생성 방법을 정리합니다.

## 1) Router 강제 경유 + 역할 라우팅
- 매핑 파일
  - `source/runtime/manager-orchestrator/config/agents.yaml`
  - `source/runtime/manager-orchestrator/backend/app/services/llm_client.py`
- 핵심 반영
  - agent transport/endpoint가 router 기준
  - 요청 시 `x-agent-role`, `extra_body.agent_role`, `metadata.agent_role` 전달

## 2) Queue/Worker + Retry/Backoff + Dead-letter
- 매핑 파일
  - `source/runtime/manager-orchestrator/backend/app/services/job_queue.py`
  - `source/runtime/manager-orchestrator/backend/app/workers/run_worker.py`
  - `source/runtime/manager-orchestrator/backend/app/services/orchestrator.py`
  - `source/runtime/manager-orchestrator/backend/app/api/routes/runs.py`
- 핵심 반영
  - background worker claim/maintenance
  - retry backoff, stale reclaim, dead-letter replay
  - run/step 재시도 및 replay API 제공

## 3) Approval + RBAC + Project Membership
- 매핑 파일
  - `source/runtime/manager-orchestrator/backend/app/api/routes/approvals.py`
  - `source/runtime/manager-orchestrator/backend/app/api/deps.py`
  - `source/runtime/manager-orchestrator/backend/app/models/project_membership.py`
  - `source/runtime/manager-orchestrator/backend/app/models/project_membership_invite.py`
  - `source/runtime/manager-orchestrator/backend/app/models/project_access_request.py`
- 핵심 반영
  - role 기반 접근 제어
  - 단계 승인(approval) + inbox
  - 프로젝트 멤버십/초대/접근요청 흐름

## 4) Artifact/Event/Audit(Replay 포함) 추적 체계
- 매핑 파일
  - `source/runtime/manager-orchestrator/backend/app/models/artifact.py`
  - `source/runtime/manager-orchestrator/backend/app/models/event.py`
  - `source/runtime/manager-orchestrator/backend/app/models/run_replay_audit.py`
  - `source/runtime/manager-orchestrator/backend/app/api/routes/artifacts.py`
  - `source/runtime/manager-orchestrator/backend/app/api/routes/runs.py`
- 핵심 반영
  - step output/tool report/rag context artifact 저장
  - event 로그 저장
  - replay audit/history/diff 조회

## 5) RAG + Project Knowledge + Reindex
- 매핑 파일
  - `source/runtime/manager-orchestrator/backend/app/services/rag_service.py`
  - `source/runtime/manager-orchestrator/backend/app/services/vector_store.py`
  - `source/runtime/manager-orchestrator/backend/app/models/project_knowledge.py`
  - `source/runtime/manager-orchestrator/backend/app/api/routes/projects.py`
  - `source/runtime/manager-orchestrator/backend/app/api/routes/artifacts.py`
- 핵심 반영
  - 프로젝트 지식 저장/조회
  - vector store 연동 조회
  - project/run artifact reindex API

## 6) Runner Sandbox 격리
- 매핑 파일
  - `source/runtime/manager-orchestrator/backend/app/services/sandbox.py`
  - `source/runtime/manager-orchestrator/backend/app/services/tool_runner.py`
  - `source/runtime/manager-orchestrator/backend/app/core/config.py`
  - `source/runtime/manager-orchestrator/sandbox-images/*`
- 핵심 반영
  - local/docker sandbox 실행 모드
  - docker 보안 옵션(cap-drop/no-new-privileges/read-only 등)
  - stack별 sandbox image 분리

---

## 적용 전체 소스 패키지 생성
아래 스크립트를 실행하면, 전달용 압축 파일을 `work/dist/` 에 생성합니다.

```bash
bash work/package_applied_source.sh
```

생성 산출물:
- `work/dist/project-agent-ai-applied-source-YYYYMMDD-HHMMSS.tar.gz`

포함 범위:
- `source/`
- `DOC/source_project_analysis.md`
- `DOC/work_step_timeline_replan.md`
- `DOC/applied_source_package_guide.md`
