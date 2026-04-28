# 런타임 안정화 실행 설계서

작성일: 2026-04-15  
대상 소스: `ai_managerr_fullstack_startpack.zip` 내 `runtime/`  
기준 문서: `runtime_stabilization_detailed_checklist.md`

---

## 1. 문서 목적

본 문서는 기존 점검서를 바탕으로, 실제 수정 작업에 바로 착수할 수 있도록 **파일별 수정 포인트**, **신규 생성 파일**, **적용 순서**, **검증 기준**을 명시한 실행 설계서이다.

이번 설계의 목표는 다음 4가지를 우선 달성하는 것이다.

1. `manager-orchestrator` 와 `work_proxy_deploy/router_service` 를 실제 운영 경로로 연결
2. LoRA 선택을 프롬프트 지시가 아니라 **라우터 기반 강제 선택**으로 전환
3. 동기식 실행을 **큐/워커 기반 비동기 실행 구조**로 바꾸기 위한 최소 골격 확보
4. 이후 RAG / Build Runner / Test Runner / Scan Runner 를 무리 없이 붙일 수 있는 구조로 재정렬

---

## 2. 적용 원칙

### 2.1 우선순위 원칙
- **P0**: 실제 연동 시 즉시 오류가 나는 항목
- **P1**: 운영 연결은 되지만 안정성/복구성이 낮은 항목
- **P2**: 품질 고도화를 위해 필요한 항목
- **P3**: 성능/관측성/운영성 향상 항목

### 2.2 구현 원칙
- DB는 **PostgreSQL 전용**으로 통일
- LLM 호출은 모두 **router service 단일 endpoint** 경유
- 역할 식별은 `agent_role` 을 명시적으로 전달
- step 실행은 API 요청 스레드에서 끝내지 않고 **job 실행 구조**로 전환
- step output 은 저장 전 **schema 검증** 통과를 기본으로 함
- RAG/Tool layer 는 step 공통 확장 포인트로 삽입

### 2.3 이번 문서에서 다루는 범위
- `runtime/manager-orchestrator`
- `runtime/work_proxy_deploy`
- 프론트 콘솔 최소 보완

이번 단계에서 **직접 구현하지 않는 것**
- SSO / OAuth 완성형 인증
- 완전한 worker infra (예: Celery+Redis full production)
- 벡터 DB 제품 선정 및 대량 ingest 파이프라인

단, 위 기능이 들어갈 **자리와 인터페이스**는 이번 설계에 반영한다.

---

## 3. 최종 목표 구조

```text
[Frontend Console]
   ↓
[manager-orchestrator API]
   ├─ run create
   ├─ run enqueue
   ├─ run status / events / artifacts
   ↓
[run worker / job executor]
   ↓
[OrchestratorService]
   ├─ context collect
   ├─ rag inject
   ├─ schema validate
   ├─ tool runner invoke
   ↓
[AgentLLMClient]
   ↓
[router service]
   ↓
[vLLM general / coder / exaone]
```

핵심 변화는 다음과 같다.

- 기존: `orchestrator -> agent endpoint 직접 호출`
- 변경: `orchestrator -> router service -> target backend`

---

## 4. 단계별 실행 순서

### Phase 1. P0 즉시 안정화
1. router 단일 endpoint 연결
2. `agent_role` 전달 구조 반영
3. DB Postgres 전용 정리
4. compose healthcheck 정리
5. JSON 응답 파싱 보강

### Phase 2. P1 실행 구조 안정화
1. 비동기 run job 구조 도입
2. 부분 재시도/재개 로직 도입
3. schema validator 연결
4. router retry 정책 반영

### Phase 3. P2 런타임 확장 포인트 삽입
1. RAG service 골격 추가
2. Tool runner 골격 추가
3. artifact/event 모델 확장
4. 프론트 실시간 상태 반영

### Phase 4. P3 운영 고도화
1. 병렬 실행
2. observability
3. auth/RBAC
4. 승인 기반 Human-in-the-loop

---

# 5. 파일별 수정 설계

## 5.1 `runtime/manager-orchestrator/backend/app/core/config.py`

### 현재 문제
- `database_url` 기본값이 sqlite 이다.
- router 연동 설정값이 없다.
- worker/job/RAG/tool runner 관련 설정이 없다.

### 수정 목표
설정 클래스를 **Postgres + Router + Job + RAG + Tool** 기준으로 재정의한다.

