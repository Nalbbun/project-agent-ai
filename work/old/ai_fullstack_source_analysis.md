# AI Fullstack 전체 소스 분석 보고서

작성일: 2026-04-15  
대상 파일: `ai_fullstack.zip`

---

## 1. 분석 요약

업로드된 전체 소스는 **학습 패키지(`learning/`)와 운영 런타임 패키지(`runtime/`)를 분리한 멀티 에이전트 모노레포**입니다.

핵심 구조는 다음과 같습니다.

- **학습 영역**: 역할별 JSON Schema, 샘플 JSONL, reward 함수, SFT/GRPO 학습 템플릿, vLLM/Ollama 배포 예시
- **운영 영역**: Manager / Orchestrator 기반의 실행 런타임, Agent Registry, 백엔드/프론트엔드/DB, 실행 로그 및 산출물 관리
- **추가 운영 보강 영역**: `runtime/work_proxy_deploy/` 아래에 실제 운영형에 가까운 **vLLM 요청 라우터 설정 및 통합 docker compose** 초안 포함

즉, 이 소스는 단순 예제가 아니라,

> **역할별 AI Agent를 학습시키고, 실제로 오케스트레이션하여 소프트웨어 제작 파이프라인으로 운영하기 위한 전체 스타터 소스**

로 보는 것이 맞습니다.

---

## 2. 실제 디렉토리 구조 요약

압축 파일 기준으로 확인한 상위 구조는 아래와 같습니다.

```text
.
├─ learning/
│  ├─ configs/
│  ├─ data_examples/
│  ├─ rewards/
│  ├─ schemas/
│  ├─ scripts/
│  ├─ serving/
│  └─ train/
├─ runtime/
│  ├─ manager-orchestrator/
│  │  ├─ backend/
│  │  ├─ frontend/
│  │  ├─ db/
│  │  ├─ config/
│  │  ├─ docs/
│  │  └─ docker-compose.yml
│  └─ work_proxy_deploy/
│     ├─ configs/
│     ├─ deployment/
│     ├─ router_service/
│     └─ docker-compose.integrated.yml
└─ README.md
```

이 구조 자체가 설계 의도를 잘 보여줍니다.

- `learning/` = 모델 제작, 학습, 평가, 서빙 준비
- `runtime/manager-orchestrator/` = 실제 Agent 실행과 상태 관리
- `runtime/work_proxy_deploy/` = 실제 vLLM/Ollama 연계 운영 보강

---

## 3. 목표 시스템 해석

이 소스가 겨냥하는 최종 시스템은 다음 흐름입니다.

```text
사용자 요구 입력
→ PM
→ Architect
→ Dev-FE / Dev-BE / Dev-DB
→ QA
→ SecOps
→ Manager 병합
→ 최종 산출물
```

즉,

- PM: 요구사항 구조화
- Architect: 시스템 설계
- Dev-FE/BE/DB: 구현
- QA: 테스트 및 검증
- SecOps: 보안 및 운영 점검
- Manager: 전체 실행 순서 제어, 재질문, 결과 병합

구조입니다.

업로드된 전략 문서에서도 **Manager가 오케스트레이션과 결과 통합을 담당하고, Dev는 FE/BE/DB로 분리 운용하는 방향**을 제시하고 있습니다. 이 점은 현재 소스 구조와 일치합니다. fileciteturn2file0

---

## 4. `learning/` 패키지 분석

### 4.1 역할

이 영역은 **모델 학습과 실험**을 위한 패키지입니다.

주요 포함 내용:

- 역할별 JSON Schema
- 역할별 샘플 JSONL 데이터
- reward 코드
- SFT 템플릿
- GRPO 템플릿
- vLLM / Ollama / k8s 서빙 예시

문서상 의도 역시 **역할별 LoRA + SFT 선행 + 이후 GRPO + Tool Use + RAG** 전략입니다. fileciteturn2file0 fileciteturn2file2

### 4.2 실제 확인된 역할별 데이터

`learning/data_examples/` 아래에는 다음 역할별 샘플이 존재합니다.

- architect
- dev-be
- dev-db
- dev-fe
- manager
- pm
- qa
- secops

각 역할마다 `*.train.sample.jsonl`, `*.valid.sample.jsonl` 이 분리되어 있어,
SFT/평가 실험에 바로 사용할 수 있는 형태입니다.

### 4.3 스키마/검증 구조

다음 구조가 존재합니다.

- `learning/schemas/*.schema.json`
- `learning/data_examples/schemas/*.schema.json`
- `learning/data_examples/scripts/validate_samples.py`
- `learning/train/validate_jsonl.py`

즉,

1. 학습 데이터 스키마 정의
2. 샘플 데이터 검증
3. 학습 전 JSONL 검증

