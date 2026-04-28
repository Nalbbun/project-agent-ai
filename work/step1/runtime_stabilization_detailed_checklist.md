# 런타임 안정화 상세 점검서

작성일: 2026-04-15  
대상 소스: `ai_managerr_fullstack_startpack.zip` 내 `runtime/` 전체  
중점 범위:
- `runtime/manager-orchestrator`
- `runtime/work_proxy_deploy`

---

## 1. 문서 목적

본 문서는 업로드된 전체 소스 중 **운영 런타임 영역**을 기준으로,
현재 구조가 어디까지 구현되어 있는지, 실제 운영 단계로 가기 전에 무엇을 어떤 순서로 안정화해야 하는지,
그리고 각 항목의 **위험도 / 원인 / 영향 / 조치안 / 검증 기준**을 정리한 상세 점검서이다.

이 점검서는 다음 단계 작업의 기준 문서로 사용한다.

1. 즉시 수정이 필요한 항목 확정
2. vLLM 라우터 연동 방식 확정
3. RAG / Build Runner / Test Runner / Scan Runner 연결 순서 확정
4. 운영 배포용 백로그 도출

---

## 2. 점검 범위 요약

### 2.1 `runtime/manager-orchestrator`
역할:
- 프로젝트 / 실행(run) 생성
- 단계(step) 생성 및 실행
- 에이전트 호출
- 이벤트 / 산출물 저장
- 프론트 운영 콘솔 제공

주요 파일:
- `backend/app/services/orchestrator.py`
- `backend/app/services/llm_client.py`
- `backend/app/core/config.py`
- `backend/app/models/*.py`
- `config/agents.yaml`
- `docker-compose.yml`
- `db/init/001_schema.sql`

### 2.2 `runtime/work_proxy_deploy`
역할:
- vLLM 다중 백엔드 실행
- 역할별 모델/LoRA 라우팅
- fallback 라우팅
- Ollama 등록 보조 스크립트 제공

주요 파일:
- `router_service/app/main.py`
- `router_service/app/config.py`
- `configs/vllm_request_router.local.yaml`
- `docker-compose.integrated.yml`

---

## 3. 현재 런타임 구조 진단 결론

현재 런타임은 다음 두 층으로 나뉜다.

### 3.1 제어면(Control Plane)
`manager-orchestrator`
- run 생성
- step 생성
- agent 호출 순서 제어
- 결과 저장
- 운영 UI 제공

### 3.2 추론면(Inference Plane)
`work_proxy_deploy`
- 역할별 모델 라우팅
- vLLM general / coder / exaone 분리
- LoRA target model 명시
- fallback 경로 보유

### 3.3 현재 상태 한 줄 요약

**구조는 맞지만, 두 런타임이 아직 완전히 연결되어 있지 않다.**

특히 아래가 핵심이다.
- `manager-orchestrator` 는 아직 **router service 전제 호출 방식이 아님**
- `adapter` 는 현재 실제 라우팅 파라미터가 아니라 **system prompt 힌트 수준**
- `RAG / build runner / test runner / security scan` 은 아직 런타임 실행 체인에 붙지 않음
- 실행 방식이 동기식이라 장시간 작업에서 운영 안정성이 낮음

---

## 4. 우선순위 기준

본 문서의 우선순위는 아래 기준으로 구분한다.

- **P0**: 지금 상태로 운영 연결 시 높은 확률로 장애 또는 오동작 발생
- **P1**: 운영 연결은 가능하지만 품질/확장성/회복성이 부족
- **P2**: 기능은 되지만 실무 운영 품질을 위해 보완 필요
- **P3**: 고도화/최적화 단계

---

## 5. 핵심 점검 결과 요약표