### 수정 내용
기존 필드 외 아래 필드를 추가한다.

```python
router_base_url: str = "http://router:8080/v1"
router_bearer_token: str = ""
router_model_name: str = "router-auto"
router_request_role_field: str = "extra_body.agent_role"
use_router: bool = True

job_mode: str = "inline"   # inline | background
worker_poll_interval_seconds: int = 2
max_step_retry_count: int = 2

artifact_dir: str = "/app/artifacts"

rag_enabled: bool = False
rag_provider: str = "local"
rag_top_k: int = 5
rag_timeout_seconds: int = 15

build_runner_enabled: bool = False
security_runner_enabled: bool = False
```

### 구현 포인트
- `database_url` 기본값은 sqlite 제거, `.env` 없으면 startup fail 처리
- `app_env != local` 일 때는 필수 env 누락 시 예외 발생
- `cors_origins_list` 외에 `is_production` 보조 property 추가

### 검증 기준
- `.env` 누락 시 의도한 설정 에러 발생
- router URL, token, job mode 가 설정에서 정상 주입됨

---

## 5.2 `runtime/manager-orchestrator/backend/app/db/session.py`

### 현재 문제
- `create_all()` 과 SQL init 스크립트가 같이 존재해 스키마 drift 위험이 있다.
- sqlite 기본값과 PostgreSQL JSONB 모델이 충돌한다.

### 수정 목표
DB 초기화 경로를 단일화한다.

### 수정 내용
1. `create_db_and_tables()` 는 local 개발 전용으로 제한
2. 운영/compose 경로는 `db/init` 또는 이후 Alembic 으로만 관리
3. DB readiness 검사 함수 추가

### 권장 코드 방향
- `wait_for_db()` 추가
- `create_db_and_tables()` 는 `if settings.app_env == "local-dev-bootstrap":` 인 경우만 사용
- 이후 단계에서 Alembic 도입 시 아래 신규 파일 생성
  - `backend/alembic.ini`
  - `backend/alembic/env.py`
  - `backend/alembic/versions/*.py`

### 검증 기준
- postgres 준비 전 backend 가 무한 실패하지 않고 재시도/대기
- 개발 환경과 compose 환경에서 스키마 생성 경로가 명확히 분리됨

---

## 5.3 `runtime/manager-orchestrator/backend/app/main.py`

### 현재 문제
- startup 에서 바로 `create_db_and_tables()` 호출
- router readiness, config readiness, artifact dir readiness 검사 없음

### 수정 목표
startup 을 “초기화”가 아니라 **의존성 검증 + seed + worker 시작점** 으로 바꾼다.

### 수정 내용
- lifespan 에서 다음 순서로 처리
  1. settings 검증
  2. DB readiness check
  3. seed 실행
  4. artifact directory 생성
  5. `job_mode=background` 이면 worker bootstrap

- health endpoint 를 아래처럼 분리
  - `/health/live`
  - `/health/ready`

### 추가 반영
`/health/ready` 는 아래를 함께 본다.
- DB 연결
- router 연결 여부
- seed agent 존재 여부

### 검증 기준
- backend 기동 시 postgres/routing 준비 상태를 구분해서 보여줌
- readiness 실패와 liveness 실패가 분리됨

---

## 5.4 `runtime/manager-orchestrator/backend/app/models/agent.py`

### 현재 문제
- endpoint/model/adapter 만 저장한다.
- direct backend 기준 모델이라 router 경유 구조를 표현하기 어렵다.

### 수정 목표
에이전트 카탈로그를 “직접 endpoint 호출 정보”가 아니라 “라우팅 정책 정보” 중심으로 바꾼다.

### 수정 내용
기존 필드를 유지하되 아래 필드를 추가한다.

```python
transport: str = Field(default="router", max_length=20)
router_role: str = Field(max_length=40)
request_timeout_seconds: int = Field(default=180)
max_retries: int = Field(default=2)
active: bool = Field(default=True)
```

### 해석 기준
- `endpoint`: router base URL 또는 legacy direct URL
- `model`: 보통 `router-auto`
- `adapter`: 참고 메타데이터용
- `router_role`: 실제 라우터 선택 키

### 검증 기준
- agent seed 후 모든 row 가 `transport=router` 로 들어감
- `router_role` 이 `pm`, `architect`, `dev-fe` 등과 정확히 매칭됨

