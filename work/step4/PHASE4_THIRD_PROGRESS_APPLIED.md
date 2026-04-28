# Phase 4 3차 진행 반영 요약

작성일: 2026-04-15  
기준 소스: `ai_managerr_fullstack_phase4_second_progress.zip` 기반 추가 반영본  
기준 문서: `PHASE4_SECOND_PROGRESS_APPLIED.md`

## 이전 단계 위치
직전 반영본은 다음 수준이었습니다.

- Phase 1: 완료
- Phase 2: 완료
- Phase 3: 완료 수준
- Phase 4: **2차 운영 고도화 반영 진행본**

즉, 직전 반영본은

> **실시간 run 관측 + stale/dead-letter 운영 처리 + 프로젝트 단위 권한 + multi-stage approval + embedding provider 확장점**

까지 포함한 상태였습니다.

## 이번 반영의 목표
이번 반영은 사용자가 지정한 다음 순서를 실제 소스에 반영하는 것이 목적이었습니다.

1. runner sandbox 격리
2. dashboard/workers 실시간 스트리밍 확대
3. approval inbox UI
4. dead-letter replay 세분화

## 이번에 실제 반영한 내용

### 1. Runner sandbox 격리 레이어 추가
반영 파일:
- `runtime/manager-orchestrator/backend/app/services/sandbox.py` 신규
- `runtime/manager-orchestrator/backend/app/services/tool_runner.py` 보강
- `runtime/manager-orchestrator/backend/app/core/config.py` 보강
- `runtime/manager-orchestrator/.env.example` 보강

반영 내용:
- `SandboxExecutor` 신규 추가
- `local` 모드: stripped env + sandbox HOME/TMP + workspace cwd 실행
- `docker` 모드: docker binary가 있을 경우 disposable container 실행 지원
- `RUNNER_SANDBOX_MODE`, `RUNNER_SANDBOX_DOCKER_IMAGE`, `RUNNER_SANDBOX_NETWORK_ENABLED` 설정 추가
- `ToolRunner` 가 직접 subprocess 실행 대신 sandbox executor 경유로 명령 실행

즉, runner 는 이제 단순 workspace 실행이 아니라,
**명시적인 sandbox abstraction을 통해 격리 실행 레이어를 거치는 구조**가 되었습니다.

### 2. dashboard/workers 실시간 스트리밍 확대
반영 파일:
- `runtime/manager-orchestrator/backend/app/api/routes/dashboard.py`
- `runtime/manager-orchestrator/backend/app/api/routes/workers.py`
- `runtime/manager-orchestrator/frontend/src/api/client.ts`
- `runtime/manager-orchestrator/frontend/src/pages/DashboardPage.tsx`
- `runtime/manager-orchestrator/frontend/src/pages/WorkersPage.tsx`

반영 내용:
- `/api/dashboard/stream` SSE 추가
- `/api/workers/stream` SSE 추가
- Dashboard가 polling 없이 summary snapshot을 실시간 수신
- Workers 페이지가 worker list + worker summary를 실시간 수신
- stream 상태 표시 추가

즉, 실시간 스트리밍이 이제 run detail을 넘어
**dashboard와 workers 화면까지 확대**되었습니다.

### 3. Approval Inbox UI 추가
반영 파일:
- `runtime/manager-orchestrator/backend/app/schemas/approval.py`
- `runtime/manager-orchestrator/backend/app/api/routes/approvals.py`
- `runtime/manager-orchestrator/frontend/src/pages/ApprovalInboxPage.tsx` 신규
- `runtime/manager-orchestrator/frontend/src/App.tsx`
- `runtime/manager-orchestrator/frontend/src/components/Layout.tsx`
- `runtime/manager-orchestrator/frontend/src/api/client.ts`
- `runtime/manager-orchestrator/frontend/src/types.ts`

반영 내용:
- `/api/approvals/inbox` 추가
- 현재 사용자 역할/프로젝트 접근 범위 내 approval inbox 조회
- actionable approval 과 queued approval 구분
- 승인/반려를 inbox 화면에서 바로 수행
- navigation 에 Approvals 메뉴 추가

즉, approval 은 더 이상 run detail 안에서만 보는 것이 아니라,
**운영자가 승인 대기함 형태로 모아서 처리할 수 있는 UI**까지 갖추게 되었습니다.

### 4. dead-letter replay 세분화
반영 파일:
- `runtime/manager-orchestrator/backend/app/schemas/run.py`
- `runtime/manager-orchestrator/backend/app/api/routes/runs.py`
- `runtime/manager-orchestrator/backend/app/services/orchestrator.py`
- `runtime/manager-orchestrator/frontend/src/api/client.ts`
- `runtime/manager-orchestrator/frontend/src/pages/RunDetailPage.tsx`

반영 내용:
- `DeadLetterReplayRequest` 추가
- `/api/runs/{run_id}/dead-letter/replay` 추가
- replay mode 지원
  - `requeue`
  - `from-last-failed`
  - `from-phase`
  - `full-reset`
- replay 시 해당 step 이후 상태/approval reset
- run detail 에 dead-letter replay action 버튼 추가

즉, dead-letter 복구는 이제 단순 재큐잉이 아니라,
**어느 범위부터 다시 재생할지 선택할 수 있는 세분화된 replay 정책**으로 확장되었습니다.

## 지금 이 반영본의 단계 평가

- Phase 1: 완료
- Phase 2: 완료
- Phase 3: 완료 수준
- Phase 4: **3차 운영 고도화 반영 진행본**

즉, 이번 반영본은

> **Phase 4 3차 적용본 (sandbox runner + dashboard/workers live stream + approval inbox + dead-letter replay refinement)**

으로 보는 것이 맞습니다.

## 검증 결과
- backend Python `compileall` 통과
- backend `pytest` 14건 통과

## 아직 남은 자연스러운 다음 단계
- approval inbox 실시간 스트리밍 추가
- dashboard에서 dead-letter / approval inbox drill-down 고도화
- sandbox docker runner 실제 운영 이미지 분리 및 보안 옵션 강화
- run replay audit/history 별도 테이블화
- project membership / approval UI 세부 UX 보완

## 최종 결론
이번 반영으로 소스는 더 이상 단순한 운영 고도화 2차 수준이 아니라,

- **sandbox 실행 abstraction**
- **dashboard/workers SSE 실시간 스트리밍**
- **approval inbox UI**
- **dead-letter replay 세분화**

까지 포함한

> **Phase 4 3차 운영 고도화 반영본**

으로 올라왔습니다.