| 우선순위 | 항목 | 현재 상태 | 결론 |
|---|---|---|---|
| P0 | Router 실제 연동 부재 | `manager-orchestrator`가 backend 직접 호출 | 실제 vLLM 라우팅 체계와 미연결 |
| P0 | LoRA 선택 전달 방식 부재 | `llm_client.py` 에서 prompt 힌트만 사용 | adapter 실선택 아님 |
| P0 | Router 사용 시 `agent_role` 미전달 | router는 role 필수, 현재 클라이언트는 미전달 | 연결 즉시 400 위험 |
| P0 | DB 기본값 sqlite vs JSONB 모델 | 설정 기본 sqlite, 모델은 JSONB 사용 | 기본 실행 경로 충돌 위험 |
| P0 | Linux 배포 호환성 | `host.docker.internal` 사용 | 리눅스 Docker 환경에서 실패 가능 |
| P0 | 장시간 실행 동기식 | `/execute` 에서 전체 step 동기 수행 | timeout / 중단 / 복구 취약 |
| P1 | 응답 JSON 파싱 취약 | `json.loads(content)` 단일 처리 | 코드블록/불완전 JSON에 취약 |
| P1 | Schema 검증 부재 | step 결과 바로 저장 | 잘못된 구조 저장 가능 |
| P1 | Retry 정책 단순 | 전체 reset 후 재실행 | 부분 재실행 불가 |
| P1 | Router의 `max_retries` 미활용 | config 존재하나 코드 반영 없음 | 설정 대비 실제 동작 불일치 |
| P1 | Postgres 준비 상태 보장 약함 | compose `depends_on`만 사용 | 초기 기동 race 가능 |
| P1 | 마이그레이션 체계 혼재 | SQL init + `create_all()` 동시 사용 | 스키마 drift 위험 |
| P2 | Auth/RBAC 부재 | 운영 콘솔 무인증 | 내부망 외 사용 불가 |
| P2 | RAG 미연결 | context는 step output만 수집 | 프로젝트 문서 활용 불가 |
| P2 | Tool runner 미연결 | QA/SecOps가 설명형 결과 중심 | 실행 검증 자동화 미흡 |
| P2 | 프론트 실시간 상태 미지원 | polling/websocket 없음 | 긴 작업 관찰성 부족 |
| P2 | 테스트 부족 | 파이프라인 순서 단일 테스트 수준 | 회귀 안정성 낮음 |
| P3 | 병렬 실행 미지원 | dev-fe/dev-be/dev-db 순차 수행 | 처리량/속도 비효율 |
| P3 | Prompt/context 비대화 대응 부족 | 전체 prior payload 누적 | 긴 run에서 prompt 팽창 |

---

## 6. 상세 점검 항목

## 6.1 P0-1. Manager-Orchestrator와 Router Service가 실제로 연결되어 있지 않음

### 관찰 근거
- `runtime/manager-orchestrator/config/agents.yaml`
  - agent endpoint가 각각 `http://host.docker.internal:8000/v1`, `8001/v1`, `8002/v1` 로 직접 설정됨
- `runtime/work_proxy_deploy/router_service/app/main.py`
  - `/v1/chat/completions` 를 통해 역할 기반 라우팅 제공

### 문제 원인
현재 제어면은 역할별 agent를 **직접 vLLM 백엔드로 호출**하고 있다.  
즉, 이미 별도로 구현된 router service를 사용하지 않는다.

### 영향
- fallback 경로를 실제로 못 씀
- 역할 기반 통합 라우팅을 못 씀
- backend 교체 시 `agents.yaml` 전부 수정해야 함
- 운영 표준 endpoint 단일화가 안 됨

### 조치안
1. `manager-orchestrator` 의 모든 agent endpoint를 router 하나로 통합
2. `model` 은 `router-auto` 또는 role별 target model 정책으로 정리
3. 실제 role 전달은 request body 또는 header 기반으로 명시

### 권장 목표 구조
- orchestrator → router (`/v1/chat/completions`)
- router → vllm-general / vllm-coder / vllm-exaone

### 검증 기준
- orchestrator 설정에서 개별 backend 주소 제거
- router `/router/routes` 기준으로 role 매핑 확인
- 실제 호출 응답 header `x-router-backend`, `x-router-model` 확인

---

## 6.2 P0-2. Router 연동 시 `agent_role` 이 누락되어 즉시 실패할 가능성