---

## 5.5 `runtime/manager-orchestrator/backend/app/models/run.py`

### 현재 문제
- run 과 step 에 queue/job 실행 상태를 담을 필드가 부족하다.
- 부분 재시도, 재개, backend trace 정보를 저장하기 어렵다.

### 수정 목표
비동기 실행과 부분 재시도에 필요한 상태 필드를 추가한다.

### `OrchestrationRun` 추가 필드
```python
execution_mode: str = Field(default="inline", max_length=20)
queue_status: str = Field(default="pending", max_length=20)
started_at: Optional[datetime] = None
finished_at: Optional[datetime] = None
last_error: Optional[str] = Field(default=None, sa_column=Column(Text))
metadata: Optional[dict] = Field(default=None, sa_column=Column(JSONB, nullable=True))
```

### `OrchestrationStep` 추가 필드
```python
retry_count: int = Field(default=0)
max_retry_count: int = Field(default=2)
backend_name: Optional[str] = Field(default=None, max_length=80)
target_model: Optional[str] = Field(default=None, max_length=120)
schema_valid: Optional[bool] = Field(default=None)
execution_ms: Optional[int] = None
```

### 검증 기준
- step 완료 후 어떤 backend/model 이 사용됐는지 저장됨
- failed step 만 골라 부분 재실행 가능

---

## 5.6 `runtime/manager-orchestrator/backend/app/models/event.py`

### 현재 문제
- payload 는 저장되지만 trace 정보의 정형 필드가 없다.

### 수정 목표
운영 이벤트를 UI 와 추후 분석에서 바로 활용할 수 있게 표준화한다.

### 수정 내용
추가 필드
```python
event_type: str = Field(default="log", max_length=40)
trace_id: Optional[str] = Field(default=None, max_length=120)
request_id: Optional[str] = Field(default=None, max_length=120)
```

### 이벤트 타입 예시
- `run.created`
- `run.enqueued`
- `step.started`
- `step.completed`
- `step.failed`
- `tool.build.started`
- `tool.scan.completed`

### 검증 기준
- 프론트에서 level 외에 event_type 으로 필터링 가능

---

## 5.7 `runtime/manager-orchestrator/backend/app/models/artifact.py`

### 현재 문제
- content JSON 만 저장한다.
- 파일형 artifact, tool report, raw response 저장 구분이 없다.

### 수정 목표
산출물과 실행 증적을 구분해 저장한다.

### 수정 내용
추가 필드
```python
storage_type: str = Field(default="json", max_length=20)  # json | file | text
path: Optional[str] = Field(default=None, max_length=255)
content_type: Optional[str] = Field(default=None, max_length=120)
summary: Optional[str] = Field(default=None, sa_column=Column(Text))
```

### artifact 유형 예시
- `step-output`
- `raw-llm-response`
- `rag-context`
- `build-report`
- `test-report`
- `scan-report`

### 검증 기준
- raw llm output 과 normalized output 을 별도 보존 가능

---

## 5.8 `runtime/manager-orchestrator/backend/app/schemas/run.py`

### 현재 문제
- API 응답이 동기 실행 기준이다.
- 큐 상태, backend trace, artifact 목록이 드러나지 않는다.

### 수정 목표
프론트가 비동기 실행 상태를 볼 수 있게 응답 스키마를 확장한다.

### 수정 내용
`RunCreate` 에 다음 추가
```python
execution_mode: str = Field(default="background")
```

`StepRead` 에 다음 추가
```python
retry_count: int = 0
max_retry_count: int = 0
backend_name: Optional[str] = None
target_model: Optional[str] = None
schema_valid: Optional[bool] = None
execution_ms: Optional[int] = None
```

`RunRead` 에 다음 추가
```python
queue_status: Optional[str] = None
started_at: Optional[datetime] = None
finished_at: Optional[datetime] = None
last_error: Optional[str] = None
```

신규 스키마 추가
- `RunEnqueueResponse`
- `StepRetryRequest`
- `ArtifactRead`

### 검증 기준
- 프론트에서 step trace / queue 상태를 타입 안전하게 표시 가능

---

## 5.9 `runtime/manager-orchestrator/backend/app/api/routes/runs.py`

### 현재 문제
- `/execute` 가 호출 즉시 전체 step 을 동기 수행한다.
- step 부분 retry/cancel/resume 가 없다.

