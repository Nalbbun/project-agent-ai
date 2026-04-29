# 장애 발생 처리 가이드

## 1. 장애 대응 원칙

1. 먼저 사용자가 보는 증상을 기록한다.
2. Dashboard와 health endpoint로 전체 상태를 확인한다.
3. run/step/event/artifact 기준으로 장애 범위를 좁힌다.
4. worker/router/vector/DB 중 어느 계층인지 분리한다.
5. 복구 후 replay 또는 retry로 재현 여부를 확인한다.

## 2. 1차 점검 명령

```powershell
cd C:\Nalbbun_Project\project-agent-ai\source\runtime\manager-orchestrator
docker compose ps
curl http://localhost:8080/health/live
curl http://localhost:8080/health/ready
curl http://localhost:8080/health
curl http://localhost:8081/health
```

로그:

```powershell
docker compose logs --tail 200 backend-api
docker compose logs --tail 200 backend-worker
docker compose logs --tail 200 router
docker compose logs --tail 200 postgres
docker compose logs --tail 200 qdrant
```

## 3. 장애 유형별 조치

### 3.1 Frontend 접속 불가

증상:

- `http://localhost:5174` 접속 실패
- 빈 화면
- API 호출 실패

확인:

```powershell
docker compose ps frontend
docker compose logs --tail 200 frontend
```

조치:

1. frontend 컨테이너가 내려갔으면 재기동
   ```powershell
   docker compose up -d frontend
   ```
2. Backend API 주소 확인
   - compose 기준 `VITE_API_BASE=http://localhost:8080/api`
3. 브라우저 캐시 새로고침
4. Backend health 확인

### 3.2 로그인 실패

증상:

- 로그인 실패
- 401 Unauthorized

확인:

- `.env`의 `AUTH_ENABLED`
- seed 계정 비밀번호
- backend-api 로그

조치:

1. 기본 계정 확인
2. DB가 이미 생성된 뒤 `.env` 비밀번호만 바꿨다면 기존 계정에는 반영되지 않을 수 있음
3. 테스트 환경이면 volume 초기화 후 재기동
   ```powershell
   docker compose down -v
   docker compose up -d --build
   ```
4. 운영 환경에서는 DB에서 계정 정책에 맞게 비밀번호 재설정 절차 수행

### 3.3 Backend health ready 실패

증상:

- `/health/live`는 정상이나 `/health/ready` 실패

가능 원인:

- PostgreSQL 연결 실패
- Qdrant 연결 실패
- stale worker/run
- 설정 오류

확인:

```powershell
docker compose ps postgres qdrant backend-api
docker compose logs --tail 200 backend-api
docker compose logs --tail 200 postgres
docker compose logs --tail 200 qdrant
```

조치:

1. DB healthcheck 확인
2. Qdrant readyz 확인
   ```powershell
   curl http://localhost:6333/readyz
   ```
3. `.env`의 `DATABASE_URL`, `VECTOR_STORE_URL` 확인
4. 서비스 재기동
   ```powershell
   docker compose restart backend-api backend-worker
   ```

### 3.4 Router 장애

증상:

- run step 실패
- LLM 호출 실패
- router health 실패
- unknown role 오류

확인:

```powershell
curl http://localhost:8081/health
docker compose logs --tail 200 router
```

설정 확인:

- `source/runtime/work_proxy_deploy/configs/vllm_request_router.local.yaml`
- role별 `routes`
- `target_model`
- `fallback`
- `unknown_role_action`

조치:

1. router 컨테이너 재기동
   ```powershell
   docker compose restart router
   ```
2. backend agent 설정과 router route 정렬 확인
   ```powershell
   cd C:\Nalbbun_Project\project-agent-ai\source\learning
   python scripts/check_runtime_alignment.py --schemas schemas_v2 --report reports/runtime_alignment.step7.json
   ```
3. 실제 vLLM/Ollama endpoint가 살아 있는지 확인
4. 장애 backend가 있으면 fallback route 확인

### 3.5 Worker가 Run을 처리하지 않음

증상:

- Run이 `queued`에서 멈춤
- Dashboard active worker count가 0

확인:

```powershell
docker compose ps backend-worker
docker compose logs --tail 200 backend-worker
```

조치:

1. worker 재기동
   ```powershell
   docker compose restart backend-worker
   ```
2. Workers 화면에서 stale 여부 확인
3. maintenance 실행
   ```powershell
   curl -X POST -H "Authorization: Bearer <TOKEN>" http://localhost:8080/api/workers/maintenance
   ```
4. Run이 dead-lettered면 replay 수행

### 3.6 Run 실패

증상:

- `failed`
- `blocked`
- `dead_lettered`
- 특정 step error

확인 순서:

1. Run Detail > Timeline
2. 실패 step의 error message
3. Events
4. Artifacts
5. Worker logs
6. Router logs

복구 선택:

- 일시 장애: Retry 또는 `from-last-failed`
- 특정 phase 산출물 오류: `from-phase`
- 요구사항 변경: 새 Run 생성
- 전체 재생성: `full-reset`

API 예:

```powershell
curl -X POST -H "Authorization: Bearer <TOKEN>" http://localhost:8080/api/runs/<RUN_ID>/retry
```

Dead-letter replay:

```powershell
curl -X POST `
  -H "Authorization: Bearer <TOKEN>" `
  -H "Content-Type: application/json" `
  -d "{\"mode\":\"from-last-failed\",\"note\":\"recover after router restart\"}" `
  http://localhost:8080/api/runs/<RUN_ID>/dead-letter/replay
```

### 3.7 Approval 대기에서 멈춤

증상:

- `waiting_approval`
- Approval Inbox에 남아 있음

확인:

- Approvals 메뉴
- required role
- due_at / overdue
- 현재 로그인 사용자 role

조치:

1. reviewer 또는 admin 계정으로 로그인
2. Approvals에서 승인/반려
3. 반려 시 Run은 blocked/approval_rejected 상태가 될 수 있음
4. 승인 후 자동 재개가 안 되면 Run Detail에서 resume/retry

### 3.8 RAG / Reindex 장애

증상:

- Knowledge 등록은 되지만 검색 반영 안 됨
- `/health/ready`에서 vector store warning/fail

확인:

```powershell
curl http://localhost:6333/readyz
docker compose logs --tail 200 qdrant
```

조치:

1. Qdrant 상태 확인
2. `.env` 확인
   ```env
   RAG_ENABLED=true
   VECTOR_STORE_ENABLED=true
   VECTOR_STORE_URL=http://qdrant:6333
   ```
3. Reindex 실행
4. backend-api 재기동

### 3.9 Sandbox 실행 실패

증상:

- tool-report fail
- build/test/lint/type/scan skipped 또는 error

확인:

- `.env`
  ```env
  RUNNER_SANDBOX_MODE=docker
  RUNNER_SANDBOX_NETWORK_ENABLED=false
  ```
- sandbox image 존재 여부

조치:

```powershell
docker compose -f docker-compose.sandbox-images.yml build
docker images | findstr manager-orchestrator-runner
docker compose restart backend-worker
```

### 3.10 Foundation Guard fail/warn

확인:

- Dashboard > Foundation Guard
- API `/api/foundation/guard`

대표 조치:

- Router fail: `USE_ROUTER`, `ROUTER_BASE_URL`, router route 확인
- Queue fail: `JOB_MODE=background`, retry/backoff 설정 확인
- Approval/RBAC fail: `AUTH_ENABLED`, `APPROVAL_ENABLED`, approval policy 확인
- RAG warn: `RAG_ENABLED`, `VECTOR_STORE_ENABLED`, Qdrant 확인
- Sandbox warn: `RUNNER_SANDBOX_MODE=docker`, network disabled 확인

## 4. 장애 보고 양식

장애 보고 시 아래 정보를 포함한다.

```text
발생 시각:
사용자/역할:
프로젝트:
Run ID:
Step/Phase:
화면 증상:
API 응답:
관련 로그:
최근 설정 변경:
복구 시도:
현재 상태:
```

## 5. 복구 후 확인

복구 후 반드시 확인한다.

```powershell
docker compose ps
curl http://localhost:8080/health/ready
curl http://localhost:8081/health
```

UI 확인:

- Dashboard 정상
- Foundation Guard pass 또는 허용 가능한 warn
- Workers active
- Run 재실행 또는 replay 성공
- Approval 대기 없음 또는 담당자 확인 완료

