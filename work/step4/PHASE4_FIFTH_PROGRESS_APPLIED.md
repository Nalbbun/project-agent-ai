# Phase 4 5차 진행 반영 요약

작성일: 2026-04-15  
기준 소스: `ai_managerr_fullstack_phase4_fourth_progress.zip` 기반 추가 반영본  
기준 문서: `PHASE4_FOURTH_PROGRESS_APPLIED.md`

## 이전 단계 위치
직전 반영본은 아래 수준이었습니다.

- Phase 1: 완료
- Phase 2: 완료
- Phase 3: 완료 수준
- Phase 4: **4차 운영 고도화 반영 진행본**

즉, 직전 반영본은

> **approval inbox live stream + sandbox runner image split + replay audit/history + approval/project membership UI 강화**

까지 포함한 상태였습니다.

## 이번 반영의 목표
이번 반영은 사용자가 지정한 다음 순서를 실제 소스에 반영하는 것이 목적이었습니다.

1. approval/dashboard 통합 통계 고도화
2. replay diff 시각화
3. sandbox image CI/CD
4. membership invite/request workflow
5. approval SLA/alert

## 이번에 실제 반영한 내용

### 1. approval/dashboard 통합 통계 고도화
반영 파일:
- `runtime/manager-orchestrator/backend/app/api/routes/dashboard.py`
- `runtime/manager-orchestrator/backend/app/api/routes/approvals.py`
- `runtime/manager-orchestrator/backend/app/schemas/run.py`
- `runtime/manager-orchestrator/backend/app/schemas/approval.py`
- `runtime/manager-orchestrator/frontend/src/pages/DashboardPage.tsx`
- `runtime/manager-orchestrator/frontend/src/pages/ApprovalInboxPage.tsx`
- `runtime/manager-orchestrator/frontend/src/types.ts`

반영 내용:
- Dashboard summary 에 actionable/queued/overdue/due-soon approval 수 추가
- pending membership invite / access request 수를 dashboard 에 통합 반영
- approval alert snapshot 을 dashboard 에 포함
- project hotspot 통계 추가
- Approval inbox snapshot 에 overdue_count / due_soon_count / by_phase / by_project 추가

즉, dashboard 와 approval inbox 가 이제 분리된 개별 화면이 아니라,
**운영자가 승인 병목과 프로젝트별 대기 상태를 함께 파악할 수 있는 통합 통계 구조**가 되었습니다.

### 2. replay diff 시각화
반영 파일:
- `runtime/manager-orchestrator/backend/app/services/orchestrator.py`
- `runtime/manager-orchestrator/backend/app/api/routes/runs.py`
- `runtime/manager-orchestrator/backend/app/schemas/run.py`
- `runtime/manager-orchestrator/frontend/src/pages/RunDetailPage.tsx`
- `runtime/manager-orchestrator/frontend/src/api/client.ts`
- `runtime/manager-orchestrator/frontend/src/types.ts`

반영 내용:
- dead-letter replay 시 `before_steps`, `after_steps`, `reset_step_ids`, `target` 정보를 audit.details 에 저장
- `/api/runs/{run_id}/replay-history/{audit_id}/diff` 추가
- Run detail 화면에서 replay history 항목 선택 시 diff 요약 및 before/after 시각화 제공

즉, replay 는 이제 단순 이력 조회를 넘어,
**어떤 step 이 어떤 상태에서 어떤 범위로 reset 되었는지 시각적으로 확인**할 수 있습니다.

### 3. sandbox image CI/CD
반영 파일:
- `.github/workflows/sandbox-images.yml`
- `runtime/manager-orchestrator/sandbox-images/build-images.sh`
- `runtime/manager-orchestrator/sandbox-images/README.md`

반영 내용:
- GitHub Actions 기반 sandbox image build/push workflow 추가
- python / node / java runner image matrix build
- GHCR 기준 latest + sha tag push 예시 반영
- 로컬 빌드 helper script 추가

즉, sandbox runner 이미지는 이제 수동 빌드 전제가 아니라,
**운영용 이미지를 지속적으로 빌드/배포할 수 있는 CI/CD 출발점**을 갖추게 되었습니다.