### 관찰 근거
- `runtime/work_proxy_deploy/router_service/app/main.py`
  - `handle_proxy()` 에서 role 없으면 400 반환
  - `missing_role_message`: `agent_role is required`
- `runtime/manager-orchestrator/backend/app/services/llm_client.py`
  - 요청 payload에 `agent_role`, `metadata.agent_role`, `extra_body.agent_role` 없음
  - header `x-agent-role` 도 없음

### 문제 원인
router는 role을 기반으로 route를 선택한다.  
그런데 orchestrator는 현재 direct backend 구조를 전제로 구현되어 있어, router에 필요한 식별 필드를 넣지 않는다.

### 영향
- endpoint만 router로 바꾸면 바로 400 오류 가능
- 운영 전환 시 “왜 라우팅이 안 되는지” 찾기 어려움

### 조치안
`llm_client.py` 요청 payload를 다음 형태 중 하나로 수정한다.

#### 권장안 A
```json
{
  "model": "router-auto",
  "messages": [...],
  "agent_role": "architect"
}
```

#### 권장안 B
```json
{
  "model": "router-auto",
  "messages": [...],
  "metadata": {
    "agent_role": "architect"
  }
}
```

#### 권장안 C
- HTTP header: `x-agent-role: architect`

### 검증 기준
- router 뒤로 연결했을 때 pm / architect / dev-fe / dev-be / dev-db / qa / secops / manager 모두 정상 호출
- role 누락 시 의도한 400 발생

---

## 6.3 P0-3. Adapter는 현재 실제 LoRA 선택값이 아니라 prompt 힌트 수준

### 관찰 근거
- `runtime/manager-orchestrator/backend/app/services/llm_client.py`
  - system message: `Use adapter={agent.adapter or ''}. Always respond in JSON.`
- `runtime/work_proxy_deploy/configs/vllm_request_router.local.yaml`
  - role별 `target_model` 명시 (`pm-lora`, `architect-lora`, `dev-fe-lora` 등)
- `runtime/work_proxy_deploy/docker-compose.integrated.yml`
  - vLLM 실행 시 `--enable-lora`, `--lora-modules` 사용

### 문제 원인
현재 orchestrator는 adapter를 실제 request 파라미터로 사용하지 않는다.  
단지 모델에게 “이 adapter를 써라”라고 말로 지시하는 구조다.

### 영향
- 실제 LoRA가 적용된다는 보장이 없음
- 응답 품질 편차가 큼
- base model 응답과 adapter 응답이 섞일 수 있음

### 조치안
1. direct backend 구조를 유지할 경우:
   - `model` 에 실제 served-model-name 또는 adapter target model 규칙 적용
2. router 구조로 전환할 경우:
   - orchestrator는 role만 전달
   - router가 `target_model` 을 강제 주입

### 권장 결론
LoRA 선택 책임은 orchestrator가 아니라 **router** 로 넘기는 것이 맞다.

### 검증 기준
- 동일 프롬프트에 대해 route별 adapter가 일관되게 선택됨
- router response header에서 target model 확인 가능

---

## 6.4 P0-4. DB 기본 설정과 모델 정의가 충돌할 수 있음

### 관찰 근거
- `runtime/manager-orchestrator/backend/app/core/config.py`
  - 기본값: `database_url = "sqlite:///./local.db"`
- `runtime/manager-orchestrator/backend/app/models/run.py`
- `runtime/manager-orchestrator/backend/app/models/event.py`
- `runtime/manager-orchestrator/backend/app/models/artifact.py`
  - `JSONB` 사용

### 문제 원인
기본 설정은 sqlite인데, 모델은 PostgreSQL 전용 `JSONB` 컬럼을 사용한다.

### 영향
- `.env` 누락 또는 로컬 기본 실행 시 테이블 생성 실패 가능
- 환경에 따라 “어떤 곳은 되고 어떤 곳은 안 되는” 상태 발생

### 조치안
둘 중 하나로 정리한다.

#### 권장안
- 기본 DB도 PostgreSQL 기준으로 통일
- sqlite fallback 제거

