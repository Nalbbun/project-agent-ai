# Phase 4 후속 적용 요약

작성일: 2026-04-15  
기준 소스: `ai_managerr_fullstack_phase4_ops_auth_approval.zip` 기반 추가 반영본  
기준 문서: `PHASE4_PROGRESS_APPLIED.md`

## 1. 이전 반영본의 단계 위치

직전 반영본은 다음 수준이었습니다.

- Phase 1: 완료
- Phase 2: 완료
- Phase 3: 완료 수준
- Phase 4: **1차 운영 고도화 반영 완료**

즉, 직전 반영본은

> **운영형 auth/RBAC + approval + worker observability + retry/backoff**

까지 포함한 **Phase 4 1차 적용본**이었습니다.

## 2. 이번 반영의 목표

이번 반영은 Phase 4 후속 과제 중 아래 항목을 실제 소스에 추가하는 것이 목적이었습니다.

1. SSE 기반 실시간 run 관측
2. stale run 회수 및 dead-letter 처리
3. 프로젝트 단위 권한 세분화
4. multi-stage approval
5. 실제 embedding provider 연동을 위한 확장점

## 3. 이번에 실제 반영한 내용

### 3.1 SSE 기반 실시간 관측 추가

반영 파일:
- `backend/app/api/routes/runs.py`
- `frontend/src/api/client.ts`
- `frontend/src/pages/RunDetailPage.tsx`

반영 내용:
- `/api/runs/{run_id}/stream` 추가
- `EventSource` 기반 snapshot 스트리밍 연결
- Run detail 화면에서 polling 대신 실시간 snapshot 수신
- stream 연결 상태 표시

즉, 이제 run detail은 수동 새로고침 없이 상태/이벤트/approval/artifact 변화를 실시간에 가깝게 반영할 수 있습니다.

### 3.2 stale run 회수 및 dead-letter 처리 추가

반영 파일:
- `backend/app/services/job_queue.py`
- `backend/app/services/worker_service.py`
- `backend/app/workers/run_worker.py`
- `backend/app/api/routes/workers.py`
- `.env.example`

반영 내용:
- `claim_next_pending_run(worker_id)` 도입
- `reclaim_stale_runs()` 추가
- `dead_letter_exhausted_runs()` 추가
- worker maintenance API 추가
- `QUEUE_DEAD_LETTER_ATTEMPTS` 환경값 추가
- worker loop 에 stale reclaim + dead-letter maintenance 반영

즉, 이제 장시간 멈춘 run 을 다시 queue 로 회수하거나, 재시도 한계를 넘긴 run 을 `dead_lettered` 상태로 분리할 수 있습니다.

### 3.3 프로젝트 단위 권한 세분화 추가

반영 파일:
- `backend/app/models/project_membership.py`
- `backend/app/models/__init__.py`
- `backend/app/api/deps.py`
- `backend/app/api/routes/projects.py`
- `backend/app/api/routes/runs.py`
- `backend/app/api/routes/artifacts.py`
- `backend/app/api/routes/approvals.py`
- `backend/app/api/routes/dashboard.py`
- `db/init/001_schema.sql`
- `frontend/src/pages/ProjectsPage.tsx`
- `frontend/src/App.tsx`
- `frontend/src/components/Layout.tsx`
- `frontend/src/types.ts`
- `frontend/src/api/client.ts`

반영 내용:
- `project_membership` 모델 추가
- project별 `viewer / reviewer / editor / owner` 권한 체계 도입
- admin은 전체 접근, 나머지는 membership 기준 접근
- project 생성 시 생성자에게 `owner` 자동 부여
- runs / artifacts / approvals / dashboard 도 project membership 기준 필터링
- 프로젝트/지식/멤버십 관리 화면 1차 추가
- 사용자 목록 API 추가 (`/api/auth/users`)

즉, 이제 운영 콘솔은 단순 전역 권한만이 아니라 **프로젝트 단위 권한**까지 반영합니다.

### 3.4 multi-stage approval 추가

반영 파일:
- `backend/app/core/config.py`
- `backend/app/models/approval.py`
- `backend/app/schemas/approval.py`
- `backend/app/services/approval_service.py`
- `backend/app/services/orchestrator.py`
- `backend/app/api/routes/approvals.py`
- `db/init/001_schema.sql`
- `.env.example`
- `frontend/src/pages/RunDetailPage.tsx`
- `frontend/src/types.ts`

반영 내용:
- `APPROVAL_POLICY` 설정 추가
  - 예: `manager-merge=reviewer>admin`
- approval row 에 `stage_index`, `stage_total` 추가
- 같은 phase 에 대해 approval chain 생성
- 첫 단계 승인 후 다음 단계 approval 이 `queued -> pending` 으로 전이
- 마지막 단계 승인 시 run 자동 재개
- UI 에 approval stage 표시

즉, approval 은 이제 단일 승인에서 벗어나 **순차 다단계 승인 흐름**을 지원합니다.

### 3.5 embedding provider 확장점 추가

반영 파일:
- `backend/app/services/vector_store.py`
- `backend/app/core/config.py`
- `.env.example`

반영 내용:
- `VECTOR_EMBEDDING_PROVIDER=hash | openai-compatible`
- `VECTOR_EMBEDDING_BASE_URL`
- `VECTOR_EMBEDDING_API_KEY`
- `VECTOR_EMBEDDING_MODEL`
- provider 지정 시 `/embeddings` 호출 기반 원격 embedding 지원
- 실패 시 기존 hash embedding fallback 유지

즉, 이제 벡터 검색은 로컬 hash embedding만이 아니라 **OpenAI-compatible embedding endpoint** 로도 확장할 수 있습니다.

## 4. 지금 이 반영본은 어디까지 왔는가

### Phase 기준
- Phase 1: 완료
- Phase 2: 완료
- Phase 3: 완료 수준
- Phase 4: **2차 운영 고도화 반영 진행본**

### 해석
이번 반영으로 Phase 4의 아래 항목은 실제 소스 수준으로 들어갔습니다.

- SSE 실시간 관측
- stale/dead-letter 운영 처리
- 프로젝트 단위 권한 세분화
- multi-stage approval
- embedding provider 확장점

다만 아직 **Phase 4 완전 종료**라고 보지는 않습니다.
남아 있는 핵심은 아래입니다.

- sandbox 기반 runner 격리 실행
- websocket/SSE 를 dashboard / workers 까지 전면 확대
- 승인 UI 추가 고도화 (대기함/승인 이력 중심)
- stale step / dead-letter replay 정책 고도화
- project membership UI 세부 보완

즉, 이번 반영본은

> **Phase 4 2차 적용본 (실시간 관측 + 운영 회수 정책 + 프로젝트 권한 + 다단계 승인)**

으로 보는 것이 가장 정확합니다.

## 5. 검증 결과

- backend Python `compileall` 통과
- router_service Python `compileall` 통과
- backend `pytest` 14건 통과

## 6. 최종 결론

이번 반영으로, 소스는 더 이상 단순한 운영 고도화 1차 수준이 아니라,

- **실시간 run 관측(SSE)**
- **stale run reclaim / dead-letter maintenance**
- **project membership 기반 접근 제어**
- **multi-stage approval**
- **실제 embedding provider 연계 확장점**

까지 포함한

> **Phase 4 후속 적용본**

으로 올라왔습니다.

다음 자연스러운 순서는 아래입니다.

1. runner sandbox 격리
2. dashboard/workers 실시간 스트리밍 확장
3. approval inbox / review queue UI
4. stale step replay / dead-letter requeue 세분화
5. 실제 embedding provider 운영값 연결 및 citation 강화