흐름이 이미 준비되어 있습니다.

### 4.4 reward 설계

`learning/rewards/` 아래에 다음이 분리되어 있습니다.

- `common.py`
- `pm.py`
- `architect.py`
- `dev.py`
- `dev_db.py`
- `qa.py`
- `secops.py`
- `manager.py`

이는 문서에서 설명한 **역할별 reward 분리 전략**과 정확히 맞습니다. 특히 Dev/QA부터 자동 평가 가능한 영역을 먼저 강화하라는 방향과 연결됩니다. fileciteturn2file0 fileciteturn2file2

### 4.5 학습/배포 보일러플레이트

다음이 준비되어 있습니다.

- `learning/train/sft_template.py`
- `learning/train/grpo_template.py`
- 역할별 `sft_*.sh`
- `learning/serving/vllm/`
- `learning/serving/ollama/`
- `learning/serving/k8s/`

즉, 학습 설계서 수준이 아니라 **실제 실행을 염두에 둔 초안 패키지**입니다.

### 4.6 learning 영역 평가

강점:

- 역할 분리가 명확함
- 스키마와 샘플이 실제 파일로 존재함
- reward 분리가 되어 있음
- 학습 및 서빙 샘플이 함께 있음

한계:

- 샘플 데이터는 구조 검증용/PoC 성격이 강함
- 실무형 대규모 학습셋으로 가기에는 추가 데이터가 더 필요함
- 실행 환경 경로/설정은 현업 환경에 맞춘 수정이 필요함

---

## 5. `runtime/manager-orchestrator/` 분석

### 5.1 역할

이 영역은 **실제 멀티 에이전트 런타임**입니다.

기술 구성:

- Backend: FastAPI
- Frontend: React + Vite + TypeScript
- DB: PostgreSQL 초기화 스크립트 포함
- 설정: YAML 기반 Agent Registry

### 5.2 핵심 설계 포인트

이 패키지는 다음을 수행합니다.

- 프로젝트 생성
- 실행 Run 생성
- 단계별 Step 생성
- Step 실행 상태 저장
- Event 로그 저장
- Artifact 저장
- 최종 병합 결과 기록

즉, 단순 프롬프트 체이닝이 아니라 **실행 이력과 산출물을 남기는 오케스트레이션 서버**입니다.

### 5.3 실제 백엔드 구조

백엔드 소스 기준 주요 모듈은 아래와 같습니다.

- `app/api/routes/` : API 엔드포인트
- `app/models/` : DB 모델
- `app/schemas/` : 요청/응답 스키마
- `app/services/orchestrator.py` : 핵심 실행 로직
- `app/services/llm_client.py` : 모델 호출
- `app/services/prompts.py` : agent별 프롬프트 템플릿
- `app/services/simulator.py` : 시뮬레이션 응답
- `app/services/seed.py` : agent registry seed

### 5.4 현재 파이프라인 흐름

실행 단계는 코드 구조상 다음 순서로 해석됩니다.

1. manager-plan
2. pm
3. architect
4. dev-fe
5. dev-be
6. dev-db
7. qa
8. secops
9. manager-merge

이 흐름은 문서에서 제시한 **Manager 기반 순서 제어와 역할별 협업 구조**와 일치합니다. fileciteturn2file0

### 5.5 프론트엔드 역할

프론트엔드는 운영 콘솔 성격입니다.

주요 페이지:

- DashboardPage
- AgentsPage
- RunsPage
- RunDetailPage

즉, 운영자가

- 어떤 agent가 있는지 보고
- run을 생성하고
- 현재 단계와 이벤트 로그를 확인하고
- 실행 결과를 추적

할 수 있게 되어 있습니다.

### 5.6 DB 설계 해석

모델 파일 기준 핵심 테이블/엔터티는 다음 성격으로 해석됩니다.

- `project` : 프로젝트 단위 관리
- `agent_catalog` : 역할별 agent 등록 정보
- `orchestration_run` : 1회 실행 단위
- `orchestration_step` : 단계별 상태
- `orchestration_event` : 로그 및 이벤트
- `artifact` : 산출물 메타데이터

이 구조는 이후 확장 시 다음에 유리합니다.

- 재시도 이력 추적
- QA/SecOps 결과 누적 관리
- 산출물 버전 관리
- 감사 로그 및 운영 추적

### 5.7 runtime 영역 평가

강점:

- 역할별 agent 운영 구조가 명확함
- Run / Step / Event / Artifact 저장 개념이 좋음
- 시뮬레이션 모드가 있어 모델 없이도 흐름 검증 가능
- 프론트/백/DB가 이미 연결 가능한 최소 단위를 가짐

한계:

- 현재는 FastAPI 기반 POC 런타임 성격이 강함
- step 실행이 동기형 구조에 가까움
- 실제 LoRA 라우팅과 RAG 주입은 아직 완전 연결 상태로 보기 어려움
- Tool Runner 계층은 아직 별도 연결이 필요함

---

## 6. `runtime/work_proxy_deploy/` 분석

이 부분이 중요합니다.

이 디렉토리는 이전 답변 시점보다 한 단계 더 진전된 흔적이 있습니다.

실제 포함 파일:

- `configs/vllm_request_router.local.yaml`
- `configs/ollama_registration.local.yaml`
- `docker-compose.integrated.yml`
- `router_service/app/main.py`
- `router_service/app/config.py`
- `deployment/README.md`

즉, 단순 Manager 런타임만 있는 것이 아니라,
**실제 vLLM/Ollama 요청 라우터를 별도 서비스로 두는 방향까지 이미 작업이 들어간 상태**입니다.

이 부분은 다음 의미를 가집니다.

1. 역할별 요청을 라우팅하려는 의도가 분명함
2. 운영용 compose 통합 구조를 준비 중임
3. 기존 FastAPI orchestrator와 별도로 inference proxy 계층을 두려는 설계임

즉 현재 전체 소스는,

- 학습
- 오케스트레이션
- 요청 라우팅

세 층을 분리하려는 방향으로 발전 중이라고 보는 것이 맞습니다.

---

## 7. 전체 소스의 강점

### 7.1 구조가 분명함

학습 패키지와 운영 패키지가 분리되어 있어 유지보수성이 좋습니다.

### 7.2 역할 분리가 명확함

PM / Architect / Dev-FE / Dev-BE / Dev-DB / QA / SecOps / Manager 가 패키지 수준에서 분리되어 있습니다.

### 7.3 문서 방향과 실제 코드 방향이 맞음

업로드된 전략 문서에서 제시한

- 역할별 LoRA
- SFT 선행
- 이후 GRPO
- Tool Use + RAG
- Manager 중심 Orchestration

방향이 실제 소스 구조에 반영되어 있습니다. fileciteturn2file0 fileciteturn2file2

### 7.4 운영용 사고방식이 들어가 있음

단순 샘플이 아니라

- run
- step
- event
- artifact

개념이 있어 실제 업무형 시스템으로 확장 가능성이 높습니다.

### 7.5 확장 포인트가 이미 보임

`work_proxy_deploy/` 는 앞으로 붙일

- vLLM request router
- adapter routing
- multi-service deployment

확장의 연결점을 제공합니다.

---

## 8. 현재 소스의 핵심 보완 포인트

### 8.1 실제 운영형 Tool Layer 연결 필요

문서상으로는 Tool Use가 핵심이지만, 현재 런타임 기준으로는 다음 연결이 아직 핵심 과제입니다.

- build runner
- test runner
- lint/type check
- security scan
- artifact packaging

즉, QA와 SecOps가 더 실전적으로 동작하려면 **설명형 응답**이 아니라 **실제 실행/검사 결과 기반**으로 바뀌어야 합니다. 문서에서도 Tool Use가 모델보다 더 중요하다고 정리합니다. fileciteturn2file0

### 8.2 RAG 연결 고도화 필요

전략상 작은 모델은 RAG와 함께 가야 하므로,
런타임에는 다음이 추가되는 것이 맞습니다.

- 프로젝트 문서 ingest
- vector index
- step별 retrieval
- source citation
- run별 context cache

문서에서도 RAG는 필수 요소로 제시되어 있습니다. fileciteturn2file0

### 8.3 실제 adapter routing 명확화 필요

현재 구조는 adapter registry와 router config 방향이 보이지만,
운영 안정성을 위해서는 다음이 명확해야 합니다.

- role → base model → adapter → endpoint 매핑
- fallback model 전략
- timeout / retry / circuit breaker
- adapter 버전 관리

### 8.4 비동기 실행/작업 큐 필요

Run/Step 구조가 이미 있으므로,
다음 단계에서는 동기 호출형보다 **queue + worker 구조**가 더 적합합니다.

예:

- Manager는 step 생성만 수행
- worker가 step별 실행
- frontend는 polling 또는 websocket 구독

### 8.5 인증/권한 필요

운영 콘솔 성격이므로 실제 사용을 위해서는

- 사용자 인증
- 프로젝트 권한
- 관리자/운영자 역할 분리
- 감사 로그

가 필요합니다.

---

## 9. 현재 전체 소스 수준에 대한 판단

이 소스는 다음 단계로 평가할 수 있습니다.

### 현재 수준

**“실무 지향 멀티 에이전트 플랫폼의 전체 스타터”**

### 아직 아닌 것