#### 대안
- dialect 분기 처리
- sqlite에서는 JSON 타입 사용, postgres에서는 JSONB 사용

### 검증 기준
- `.env` 없이도 실패 원인이 명확해야 함
- 개발/운영 DB 전략 문서화

---

## 6.5 P0-5. `host.docker.internal` 의존으로 Linux Docker 배포 호환성이 낮음

### 관찰 근거
- `runtime/manager-orchestrator/config/agents.yaml`
  - endpoint가 `http://host.docker.internal:*` 로 지정

### 문제 원인
`host.docker.internal` 은 환경에 따라 동작 보장이 다르며, Linux Docker에서는 별도 설정 없으면 실패할 수 있다.

### 영향
- Linux 서버에서 backend 컨테이너가 LLM endpoint 연결 실패 가능
- 개발 PC에서는 되고 서버에서는 안 되는 배포 장애 발생

### 조치안
1. 동일 compose network 안에서 service name 통신으로 전환
2. 또는 router 단일 endpoint만 바라보게 변경
3. 정말 host 통신이 필요하면 `extra_hosts` 등 명시 설정

### 권장 목표
- backend → `http://router:8080/v1`
- router → 내부 service name 기반 통신

### 검증 기준
- Linux Docker / WSL2 / 단일 서버 환경 모두 동일 설정으로 동작

---

## 6.6 P0-6. 전체 step 실행이 동기식이라 장시간 작업에서 불안정

### 관찰 근거
- `runtime/manager-orchestrator/backend/app/services/orchestrator.py`
  - `execute_run()` 에서 모든 step을 for-loop로 동기 실행
- `runtime/manager-orchestrator/backend/app/api/routes/runs.py`
  - `/runs/{run_id}/execute` 호출 시 즉시 전체 실행

### 문제 원인
요청-응답 한 번으로 전체 파이프라인을 완료하려고 한다.

### 영향
- 긴 응답에서 API timeout 위험
- 네트워크 끊김 시 사용자가 실행 상태를 잃음
- cancel/resume가 어려움
- step별 worker 분리 불가

### 조치안
#### 1차 안정화
- run execute는 job enqueue만 수행
- worker가 step별 실행
- 상태는 DB에 반영

#### 2차 고도화
- Celery / RQ / Dramatiq / Kafka consumer / Spring Batch 등 도입
- step timeout / retry / dead-letter 분리

### 검증 기준
- 긴 run에서도 API 응답은 즉시 반환
- 프론트는 상태 polling 또는 websocket으로 추적
- step 실패 시 다음 step 진행 차단 가능

---

## 6.7 P1-1. 응답 JSON 파싱이 취약함

### 관찰 근거
- `runtime/manager-orchestrator/backend/app/services/llm_client.py`
  - `content = data["choices"][0]["message"]["content"]`
  - `return json.loads(content)`

### 문제 원인
모델 응답이 항상 순수 JSON 문자열이라고 가정한다.

### 영향
- 모델이 markdown code fence 를 감싸면 실패
- trailing text, 설명 문장, JSON 불완전 출력 시 실패
- 동일 모델이라도 temperature/route에 따라 간헐적 장애 발생

### 조치안
1. JSON extractor 추가
   - code fence 제거
   - 첫 `{` ~ 마지막 `}` 추출
2. strict parse 실패 시 repair parser 적용
3. 최종적으로 schema validation 적용

### 검증 기준
- JSON code block 응답도 정상 파싱
- 경미한 포맷 흔들림에서 복구 가능

---

## 6.8 P1-2. 역할별 output schema 검증이 없음

### 관찰 근거
- `orchestrator.py` 에서 `payload = self.client.invoke(...)` 후 바로 `step.output_payload = payload`
- 역할별 schema 파일은 `learning/schemas/` 에 분리되어 있으나 runtime에 연결되어 있지 않음

### 문제 원인
학습 영역과 운영 영역이 분리된 장점은 있으나, runtime validation layer가 아직 없다.

### 영향
- 필수 필드 누락 데이터를 저장할 수 있음
- downstream step가 예상 필드를 찾다가 실패할 수 있음
- 품질 모니터링 지표 산출이 어려움