### 수정 목표
API 를 “즉시 실행”이 아니라 “작업 지시” 형태로 바꾼다.

### 변경 방향
기존 엔드포인트를 아래처럼 개편한다.

#### 유지
- `POST /api/runs`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/events`

#### 변경
- `POST /api/runs/{run_id}/execute` → enqueue 방식으로 변경
- 반환은 `202 Accepted`

#### 신규
- `POST /api/runs/{run_id}/cancel`
- `POST /api/runs/{run_id}/resume`
- `POST /api/runs/{run_id}/steps/{step_id}/retry`
- `GET /api/runs/{run_id}/artifacts`

### 구현 포인트
- `execute_run()` 는 `svc.enqueue_run()` 으로 변경
- `job_mode=inline` 인 경우에만 예전 동기 실행 허용
- 기본은 background

### 검증 기준
- 프론트에서 “실행 요청” 직후 즉시 응답 수신
- 실제 step 진행은 DB 상태 변화로 확인

---

## 5.10 `runtime/manager-orchestrator/backend/app/services/llm_client.py`

### 현재 문제
- router 요구 필드(`agent_role`)를 보내지 않는다.
- `adapter` 를 system prompt 문자열로만 지시한다.
- 응답을 `json.loads(content)` 로 단순 파싱한다.
- router header 결과를 수집하지 않는다.

### 수정 목표
router 전용 클라이언트로 재정의한다.

### 필수 변경 사항
1. request payload 에 `extra_body.agent_role` 포함
2. `model` 은 `router-auto` 사용
3. 인증 토큰 헤더 지원
4. router 가 내려주는 `x-router-backend`, `x-router-model` 읽기
5. JSON extraction fallback 추가

### 권장 요청 형태
```json
{
  "model": "router-auto",
  "messages": [
    {"role": "system", "content": "Always respond in JSON matching the requested schema."},
    {"role": "user", "content": "...prompt..."}
  ],
  "temperature": 0.2,
  "extra_body": {
    "agent_role": "architect"
  },
  "metadata": {
    "run_id": "...",
    "step_id": "..."
  }
}
```

### 파싱 전략
1. `choices[0].message.content` 가 dict 이면 그대로 사용
2. str 이면 JSON 직접 파싱
3. 실패 시 code fence 제거 후 재파싱
4. 그래도 실패하면 raw text 와 함께 예외 반환

### 추가 반환 구조
`invoke()` 는 payload 만 주지 말고 아래 구조를 반환하도록 바꾼다.

```python
{
  "parsed": {...},
  "raw_text": "...",
  "backend_name": "qwen-general",
  "target_model": "architect-lora",
  "latency_ms": 1234
}
```

### 검증 기준
- router 기반 호출이 정상 동작
- code fence 포함 JSON 응답도 파싱 성공
- step 에 backend/model trace 저장 가능

---

## 5.11 `runtime/manager-orchestrator/backend/app/services/orchestrator.py`

### 현재 문제
- 동기식 전체 실행 구조
- step 실행 책임이 너무 많다
- schema validation / RAG / tool runner 훅이 없다.
- 부분 재시도가 안 된다.

### 수정 목표
오케스트레이터를 “실행 조정 서비스”로 재분해한다.

### 권장 분리 구조
기존 파일은 유지하되 내부 책임을 아래 함수로 분리한다.

- `enqueue_run()`
- `execute_run_inline()`
- `execute_run_background()`
- `execute_next_step()`
- `prepare_step_context()`
- `validate_step_output()`
- `record_step_success()`
- `record_step_failure()`

### step 실행 흐름 재설계
1. prior step context 수집
2. RAG context 주입
3. prompt 생성
4. LLM 호출
5. schema 검증
6. 필요 시 tool runner 호출
7. artifact/event 저장
8. 다음 step 전이

### `PIPELINE` 수정 방향
현재는 순차 배열인데, 향후 병렬 실행을 위해 구조를 아래 형태로 확장한다.

```python
PIPELINE = [
  {"seq": 1, "phase": "manager-plan", "agent_code": "manager", "depends_on": []},
  {"seq": 2, "phase": "pm", "agent_code": "pm", "depends_on": ["manager-plan"]},
  {"seq": 3, "phase": "architect", "agent_code": "architect", "depends_on": ["pm"]},
  {"seq": 4, "phase": "dev-fe", "agent_code": "dev-fe", "depends_on": ["architect"]},
  ...
]
```

### retry 정책
- step 단위 retry count 증가
- `max_retry_count` 초과 시 run failed
- `qa`/`secops` 실패 시 `dev-*` 재작업 분기용 hook 추가

### 검증 기준
- 단일 step retry 가능
- step output schema fail 시 completed 가 아니라 failed 처리
- `manager-merge` 는 정상 완료된 산출물만 취합

---

## 5.12 `runtime/manager-orchestrator/backend/app/services/prompts.py`

### 현재 문제
- 모든 역할에 “항상 JSON으로 응답” 수준의 느슨한 지시만 있다.
- schema 수준의 요구와 field contract 가 프롬프트에 없다.

### 수정 목표
역할별 프롬프트에 **출력 스키마 요구**를 포함한다.

### 수정 내용
- 역할별 `required_keys` 정의 추가
- 프롬프트 빌드 시 아래 포함
  - 역할 설명
  - 금지사항
  - required keys
  - output 예시
  - 이전 단계 context 요약
  - 선택적 RAG 컨텍스트

### 권장 구조
```python
PROMPT_SPECS = {
  "architect": {
    "instruction": "...",
    "required_keys": ["architecture_style", "components", "apis", "database", "sequence", "adrs"],
    "forbidden": ["markdown", "explanation outside JSON"]
  }
}
```

### 검증 기준
- step output key 누락 비율 감소
- schema validation pass rate 상승

---

## 5.13 `runtime/manager-orchestrator/backend/app/services/run_reader.py`

### 현재 문제
- events, steps 만 조합하고 artifact, queue metadata 는 노출하지 않는다.

### 수정 목표
프론트가 run 상세를 한 번에 표현할 수 있도록 reader 를 확장한다.

### 수정 내용
- artifact 집계 조회 추가
- latest backend/model trace 포함
- queue status, timestamps 포함
- step 별 artifact 개수 포함

### 검증 기준
- run detail 화면에서 추가 API 호출 없이 핵심 상태를 표시 가능

---

## 5.14 `runtime/manager-orchestrator/backend/app/services/seed.py`

### 현재 문제
- agent YAML 정보를 그대로 DB에 넣는다.
- router 구조 전환 시 legacy direct endpoint 값이 남을 수 있다.

### 수정 목표
seed 단계에서 router 기반 정책을 강제한다.

### 수정 내용
- `transport=router` 기본값 주입
- `endpoint` 는 router base url 로 표준화
- `router_role` 필드 세팅
- local 개발에서만 legacy direct endpoint 허용

### 검증 기준
- seed 후 모든 agent row 가 router 기준 값으로 정규화됨

---

## 5.15 `runtime/manager-orchestrator/config/agents.yaml`

### 현재 문제
- agent 마다 direct vLLM endpoint 를 바라본다.
- linux host 에서 `host.docker.internal` 의존성이 있다.

### 수정 목표
모든 agent 를 router 하나로 수렴한다.

### 변경 예시
```yaml
version: 2
agents:
  - code: architect
    name: Architect Agent
    role: architect
    transport: router
    endpoint: http://router:8080/v1
    model: router-auto
    adapter: architect-lora
    router_role: architect
    prompt_key: architect
    active: true