### 4. membership invite/request workflow
반영 파일:
- `runtime/manager-orchestrator/backend/app/models/project_membership_invite.py`
- `runtime/manager-orchestrator/backend/app/models/project_access_request.py`
- `runtime/manager-orchestrator/backend/app/models/__init__.py`
- `runtime/manager-orchestrator/backend/app/api/routes/projects.py`
- `runtime/manager-orchestrator/backend/app/schemas/project.py`
- `runtime/manager-orchestrator/db/init/001_schema.sql`
- `runtime/manager-orchestrator/frontend/src/pages/ProjectsPage.tsx`
- `runtime/manager-orchestrator/frontend/src/api/client.ts`
- `runtime/manager-orchestrator/frontend/src/types.ts`

반영 내용:
- project membership invite 모델/테이블 추가
- project access request 모델/테이블 추가
- owner 가 invite 생성 가능
- invitee 가 accept / decline 가능
- 비멤버 사용자가 access request 생성 가능
- owner 가 approve / reject 가능
- 승인 시 project membership 자동 생성/갱신
- Projects UI 에 invites / my invites / access requests / my requests 화면 반영

즉, 프로젝트 권한 운영은 이제 직접 membership 을 꽂아 넣는 수준을 넘어,
**초대와 접근 요청을 처리하는 실무형 workflow** 로 확장되었습니다.

### 5. approval SLA/alert
반영 파일:
- `runtime/manager-orchestrator/backend/app/core/config.py`
- `runtime/manager-orchestrator/backend/app/models/approval.py`
- `runtime/manager-orchestrator/backend/app/services/approval_service.py`
- `runtime/manager-orchestrator/backend/app/api/routes/approvals.py`
- `runtime/manager-orchestrator/backend/app/schemas/approval.py`
- `runtime/manager-orchestrator/.env.example`
- `runtime/manager-orchestrator/frontend/src/pages/ApprovalInboxPage.tsx`
- `runtime/manager-orchestrator/frontend/src/pages/DashboardPage.tsx`

반영 내용:
- `APPROVAL_SLA_HOURS`, `APPROVAL_ALERT_BEFORE_MINUTES`, `APPROVAL_SLA_PHASE_HOURS` 설정 추가
- approval 생성/승격 시 `due_at` 설정
- overdue / due-soon 판정 로직 추가
- `/api/approvals/alerts` 추가
- approval inbox / dashboard 에 SLA 상태와 경고 카드 반영

즉, approval 은 이제 단순 대기 상태가 아니라,
**SLA 기준으로 기한 초과 및 임박 상태를 추적할 수 있는 alert 구조**까지 갖추게 되었습니다.

## 지금 이 반영본의 단계 평가
- Phase 1: 완료
- Phase 2: 완료
- Phase 3: 완료 수준
- Phase 4: **5차 운영 고도화 반영 진행본**

즉, 이번 반영본은

> **Phase 4 5차 적용본 (approval/dashboard 통합 통계 + replay diff + sandbox CI/CD + membership workflow + approval SLA/alert)**

으로 보는 것이 맞습니다.

## 검증 결과
- backend Python `compileall` 통과
- router_service Python `compileall` 통과
- backend `pytest` 14건 통과

## 아직 남은 자연스러운 다음 단계
- approval / membership notification 채널(이메일/슬랙/웹훅)
- replay diff 시 step payload field-level diff 고도화
- sandbox image signing / provenance / 정책 검증
- invite/request/approval 전부에 audit trail drill-down 추가
- dashboard 에 approval/member workflow drill-down 링크 강화

## 최종 결론
이번 반영으로 소스는 더 이상 단순한 운영 고도화 4차 수준이 아니라,

- **approval/dashboard 통합 통계**
- **replay diff 시각화**
- **sandbox image CI/CD**
- **membership invite/request workflow**
- **approval SLA/alert**

까지 포함한

> **Phase 4 5차 운영 고도화 반영본**

으로 올라왔습니다.