### 조치안
1. runtime에 role→schema 매핑 테이블 추가
2. step 완료 전 schema validate
3. 실패 시 `failed_validation` 상태로 저장하고 retry 가능하게 처리

### 검증 기준
- pm은 `functional_requirements`, `questions` 등 필드 검증
- architect는 `components`, `apis`, `database` 등 검증
- dev/qa/secops/manager 모두 역할별 필수 필드 검증

---

## 6.9 P1-3. Retry가 전체 초기화 방식이라 실무 운영에 비효율적

### 관찰 근거
- `orchestrator.py` 의 `reset_and_retry()`
  - 모든 step을 pending으로 초기화
  - 전체 다시 실행

### 문제 원인
부분 재실행, 특정 step부터 재실행, 실패 step만 재시도 개념이 아직 없다.

### 영향
- dev-be만 실패해도 pm/architect/qa/secops까지 다시 수행
- 비용 증가
- 동일 입력 재호출로 결과 일관성 저하 가능

### 조치안
1. retry scope 추가
   - current step only
   - from this step onward
   - full reset
2. step별 retry_count 관리
3. 실패 유형별 재시도 정책 분리

### 검증 기준
- 특정 step 실패 시 그 step부터 재실행 가능
- 성공 step 산출물은 보존 가능

---

## 6.10 P1-4. Router config의 `max_retries` 는 정의되어 있으나 코드에서 미사용

### 관찰 근거
- `runtime/work_proxy_deploy/configs/vllm_request_router.local.yaml`
  - backend마다 `max_retries` 정의
- `runtime/work_proxy_deploy/router_service/app/main.py`
  - 후보 백엔드 순회는 있으나 backend별 retry loop 없음

### 문제 원인
config 설계는 되어 있으나 실제 코드 반영이 미완성이다.

### 영향
- 운영자가 기대한 retry 정책이 실제로 동작하지 않음
- 일시적인 네트워크 오류를 그대로 실패로 처리

### 조치안
1. backend별 retry loop 구현
2. 재시도 대상 예외 명확화
3. exponential backoff 추가
4. fallback과 retry 순서를 분리 정의

### 검증 기준
- connect timeout 1회 시 동일 backend 재시도 후 fallback 전환
- retry 횟수 로그에 남김

---

## 6.11 P1-5. Postgres 준비 완료 보장이 약함

### 관찰 근거
- `runtime/manager-orchestrator/docker-compose.yml`
  - backend는 postgres에 `depends_on` 만 사용
  - postgres healthcheck 없음
- `backend/app/main.py`
  - startup에서 `create_db_and_tables()`, `seed_agents_from_yaml()` 즉시 수행

### 문제 원인
컨테이너 시작 순서만 보장하고 DB ready 상태는 보장하지 않는다.

### 영향
- 초기 기동 race condition 가능
- 간헐적인 DB connection 실패 가능

### 조치안
1. postgres healthcheck 추가
2. backend는 `condition: service_healthy` 사용
3. backend startup retry 또는 wait-for-db 추가

### 검증 기준
- cold start 반복 시에도 초기화 실패 없음

---

## 6.12 P1-6. 스키마 관리 방식이 이원화되어 drift 위험 존재

### 관찰 근거
- `db/init/001_schema.sql` 존재
- `backend/app/db/session.py` 의 `create_db_and_tables()` 에서 `SQLModel.metadata.create_all(engine)` 수행

### 문제 원인
초기 SQL과 ORM auto create가 동시에 존재한다.

### 영향
- 스키마 변경 시 어느 쪽이 기준인지 불명확
- 로컬/운영 간 테이블 상태 차이 가능

### 조치안
권장 순서는 다음과 같다.

1. 운영 기준: Alembic/Flyway 등 명시적 migration 체계 채택
2. `create_all()` 은 개발 편의용으로만 제한하거나 제거
3. schema source of truth 를 하나로 통일

### 검증 기준
- 모든 환경에서 같은 migration history 재현 가능

---

## 6.13 P2-1. Auth / RBAC 부재