```

### 검증 기준
- `host.docker.internal` 제거
- compose 내부 네트워크 기준으로 동작

---

## 5.16 `runtime/manager-orchestrator/docker-compose.yml`

### 현재 문제
- postgres healthcheck 없음
- backend 가 postgres 준비 전에 올라올 수 있다.
- router service 가 포함되어 있지 않다.

### 수정 목표
local 통합 실행 기준 compose 로 재구성한다.

### 수정 내용
1. postgres healthcheck 추가
2. backend `depends_on: condition: service_healthy` 적용
3. router service 추가 또는 외부 router URL env 주입
4. 가능하면 `backend-worker` 분리

### 권장 서비스 구성
- `postgres`
- `backend-api`
- `backend-worker`
- `frontend`
- `router` (선택: same compose 또는 external)

### 검증 기준
- `docker compose up` 시 백엔드가 DB 준비 후 안정 기동
- 백엔드/워커가 같은 코드베이스로 분리 동작

---

## 5.17 `runtime/manager-orchestrator/db/init/001_schema.sql`

### 현재 문제
- 모델 확장 사항을 반영하지 못한다.
- create_all 과 동시 사용 시 drift 가능성이 높다.

### 수정 목표
현재 SQL init 을 유지할 경우 이번 설계 필드를 반영한다.

### 수정 포인트
- `orchestration_run` 에 `execution_mode`, `queue_status`, `started_at`, `finished_at`, `last_error`, `metadata`
- `orchestration_step` 에 `retry_count`, `max_retry_count`, `backend_name`, `target_model`, `schema_valid`, `execution_ms`
- `artifact` 에 `storage_type`, `path`, `content_type`, `summary`
- `orchestration_event` 에 `event_type`, `trace_id`, `request_id`

### 권장 보완
이번 단계 끝나면 SQL init 기반에서 Alembic 기반으로 넘어간다.

---

## 5.18 `runtime/manager-orchestrator/backend/app/tests/test_pipeline.py`

### 현재 문제
- 파이프라인 순서만 검증한다.

### 수정 목표
최소 회귀 테스트 세트를 1차 확장한다.

### 분리 권장
기존 파일 유지 + 아래 신규 테스트 파일 추가

- `test_llm_client_router_payload.py`
- `test_llm_client_json_parse.py`
- `test_orchestrator_step_retry.py`
- `test_run_enqueue_api.py`
- `test_router_integration_mock.py`

### 검증 포인트
- 요청 body 에 `extra_body.agent_role` 포함 여부
- code fence JSON 파싱 여부
- failed step retry count 증가 여부
- enqueue API 202 반환 여부

---

## 5.19 `runtime/manager-orchestrator/frontend/src/types.ts`

### 현재 문제
- run/step 타입이 동기 실행 기준이다.

### 수정 목표
queue 상태와 trace 필드를 수용한다.

### 추가 타입
- `queue_status`
- `started_at`, `finished_at`
- `backend_name`, `target_model`, `schema_valid`, `execution_ms`
- `artifacts`

### 검증 기준
- 프론트에서 타입 오류 없이 신규 필드 표시 가능

---

## 5.20 `runtime/manager-orchestrator/frontend/src/api/client.ts`

### 현재 문제
- 단발성 조회 위주
- enqueue/cancel/resume/step retry API 없음

### 수정 목표
비동기 실행용 API client 추가

### 추가 함수
- `enqueueRun(runId)`
- `cancelRun(runId)`
- `resumeRun(runId)`
- `retryStep(runId, stepId)`
- `listArtifacts(runId)`

### 선택 보완
- `pollRun(runId, intervalMs)` helper

---

## 5.21 `runtime/manager-orchestrator/frontend/src/pages/RunDetailPage.tsx`

### 현재 문제
- 실시간 상태 갱신이 없다.
- router trace, artifact, failed step action 버튼이 없다.

### 수정 목표
운영자가 실행 흐름과 실패 원인을 즉시 파악할 수 있게 한다.

### 수정 내용
- run status badge / queue badge 추가
- 3~5초 polling 추가
- step 행에 `backend_name`, `target_model`, `schema_valid`, `retry_count` 표시
- failed step 에 `retry` 버튼 노출
- artifact 목록 탭 추가

### 검증 기준
- 실행 중 화면 갱신
- step retry 버튼 동작

---

## 5.22 `runtime/work_proxy_deploy/router_service/app/config.py`

### 현재 문제
- config 형식 검증은 있으나 `request_role_fields`, `max_retries` 활용 검증이 약하다.

### 수정 목표
router 설정 오류를 startup 시 더 빨리 잡는다.

### 수정 내용
- `request_role_fields` 가 비어 있으면 에러
- backend 마다 `base_url`, `timeout_seconds`, `max_retries` 타입 검증
- route 마다 `target_model` 누락 시 경고/에러 정책 명시

### 검증 기준
- 설정 파일 오타를 startup 단계에서 발견 가능

---

## 5.23 `runtime/work_proxy_deploy/router_service/app/main.py`

### 현재 문제
- backend `max_retries` 설정을 실제 사용하지 않는다.
- top-level `agent_role` 은 읽지 않는다.
- trace 정보 전달이 최소 수준이다.

### 수정 목표
라우터를 운영형에 맞게 보강한다.

### 필수 수정 내용
1. `get_role()` 가 아래 순서로 role 탐색
   - `agent_role`
   - `extra_body.agent_role`
   - `metadata.agent_role`
   - header `x-agent-role`

2. `try_non_stream()` / `try_stream()` 에 backend 자체 재시도 루프 반영

3. request/response trace header 추가
   - `x-router-role`
   - `x-router-backend`
   - `x-router-model`

4. 실패 응답 표준화
```json
{
  "error": {
    "message": "all backends failed",
    "role": "architect",
    "errors": [...]
  }
}
```

### 선택 보완
- `/router/routes` 외에 `/router/decision?role=architect` 추가
- dry-run mode 지원

### 검증 기준
- 동일 backend 내 재시도 정상 작동
- top-level / extra_body / header 방식 모두 role 인식 가능

---

## 5.24 `runtime/work_proxy_deploy/configs/vllm_request_router.local.yaml`

### 현재 문제
- `request_role_fields` 에 top-level `agent_role` 이 없다.
- 재시도 횟수는 정의되어 있으나 main.py 가 사용하지 않는다.

### 수정 목표
클라이언트 다양성에 강한 설정으로 바꾼다.

### 수정 내용
```yaml
request_role_fields:
  - agent_role
  - extra_body.agent_role
  - extra_body.role
  - metadata.agent_role
  - metadata.role
