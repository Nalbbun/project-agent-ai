# SW 운영 매뉴얼

## 1. 운영 목적

운영자는 Manager / Orchestrator SW가 안정적으로 run을 생성, queue 처리, role routing, approval, artifact/event/audit 추적, RAG/reindex, sandbox runner를 수행하는지 확인한다.

## 2. 운영자 역할

권장 역할 구분:

- `admin`: 전체 시스템 관리, 사용자/권한/삭제 권한
- `operator`: run 생성/실행/재시도, worker maintenance
- `reviewer`: approval 처리
- `viewer`: 조회 전용

## 3. 일일 점검 항목

### 3.1 컨테이너 상태

```powershell
cd C:\Nalbbun_Project\project-agent-ai\source\runtime\manager-orchestrator
docker compose ps
```

정상 기준:

- 모든 컨테이너가 `Up`
- `postgres`, `qdrant`, `router` healthcheck 정상

### 3.2 Health 확인

```powershell
curl http://localhost:8080/health/live
curl http://localhost:8080/health/ready
curl http://localhost:8080/health
```

중요 필드:

- `status`
- `simulation_mode`
- `job_mode`
- `vector_store`
- `workers`
- `runs`
- `auth_enabled`
- `approval_enabled`

### 3.3 Foundation Guard 확인

UI:

- Dashboard > Foundation Guard

API:

```powershell
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8080/api/foundation/guard
```

확인 항목:

- Router forced path + role routing
- Queue/worker + retry/backoff + dead-letter
- Approval + RBAC + project membership
- Artifact/event/audit tracking with replay
- RAG + project knowledge + reindex
- Runner sandbox isolation

`fail`은 즉시 조치 대상이고, `warn`은 운영 정책에 따라 개선한다.

## 4. Worker 운영

UI:

- Workers 메뉴

점검 항목:

- worker count
- active worker count
- stale worker count
- current run
- current step phase

stale run 정리:

```powershell
curl -X POST -H "Authorization: Bearer <TOKEN>" http://localhost:8080/api/workers/maintenance
```

결과:

- `reclaimed_runs`
- `dead_lettered_runs`

## 5. Run 운영

### 5.1 Run 생성

UI:

- Runs > Create Run

필수 입력:

- Project
- Execution mode: `background` 권장
- Title
- User request

### 5.2 Run 실행

생성 후 Run Detail 화면에서 Execute를 실행한다.

처리 단계:

1. manager-plan
2. pm
3. architect
4. dev-fe
5. dev-be
6. dev-db
7. qa
8. secops
9. manager-merge

### 5.3 Run 상태

주요 상태:

- `draft`
- `queued`
- `running`
- `waiting_approval`
- `retrying`
- `completed`
- `failed`
- `blocked`

Queue 상태:

- `pending`
- `queued`
- `running`
- `retry_scheduled`
- `waiting_approval`
- `dead_lettered`
- `completed`

## 6. Approval 운영

UI:

- Approvals 메뉴
- Dashboard > Approval Alerts

처리 기준:

- `pending`: 현재 사용자가 승인 가능할 수 있음
- `queued`: 다른 role 또는 다음 stage 대기
- overdue/due soon은 SLA 위반 또는 임박 상태

승인:

- Approve 버튼
- 필요 시 note 입력

반려:

- Reject 버튼
- 반려 사유 note 입력 권장

## 7. Project Knowledge / RAG 운영

UI:

- Projects > Knowledge

운영 절차:

1. 프로젝트 선택
2. Knowledge title/content 등록
3. Reindex Knowledge 실행
4. 새 run에서 RAG context 반영 여부 확인

API:

```powershell
curl -X POST -H "Authorization: Bearer <TOKEN>" http://localhost:8080/api/projects/<PROJECT_ID>/knowledge/reindex
```

## 8. Artifact/Event/Audit 운영

Run Detail에서 확인:

- Steps
- Events
- Artifacts
- Replay History
- Replay Diff

장애 분석 시 우선순위:

1. Step error message
2. Events
3. Artifacts
4. Replay audit
5. Worker 상태

## 9. Dead-letter / Replay 운영

Dead-letter 또는 실패 run은 다음 방식으로 복구한다.

지원 모드:

- `requeue`
- `from-last-failed`
- `from-phase`
- `full-reset`

권장 순서:

1. 장애 원인 확인
2. 일시 장애면 `from-last-failed`
3. 특정 단계 산출물이 깨졌으면 `from-phase`
4. 요구사항 자체가 바뀌었으면 새 run 생성
5. 데이터 전체 재생성이 필요하면 `full-reset`

## 10. 로그 확인

```powershell
docker compose logs -f backend-api
docker compose logs -f backend-worker
docker compose logs -f router
docker compose logs -f postgres
docker compose logs -f qdrant
```

최근 로그만 확인:

```powershell
docker compose logs --tail 200 backend-api
```

## 11. 백업 권장

정기 백업 대상:

- PostgreSQL volume
- Qdrant volume
- `artifacts/`
- `.env`
- `config/agents.yaml`
- router config

운영 변경 전 백업:

```powershell
docker compose down
```

이후 volume 또는 DB dump 방식으로 백업한다.