### 관찰 근거
- FastAPI routes에 인증 의존성 없음
- 프론트도 로그인 화면/토큰 처리 구조 없음

### 영향
- 운영 콘솔 외부 노출 불가
- 프로젝트별 접근 통제 불가
- 실행 이력과 산출물 보안 취약

### 조치안
1. 관리자 인증 우선
2. 이후 RBAC 확장
   - Admin
   - Operator
   - Reviewer
   - Readonly

### 검증 기준
- 인증 없이 run 생성/실행 불가
- 프로젝트별 조회 제어 가능

---

## 6.14 P2-2. RAG 미연결

### 관찰 근거
- `orchestrator.py` 의 `_collect_context()` 는 오직 이전 step output만 수집
- vector store / retriever / document ingest 관련 runtime 코드 없음

### 영향
- 프로젝트 문서, 기존 코드, 보안 정책, 아키텍처 표준을 step에 주입할 수 없음
- 실제 실무 품질이 prompt chaining 수준에 머무름

### 조치안
1. project별 knowledge source 테이블 추가
2. ingest worker 추가
3. step 실행 전 role별 retrieval hook 추가
4. retrieved sources 를 prompt/context에 주입

### 검증 기준
- 동일 사용자 요구라도 프로젝트 문서 차이에 따라 결과가 달라짐
- source provenance 저장 가능

---

## 6.15 P2-3. Build/Test/Lint/Type/SAST Runner 미연결

### 관찰 근거
- QA/SecOps는 simulator 및 프롬프트 기반 결과 반환
- runtime 쪽에 tool runner API 없음
- 학습 패키지의 reward 방향은 있으나 운영 체인에는 미반영

### 영향
- QA verdict가 실제 검증 결과가 아니라 서술형 판단에 머무름
- SecOps finding이 정적 점검이 아니라 언어모델 추론 중심이 됨

### 조치안
1. Tool Runner service 분리
   - build
   - test
   - lint
   - type-check
   - secret scan
   - dependency scan
2. qa / secops step는 runner 결과를 입력으로 사용
3. artifact 로 report 저장

### 검증 기준
- run 결과에 실제 junit/sarif/text reports 저장
- qa verdict 가 실행 결과와 일치

---

## 6.16 P2-4. 프론트 실시간 모니터링이 부족함

### 관찰 근거
- 현재 프론트는 기본 목록/상세 구조
- polling/websocket/SSE 코드 없음

### 영향
- 긴 run 수행 시 사용자가 새로고침해야 함
- 상태 추적 경험이 약함

### 조치안
1. 우선 polling 3~5초 추가
2. 이후 websocket/SSE 도입
3. step log incremental view 추가

### 검증 기준
- execute 후 UI가 자동 반영
- step 상태 변화가 순차 표시됨

---

## 6.17 P2-5. 테스트 커버리지가 매우 낮음

### 관찰 근거
- `backend/app/tests/test_pipeline.py` 단일 테스트 수준

### 영향
- 리팩토링 시 회귀 탐지 어려움
- 운영 연결 이후 장애 가능성 높음

### 조치안
필수 테스트 최소 세트:
1. run 생성 API
2. execute API (simulation mode)
3. role별 agent not found 처리
4. JSON parsing error 처리
5. retry 범위 처리
6. router role field 포함 여부
7. DB startup / seed 동작

### 검증 기준
- CI 기준 최소 smoke suite 통과

---

## 6.18 P3-1. Dev 단계 병렬 실행 미지원

### 관찰 근거
- `PIPELINE` 이 dev-fe → dev-be → dev-db 순차 고정

### 영향
- 불필요한 지연
- 구조상 병렬 가능 단계가 직렬 처리됨

### 조치안
1. architect 완료 후 dev-fe/dev-be/dev-db fan-out
2. qa/secops 는 fan-in 이후 실행
3. run graph 모델 확장

### 검증 기준
- independent step 동시 실행 가능

---

## 6.19 P3-2. Context 누적 방식이 장기적으로 prompt 팽창 위험