- 즉시 상용 운영 가능한 완성형 플랫폼
- 완전한 Spring Boot 운영 서버
- 완성된 vLLM multi-LoRA production router
- 완성된 RAG + build runner + security runner 통합형 플랫폼

즉,

> 방향은 매우 좋고, 패키지 분리도 잘 되어 있으며, 다음 단계 개발 우선순위가 선명한 상태

라고 보는 것이 가장 정확합니다.

---

## 10. 다음 단계 우선순위 제안

사용자께서 “순서적으로 필요한 우선순위대로 다음 단계로 간다”고 하셨으므로, 현재 전체 소스 기준 우선순위를 아래처럼 잡는 것이 가장 좋습니다.

### 1순위. 런타임 실행 안정화

가장 먼저 해야 할 일:

- 환경설정 정리
- agent registry와 router 설정 정합성 확인
- step 실행 실패 처리 보강
- schema validation 추가
- run/step 상태 전이 명확화

이 단계는 **현재 소스를 제대로 돌릴 수 있는 상태**를 만드는 단계입니다.

### 2순위. vLLM 요청 라우터 실전화

다음으로 해야 할 일:

- `work_proxy_deploy/router_service` 완성도 점검
- role별 adapter routing 설계 확정
- fallback 모델 정책 추가
- timeout / retry / backoff 추가

이 단계는 **실제 모델 호출을 안정화하는 단계**입니다.

### 3순위. RAG 계층 추가

그 다음:

- 프로젝트 문서 업로드/색인
- retrieval API
- step별 context augmentation
- source citation

이 단계는 **작은 모델의 정확도를 올리는 핵심 단계**입니다. fileciteturn2file0

### 4순위. Tool Runner 연결

그 다음:

- build/test/lint/type check runner
- security scan runner
- artifact packaging
- QA/SecOps 자동 평가 연결

이 단계부터 비로소 **Dev → QA → SecOps 루프가 실무형**이 됩니다.

### 5순위. Spring Boot 전환 또는 병행 설계

마지막으로 선택할 방향:

- 현재 FastAPI 런타임을 Spring Boot로 전환
- 또는 Java 기반 Tool Runner / API Gateway만 Spring으로 분리
- 또는 Orchestrator는 FastAPI 유지, 기업 운영 계층만 Spring Boot 도입

즉, Spring 전환은 중요하지만, **현재 시점에서는 1~4단계 정리가 선행될 때 가장 효과적**입니다.

---

## 11. 권장 진행안

현재 전체 소스를 기준으로 가장 현실적인 진행 순서는 아래입니다.

### 추천 순서

1. **전체 런타임 실행 안정화 점검**
2. **vLLM 요청 라우터 설정/코드 보강**
3. **RAG 추가**
4. **빌드/테스트/보안 Runner 연결**
5. **Spring Boot 전환 또는 병행 아키텍처 결정**

이 순서가 좋은 이유는,

- 먼저 돌아가야 하고
- 그 다음 실제 모델 연결이 되어야 하며
- 그 다음 정확도와 자동 검증을 붙여야 하고
- 마지막에 운영 기술 스택 전환을 해도 늦지 않기 때문입니다.

---

## 12. 결론

업로드된 전체 소스는 단순한 예시가 아니라,

- **학습 패키지**
- **운영 런타임**
- **요청 라우팅 보강 패키지**

까지 포함한 **전체 멀티 에이전트 플랫폼 초안**입니다.

현재 상태는 매우 좋은 출발점입니다.
특히 다음이 분명합니다.

- 역할 분리 방향이 맞다
- Manager 중심 orchestration 방향이 맞다
- 학습과 운영 분리가 잘 되어 있다
- vLLM/Ollama 확장 방향이 이미 보인다

따라서 다음 단계는 무작정 Spring Boot로 옮기기보다,

> **현재 런타임을 먼저 안정화하고, 실제 요청 라우터와 RAG/Runner를 붙인 뒤, 그 다음 Spring Boot 전환 여부를 결정하는 순서**

가 가장 효율적입니다.

---

## 13. 바로 이어서 진행할 추천 다음 작업

다음 턴에서 가장 먼저 진행할 작업으로는 아래 2안 중 하나가 적합합니다.

### 안 1. 런타임 안정화 상세 점검서 작성

포함 내용:

- 어디부터 실행해야 하는지
- 어떤 설정이 필요한지
- 어떤 파일을 우선 수정해야 하는지
- 실행 에러 가능 포인트
- 단계별 체크리스트

### 안 2. vLLM 요청 라우터 + RAG + Runner 붙이는 상세 설계서 작성

포함 내용:

- 실제 target architecture
- 서비스 분리 구조
- API 설계
- DB 추가 테이블 설계
- 실행 순서
- 구현 우선순위

현재 우선순위상으로는 **안 1 → 안 2 순서**를 권장합니다.