```

추가 권장 필드
```yaml
router:
  trace_response_headers: true
  emit_router_metadata: true
```

### 검증 기준
- orchestrator 가 어떤 방식으로 role 을 보내더라도 라우팅 성공

---

## 5.25 `runtime/work_proxy_deploy/docker-compose.integrated.yml`

### 현재 문제
- router 는 잘 구성돼 있으나 orchestrator 와 직접 묶여 있지 않다.
- 운영 시 network 경계와 API endpoint 표준을 문서화할 필요가 있다.

### 수정 목표
통합 실행 기준을 명확히 한다.

### 수정 내용
- 선택지 A: router stack 과 orchestrator stack 을 하나의 compose project 로 합침
- 선택지 B: 현재 구조 유지 + orchestrator 에 `ROUTER_BASE_URL=http://router:8080/v1` 주입

### 권장안
초기에는 **B안**이 낫다.
이유:
- 역할 분리가 명확함
- 추론면과 제어면을 따로 재시작 가능
- GPU stack 과 app stack 을 분리 운영 가능

### 검증 기준
- orchestrator compose 와 router compose 를 같은 network 에 붙여 상호 통신 가능

---

# 6. 신규 생성 파일 설계

## 6.1 `backend/app/services/schema_validator.py`

### 목적
역할별 output 을 저장 전에 검증