### 관찰 근거
- `_collect_context()` 에서 이전 step output 전체를 context로 전달

### 영향
- 긴 프로젝트에서 토큰 증가
- 중요 정보와 불필요 정보가 섞임

### 조치안
1. step output summary 저장
2. downstream role별 selective context mapping
3. artifact reference 기반 lazy load

### 검증 기준
- role별 필요한 subset만 prompt에 포함

---

## 7. 즉시 수정 권장안 (1차 안정화 스프린트)

아래 8개는 바로 손보는 것을 권장한다.

### 7.1 설정 및 배포
- [ ] sqlite 기본값 제거, postgres 기준으로 통일
- [ ] `host.docker.internal` 제거
- [ ] orchestrator → router 단일 endpoint 구조로 정리
- [ ] postgres healthcheck + backend readiness 대기 추가

### 7.2 호출 프로토콜
- [ ] `llm_client.py` 에 `agent_role` 전달 추가
- [ ] `model=router-auto` 정책 적용
- [ ] JSON extractor + repair parser 추가
- [ ] step output schema validation 추가

### 7.3 실행 안정성
- [ ] `/execute` 를 비동기 job 시작 방식으로 변경
- [ ] retry scope 분리
- [ ] step timeout / retry_count 저장

### 7.4 품질 확인
- [ ] simulation mode 기반 API 테스트 세트 추가
- [ ] router integration smoke test 추가

---

## 8. 2차 연동 권장안 (운영형 연결)

### 8.1 RAG
- project knowledge source 등록
- chunk/vector 저장
- role별 retrieval policy
- citation/provenance 저장

### 8.2 Tool Runner
- build runner
- test runner
- lint runner
- type-check runner
- secret/dependency scan runner

### 8.3 Auth/RBAC
- 관리자 로그인
- 프로젝트 접근 제어
- 실행 승인 플로우

---

## 9. 권장 작업 순서

### Phase 1. 런타임 연결 바로잡기
1. orchestrator → router 통합
2. `agent_role` 전달
3. postgres 통일
4. Linux-friendly networking 정리

### Phase 2. 안정성 보강
5. JSON parse/validation 보강
6. async execution 구조 전환
7. retry / timeout / error classification 추가
8. 테스트 보강

### Phase 3. 실무 기능 연결
9. RAG 연결
10. Tool runner 연결
11. artifact/report 저장 구조 확장

### Phase 4. 운영 고도화
12. auth/RBAC
13. 실시간 UI
14. 병렬 step 실행
15. observability/log correlation

---

## 10. 다음 단계 권장 산출물

본 점검서 다음에 바로 만드는 것이 좋은 문서는 아래 순서다.

### 1순위
**런타임 안정화 실행 설계서**
- 수정 대상 파일별 변경 포인트
- API payload 변경안
- docker-compose/network 변경안
- DB 설정 통일안

### 2순위
**vLLM Router 연동 상세 설계서**
- orchestrator request 포맷
- role 전달 방식
- router target_model 정책
- fallback / retry 규칙

### 3순위
**RAG + Tool Runner 연계 설계서**
- ingest 흐름
- retrieval 흐름
- build/test/scan orchestration
- artifact/report schema

---

## 11. 최종 결론

현재 소스의 런타임은 방향이 잘 잡혀 있고, 학습 패키지와 운영 패키지 분리도 적절하다.  
다만 운영 진입 전 반드시 먼저 손봐야 할 핵심은 아래 6가지다.

1. **orchestrator 와 router 를 실제로 연결할 것**  
2. **role / adapter 선택을 prompt가 아니라 request 라우팅으로 바꿀 것**  
3. **DB 전략을 postgres 기준으로 통일할 것**  
4. **동기 실행 구조를 비동기 job 구조로 바꿀 것**  
5. **JSON parsing + schema validation 을 추가할 것**  
6. **RAG / Tool runner 는 2차 단계로 붙이되 인터페이스를 먼저 열어둘 것**

즉, 지금 바로 다음 단계는 기능 추가보다 먼저 **런타임 연결과 안정성 기반을 다지는 작업**이 우선이다.
