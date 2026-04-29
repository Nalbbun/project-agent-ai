# 시스템 설치 및 환경 구성 매뉴얼

## 1. 대상 SW

Manager / Orchestrator Runtime은 멀티 에이전트 작업 실행 플랫폼이다.

구성 요소:

- Frontend: React + Vite
- Backend API: FastAPI
- Worker: background run 실행기
- PostgreSQL: run, step, event, artifact, auth 저장소
- Qdrant: RAG/vector store
- Router: role 기반 OpenAI-compatible LLM 라우터
- Sandbox Runner: build/test/lint/type/scan 실행 격리

## 2. 사전 준비

필수:

- Docker Desktop 또는 Docker Engine
- Docker Compose v2
- Git
- 최소 메모리 8GB 이상 권장

LLM을 실제 연결할 경우 추가 필요:

- vLLM 또는 Ollama serving 환경
- role별 LoRA/adapter 준비
- router config의 backend endpoint 접근 가능

## 3. 소스 위치

실행 기준 디렉터리:

```powershell
cd C:\Nalbbun_Project\project-agent-ai\source\runtime\manager-orchestrator
```

관련 디렉터리:

- Runtime: `source/runtime/manager-orchestrator`
- Router: `source/runtime/work_proxy_deploy`
- Learning assets: `source/learning`
- 작업 이력: `work/`
- 문서: `DOC/`

## 4. 환경 파일 생성

```powershell
Copy-Item .env.example .env
```

운영 전 필수 확인 항목:

```env
SIMULATION_MODE=true
USE_ROUTER=true
JOB_MODE=background
RAG_ENABLED=true
VECTOR_STORE_ENABLED=true
RUNNER_SANDBOX_MODE=docker
RUNNER_SANDBOX_NETWORK_ENABLED=false
AUTH_ENABLED=true
APPROVAL_ENABLED=true
```

초기 검증은 `SIMULATION_MODE=true`로 진행한다. 실제 LLM을 사용할 때만 `SIMULATION_MODE=false`로 전환한다.

## 5. 비밀번호 변경

운영 환경에서는 `.env`에서 다음 값을 변경한다.

```env
AUTH_ADMIN_PASSWORD=change-this
AUTH_OPERATOR_PASSWORD=change-this
AUTH_REVIEWER_PASSWORD=change-this
AUTH_VIEWER_PASSWORD=change-this
```

주의: 이미 DB가 생성된 뒤에는 seed 계정이 재생성되지 않을 수 있다. 초기 운영 전 비밀번호를 먼저 바꾼 뒤 기동한다.

## 6. Router 설정

Router 설정 파일:

```text
source/runtime/work_proxy_deploy/configs/vllm_request_router.local.yaml
```

확인 항목:

- `router.request_role_fields`에 `extra_body.agent_role`, `metadata.agent_role` 포함
- `unknown_role_action: reject`
- `routes`에 8개 role 존재
  - `manager`
  - `pm`
  - `architect`
  - `dev-fe`
  - `dev-be`
  - `dev-db`
  - `qa`
  - `secops`
- 각 route의 `backend`, `target_model`, `fallback` 확인

## 7. Agent 설정

Agent catalog seed 파일:

```text
source/runtime/manager-orchestrator/config/agents.yaml
```

확인 항목:

- `code`, `role`, `adapter`, `router_role`, `prompt_key`
- `active: true`
- runtime validator required key와 learning schema v2 정렬 상태

정렬 확인:

```powershell
cd C:\Nalbbun_Project\project-agent-ai\source\learning
python scripts/check_runtime_alignment.py --schemas schemas_v2 --report reports/runtime_alignment.step7.json
```

정상 예:

```json
{"ok": true, "checked_agents": 8, "finding_count": 0}
```

## 8. Sandbox 이미지 준비

Runner sandbox를 docker로 사용할 경우 이미지 빌드가 필요하다.

```powershell
cd C:\Nalbbun_Project\project-agent-ai\source\runtime\manager-orchestrator
docker compose -f docker-compose.sandbox-images.yml build
```

설정 확인:

```env
RUNNER_SANDBOX_MODE=docker
RUNNER_SANDBOX_DOCKER_READ_ONLY=true
RUNNER_SANDBOX_NETWORK_ENABLED=false
```

## 9. 서비스 기동

```powershell
cd C:\Nalbbun_Project\project-agent-ai\source\runtime\manager-orchestrator
docker compose up -d --build
```

서비스 확인:

```powershell
docker compose ps
```

주요 컨테이너:

- `postgres`
- `qdrant`
- `router`
- `backend-api`
- `backend-worker`
- `frontend`

## 10. 접속 확인

Frontend:

```text
http://localhost:5174
```

Backend health:

```powershell
curl http://localhost:8080/health
curl http://localhost:8080/health/live
curl http://localhost:8080/health/ready
```

Router health:

```powershell
curl http://localhost:8081/health
```

Foundation Guard:

```powershell
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8080/api/foundation/guard
```

## 11. 로그인 확인

브라우저에서 `http://localhost:5174/login` 접속 후 로그인한다.

초기 계정:

- `admin / admin1234!`
- `operator / operator1234!`
- `reviewer / reviewer1234!`
- `viewer / viewer1234!`

로그인 후 Dashboard 화면이 보이면 기본 설치가 완료된 것이다.

## 12. 종료

```powershell
docker compose down
```

데이터까지 삭제할 경우:

```powershell
docker compose down -v
```

주의: `-v`는 PostgreSQL/Qdrant volume을 삭제한다.