### 최소 기능
- `validate(role: str, payload: dict) -> tuple[bool, list[str]]`
- schema path 매핑
- 검증 실패 메시지 정규화

### 연결 지점
- `orchestrator.py` step 완료 직전

---

## 6.2 `backend/app/services/job_queue.py`

### 목적
API 요청과 step 실행을 분리

### 최소 기능
- enqueue run
- reserve next pending run
- mark running/completed/failed

### 초기 구현 권장
- DB polling 기반 단순 구현
- 추후 Redis/RQ/Celery 로 교체 가능하게 추상화

---

## 6.3 `backend/app/workers/run_worker.py`

### 목적
background 모드에서 run 실행

### 최소 기능
- pending run poll
- orchestrator execute
- timeout/retry 처리

---

## 6.4 `backend/app/services/rag_service.py`

### 목적
프로젝트 문서/이전 artifact 를 검색하여 step context 에 주입

### 최소 기능
- `retrieve(project_id, role, query, top_k)`
- return: chunk list, source metadata

### 초기 단계
- artifact / project 문서 기반 mock retrieval 만 구현

---

## 6.5 `backend/app/services/tool_runner.py`

### 목적
build / test / lint / scan 실행용 공통 인터페이스 제공

### 최소 기능
- `run_build(...)`
- `run_test(...)`
- `run_lint(...)`
- `run_scan(...)`

### 초기 단계
- 실제 실행 대신 stub report 생성 가능

---

## 6.6 `backend/app/api/routes/artifacts.py`

### 목적
artifact 조회 endpoint 분리

### 최소 기능
- run artifact 목록
- step artifact 목록
- artifact 상세 조회

---

## 6.7 `backend/app/tests/test_schema_validator.py`
## 6.8 `backend/app/tests/test_worker_flow.py`
## 6.9 `backend/app/tests/test_router_headers.py`

### 목적
이번 단계에서 가장 깨지기 쉬운 영역을 선제 검증

