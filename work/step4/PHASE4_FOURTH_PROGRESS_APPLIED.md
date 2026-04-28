# Phase 4 4차 진행 반영 요약

작성일: 2026-04-15  
기준 소스: `ai_managerr_fullstack_phase4_third_progress.zip` 기반 추가 반영본  
기준 문서: `PHASE4_THIRD_PROGRESS_APPLIED.md`

## 이전 단계 위치
직전 반영본은 다음 수준이었습니다.

- Phase 1: 완료
- Phase 2: 완료
- Phase 3: 완료 수준
- Phase 4: **3차 운영 고도화 반영 진행본**

즉, 직전 반영본은

> **sandbox runner + dashboard/workers live stream + approval inbox + dead-letter replay refinement**

까지 포함한 상태였습니다.

## 이번 반영의 목표
이번 반영은 사용자가 지정한 다음 순서를 실제 소스에 반영하는 것이 목적이었습니다.

1. approval inbox 실시간 스트리밍
2. sandbox docker runner 운영 이미지 분리
3. run replay audit/history
4. approval/project membership UI 보강

## 이번에 실제 반영한 내용

### 1. Approval inbox 실시간 스트리밍 추가
반영 파일:
- `runtime/manager-orchestrator/backend/app/api/routes/approvals.py`
- `runtime/manager-orchestrator/backend/app/schemas/approval.py`
- `runtime/manager-orchestrator/frontend/src/api/client.ts`
- `runtime/manager-orchestrator/frontend/src/pages/ApprovalInboxPage.tsx`

반영 내용:
- `/api/approvals/inbox/stream` SSE 추가
- inbox snapshot 에 `items / actionable_count / queued_count / total_count` 포함
- 프론트 Approval Inbox 화면이 EventSource 기반으로 실시간 snapshot 수신
- project/phase/view filter 및 inbox 통계 표시

즉, approval inbox 는 이제 단순 목록 조회가 아니라,
**실시간 운영 대기함**으로 동작합니다.

### 2. Sandbox docker runner 운영 이미지 분리
반영 파일:
- `runtime/manager-orchestrator/backend/app/core/config.py`
- `runtime/manager-orchestrator/backend/app/services/sandbox.py`
- `runtime/manager-orchestrator/backend/app/services/tool_runner.py`
- `runtime/manager-orchestrator/.env.example`
- `runtime/manager-orchestrator/sandbox-images/python/Dockerfile`
- `runtime/manager-orchestrator/sandbox-images/node/Dockerfile`
- `runtime/manager-orchestrator/sandbox-images/java/Dockerfile`
- `runtime/manager-orchestrator/sandbox-images/README.md`
- `runtime/manager-orchestrator/docker-compose.sandbox-images.yml`

반영 내용:
- stack 별 docker runner image map 지원
  - python
  - node
  - java-maven / java-gradle
- docker sandbox 실행 시 보안 옵션 강화
  - `--cap-drop=ALL`
  - `--security-opt=no-new-privileges`
  - `--read-only`
  - `--tmpfs`
  - `--pids-limit`
  - `--memory`
  - `--cpus`
  - `--network none` 기본
- 실제 운영용 사전 빌드 이미지용 Dockerfile 분리

즉, sandbox docker runner 는 이제 단일 테스트 이미지가 아니라,
**운영용 스택별 이미지 분리 구조**까지 갖추게 되었습니다.

### 3. Run replay audit/history 추가
반영 파일:
- `runtime/manager-orchestrator/backend/app/models/run_replay_audit.py`
- `runtime/manager-orchestrator/backend/app/models/__init__.py`
- `runtime/manager-orchestrator/backend/app/schemas/run.py`
- `runtime/manager-orchestrator/backend/app/services/orchestrator.py`
- `runtime/manager-orchestrator/backend/app/api/routes/runs.py`
- `runtime/manager-orchestrator/db/init/001_schema.sql`
- `runtime/manager-orchestrator/frontend/src/types.ts`
- `runtime/manager-orchestrator/frontend/src/api/client.ts`
- `runtime/manager-orchestrator/frontend/src/pages/RunDetailPage.tsx`

반영 내용:
- `run_replay_audit` 테이블 추가
- dead-letter replay 시 아래 정보 기록
  - requested_by_user_id
  - mode
  - from_phase
  - target_seq / target_phase
  - previous_status / previous_queue_status
  - result_status / result_queue_status
  - replay_group
  - details
- `/api/runs/{run_id}/replay-history` 추가
- Run detail 화면에서 replay history 확인 가능

즉, replay 는 이제 단순 이벤트 로그가 아니라,
**별도 이력 테이블을 가진 audit/history** 로 관리됩니다.

### 4. Approval / Project Membership UI 보강
반영 파일:
- `runtime/manager-orchestrator/backend/app/schemas/project.py`
- `runtime/manager-orchestrator/backend/app/api/routes/projects.py`
- `runtime/manager-orchestrator/frontend/src/pages/ProjectsPage.tsx`
- `runtime/manager-orchestrator/frontend/src/styles.css`
- `runtime/manager-orchestrator/frontend/src/api/client.ts`
- `runtime/manager-orchestrator/frontend/src/types.ts`

반영 내용:
- `/api/projects/{project_id}/summary` 추가
- project summary 에 아래 지표 반영
  - knowledge_count
  - membership_count
  - run_count
  - waiting_approval_count
  - my_access_role
- Projects 페이지에서 summary 카드 표시
- membership filter / remove 액션 추가
- knowledge delete / reindex 액션 추가
- approval inbox 쪽도 filter + 통계 UI 반영

즉, 운영 UI 는 이제 단순 CRUD 목록이 아니라,
**프로젝트 권한/지식/멤버십 운영에 필요한 실질적인 관리 화면**에 가까워졌습니다.

## 지금 이 반영본의 단계 평가
- Phase 1: 완료
- Phase 2: 완료
- Phase 3: 완료 수준
- Phase 4: **4차 운영 고도화 반영 진행본**

즉, 이번 반영본은

> **Phase 4 4차 적용본 (approval inbox live stream + sandbox runner image split + replay audit/history + approval/project membership UI 강화)**

으로 보는 것이 맞습니다.

## 검증 결과
- backend Python `compileall` 통과
- backend `pytest` 14건 통과

## 아직 남은 자연스러운 다음 단계
- approval inbox / dashboard drill-down 통합 통계 고도화
- replay audit diff / step reset 범위 시각화
- sandbox image CI/CD 및 서명 정책
- project membership invite / request workflow
- approval SLA / overdue alerts

## 최종 결론
이번 반영으로 소스는 더 이상 단순한 운영 고도화 3차 수준이 아니라,

- **approval inbox 실시간 스트리밍**
- **sandbox docker runner 운영 이미지 분리**
- **run replay audit/history 별도 저장**
- **approval/project membership UI 강화**

까지 포함한

> **Phase 4 4차 운영 고도화 반영본**

으로 올라왔습니다.
