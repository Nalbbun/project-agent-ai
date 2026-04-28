# Step 5 - Foundation Guard 적용 이력

작성일: 2026-04-28

## 목표

`DOC/work_step_timeline_replan.md`의 Must Keep 항목을 런타임에서 계속 확인할 수 있도록 운영 보호 점검 장치를 추가했다.

대상 Must Keep:

1. Router 강제 경유 + 역할 라우팅
2. Queue/Worker + Retry/Backoff + Dead-letter
3. Approval + RBAC + Project Membership
4. Artifact/Event/Audit(Replay 포함) 추적 체계
5. RAG + Project Knowledge + Reindex
6. Runner Sandbox 격리

## 적용 내용

### Backend

- `GET /api/foundation/guard` API 추가
- Must Keep 6개 항목을 `pass`, `warn`, `fail` 상태로 점검
- Router 설정, active agent router role, queue/retry/dead-letter 설정, auth/approval 정책, replay audit, project knowledge/vector/RAG, runner sandbox 설정을 evidence로 반환
- 기존 RBAC 흐름을 유지하여 `admin/operator/reviewer/viewer` 인증 사용자만 조회 가능
- FastAPI main router에 foundation route 등록
- Must Keep 코드 목록 누락 방지용 테스트 추가

### Frontend

- Dashboard에 Foundation Guard 섹션 추가
- 각 Must Keep 항목의 상태와 요약을 카드 형태로 노출
- foundation guard API 타입 및 client 함수 추가

## 변경 파일

- `source/runtime/manager-orchestrator/backend/app/api/routes/foundation.py`
- `source/runtime/manager-orchestrator/backend/app/schemas/foundation.py`
- `source/runtime/manager-orchestrator/backend/app/services/foundation_guard.py`
- `source/runtime/manager-orchestrator/backend/app/tests/test_foundation_guard.py`
- `source/runtime/manager-orchestrator/backend/app/api/routes/__init__.py`
- `source/runtime/manager-orchestrator/backend/app/main.py`
- `source/runtime/manager-orchestrator/frontend/src/api/client.ts`
- `source/runtime/manager-orchestrator/frontend/src/pages/DashboardPage.tsx`
- `source/runtime/manager-orchestrator/frontend/src/styles.css`
- `source/runtime/manager-orchestrator/frontend/src/types.ts`

## 검증

- Backend syntax check: `python -m compileall app` 통과
- Pytest: 현재 작업 환경에 `pytest` 모듈이 없어 실행 불가
- Frontend build: `node_modules`가 없어 `tsc`/`vite` 실행 불가

## 산출물

- 변경 소스 압축 파일: `work/dist/step5_foundation_guard_sources.zip`

## 다음 권장 작업

1. CI 환경 또는 dependency 설치 환경에서 backend pytest 전체 실행
2. `npm install` 후 frontend `npm run build` 실행
3. 운영 프로파일에서 `RAG_ENABLED=true`, `VECTOR_STORE_ENABLED=true`, `RUNNER_SANDBOX_MODE=docker` 기준으로 Foundation Guard warning 제거