---

# 7. 실제 적용 순서와 작업 묶음

## 작업 묶음 A: Router 연결 최소화
대상 파일:
- `backend/app/core/config.py`
- `backend/app/services/llm_client.py`
- `config/agents.yaml`
- `router_service/app/main.py`
- `configs/vllm_request_router.local.yaml`

완료 조건:
- orchestrator 가 router 를 통해 pm/architect/dev-* 호출 성공
- `x-router-backend`, `x-router-model` 이 step 에 저장됨

---

## 작업 묶음 B: DB/상태 모델 정리
대상 파일:
- `backend/app/models/*.py`
- `backend/app/schemas/run.py`
- `db/init/001_schema.sql`
- `backend/app/services/run_reader.py`

완료 조건:
- queue 상태, retry, backend trace 가 저장/조회됨

---

## 작업 묶음 C: 비동기 실행 구조
대상 파일:
- `backend/app/api/routes/runs.py`
- `backend/app/services/orchestrator.py`
- `backend/app/services/job_queue.py` 신규
- `backend/app/workers/run_worker.py` 신규
- `docker-compose.yml`

완료 조건:
- `POST /runs/{id}/execute` 가 202 반환
- worker 가 별도 step 실행 수행

---

## 작업 묶음 D: schema/RAG/tool 확장점
대상 파일:
- `backend/app/services/schema_validator.py` 신규
- `backend/app/services/rag_service.py` 신규
- `backend/app/services/tool_runner.py` 신규
- `backend/app/services/prompts.py`
- `backend/app/services/orchestrator.py`

완료 조건:
- role별 output schema 검증 적용
- mock RAG / mock tool runner 연결 성공

---

## 작업 묶음 E: 프론트 운영 화면 보완
대상 파일:
- `frontend/src/types.ts`
- `frontend/src/api/client.ts`
- `frontend/src/pages/RunDetailPage.tsx`
- 필요 시 `frontend/src/components/RunTimeline.tsx`

완료 조건:
- queue 상태/trace/artifact/retry UI 제공

---

# 8. 산출물 기준 완료 정의

## 8.1 P0 완료 기준
- direct backend 주소 제거
- router 단일 endpoint 사용
- `agent_role` 전달 성공
- postgres 전용 기동 성공
- JSON 파싱 오류 감소

## 8.2 P1 완료 기준
- execute API 가 background enqueue 방식으로 전환
- step retry 가능
- schema validation 적용
- router retry 반영

## 8.3 P2 완료 기준
- RAG/service/tool hook 삽입
- artifact/event 추적 강화
- 프론트 상태 자동 갱신

---

# 9. 권장 다음 실행 순서

이 설계서를 기준으로 실제 구현은 아래 순서가 가장 안전하다.

### Step 1
**Router 연동 수정본 구현**
- `llm_client.py`
- `agents.yaml`
- `router main/config/yaml`

### Step 2
**DB/모델/스키마 수정본 구현**
- run/step/event/artifact 모델 확장
- SQL init 동기화

### Step 3
**비동기 run 실행 구조 구현**
- enqueue API
- worker
- retry/cancel/resume

### Step 4
**schema validator + mock RAG + mock tool runner 구현**

### Step 5
**프론트 보완**
- 실시간 상태 반영
- artifact/retry UI

---

# 10. 최종 결론

이번 런타임 안정화의 핵심은 단순히 코드 정리가 아니라, 현재의 POC 구조를 **실제 운영 가능한 제어면(control plane) + 추론면(inference plane) 구조**로 바꾸는 것이다.

가장 먼저 손볼 핵심 파일은 다음 8개다.

1. `runtime/manager-orchestrator/backend/app/services/llm_client.py`
2. `runtime/manager-orchestrator/backend/app/services/orchestrator.py`
3. `runtime/manager-orchestrator/backend/app/core/config.py`
4. `runtime/manager-orchestrator/backend/app/api/routes/runs.py`
5. `runtime/manager-orchestrator/config/agents.yaml`
6. `runtime/work_proxy_deploy/router_service/app/main.py`
7. `runtime/work_proxy_deploy/configs/vllm_request_router.local.yaml`
8. `runtime/manager-orchestrator/docker-compose.yml`

이 8개를 먼저 정리하면, 이후 RAG / build runner / test runner / scan runner 는 현재 구조 위에 자연스럽게 증설할 수 있다.

