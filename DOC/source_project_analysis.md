# project-agent-ai 프로젝트 1차 분석 리포트

## 1) 한 줄 요약
이 프로젝트는 **역할 분리형 멀티 에이전트(Manager/PM/Architect/Dev/QA/SecOps)**를 대상으로, 
- 상위 설계/학습 자산(`DOC/`, `source/learning/`)
- 실제 실행 런타임(`source/runtime/manager-orchestrator`, `source/runtime/work_proxy_deploy`)
를 함께 제공하는 **학습 + 오케스트레이션 통합형 저장소**입니다.

---

## 2) 현재 저장소 구조 분석

### A. 문서/설계 자산 (DOC)
- `DOC/ai_agent_multiactor_design.md`:
  - 역할별 파이프라인(Manager→PM→Architect→Dev→QA/SecOps→Manager merge)
  - 역할별 JSONL 스키마 설계
  - SFT→GRPO 흐름과 운영 관점의 설계 원칙
- `DOC/ai_agent_slm_strategy.md`:
  - 3B 이하 중심의 모델 선정 기준
  - 역할별 베이스 모델/LoRA 분리 전략
  - SFT 선행 후 GRPO 확장 전략

### B. 학습 자산 (source/learning)
- `schemas/`: 역할 8종 JSON Schema
- `rewards/`: 역할별 reward 코드 골격
- `train/`: SFT/GRPO 템플릿, 검증 스크립트
- `serving/`: vLLM/Ollama/k8s 배포 템플릿
- `configs/`: 로컬 실행/어댑터 레지스트리 예시

즉, 학습 파이프라인 설계가 이미 파일 구조로 분해되어 있어, 데이터/보상/학습/서빙을 분리해서 확장하기 좋습니다.

### C. 런타임 자산 (source/runtime)
1. `manager-orchestrator`
   - FastAPI + SQLModel + PostgreSQL 기반 백엔드
   - React + Vite + TypeScript 프론트엔드
   - 실행(run) 생성/큐잉/재시도/취소/이벤트 스트리밍/SSE 제공
   - 단계별 승인(approval), worker, artifact 기능 포함
2. `work_proxy_deploy/router_service`
   - role 기반으로 OpenAI-compatible 요청을 vLLM/Ollama 등으로 라우팅하는 프록시

즉, “역할별 모델 라우팅” + “워크플로우 실행기”가 분리되어 있어 운영 아키텍처가 명확합니다.

---

## 3) 실제 오케스트레이션 동작 관찰 포인트

### 파이프라인 정의
`app/services/orchestrator.py`에 고정 파이프라인이 코드 상수로 정의되어 있습니다.
- manager-plan
- pm
- architect
- dev-fe / dev-be / dev-db
- qa / secops
- manager-merge

장점:
- 단계 의존성이 명확하여 장애 분석과 리플레이 기준점이 분명함

주의점:
- 파이프라인이 코드 상수라 커스텀 워크플로우(역할 추가, 순서 변경)를 동적으로 바꾸려면 설정화가 필요함

### 재시도/복구(Dead-letter replay)
`dead_letter_replay()`가 구현되어 있어,
- last failed부터 재실행
- 특정 phase부터 재실행
- full reset
등 운영 중 장애 복구 시나리오를 지원합니다.

장점:
- 단순 retry 이상으로 운영 복구 플로우가 준비됨

주의점:
- 복구 이력(audit)이 누적되므로, 장기 운영 시 DB 보관/아카이빙 정책이 필요함

### 헬스체크
`/health/live`, `/health/ready`, `/health`를 분리해,
- DB 연결
- vector store
- worker 상태
- stale run
를 readiness에 반영합니다.

장점:
- 쿠버네티스 readiness/liveness에 바로 연결 가능한 구조

---

## 4) 이 프로젝트의 강점

1. **역할 분리 철학이 문서/코드에 일관되게 반영**
   - 문서 설계, 학습 스키마, 런타임 파이프라인이 동일한 역할 체계를 공유
2. **실무 운영 기능이 이미 포함**
   - queue, retry, replay, approval, event stream, artifact
3. **학습-서빙-오케스트레이션의 연결 고리 존재**
   - learning 자산 + router_service + orchestrator가 이어짐
4. **PoC에서 운영으로 넘어가기 쉬운 디렉터리 구성**
   - docker-compose, k8s, config 템플릿 동시 제공

---

## 5) 리스크/개선 우선순위

### 우선순위 1: 동적 파이프라인 설정화
- 현재는 고정 상수 파이프라인
- 개선: DB 또는 YAML 기반 파이프라인 정의 + 검증 로직 추가

### 우선순위 2: 관측성(Observability) 강화
- 현재 이벤트/상태는 있으나, 운영 지표 표준화는 추가 여지
- 개선: OpenTelemetry + 단계별 latency/error/approval 대기시간 메트릭

### 우선순위 3: 데이터/모델 버전 트래킹 강화
- 학습/배포 자산은 있으나, 런타임 run과 모델 버전의 강한 결합 추적은 확장 여지
- 개선: run_metadata에 adapter/model/git sha 강제 기록

### 우선순위 4: 보안 경계 명시화
- role router + LLM endpoint 연동 구조상 키/권한/네트워크 경계가 중요
- 개선: Secret manager 연동, 최소권한 네트워크 정책, 감사 로그 표준화

---

## 6) “먼저 분석” 기준의 결론

현재 상태는 **개념 문서만 있는 초기 단계가 아니라, 실행 가능한 런타임과 학습 설계가 결합된 중후반 단계**입니다.

다음 단계 권장:
1. `manager-orchestrator`를 `SIMULATION_MODE=true`로 기동해 end-to-end run 확인
2. role router를 붙여 실제 role별 backend route 검증
3. dead-letter replay/approval 포함 운영 시나리오 테스트 케이스 작성
4. 이후 pipeline 설정화 및 관측성 도입

이 순서로 가면 PoC 품질을 빠르게 운영 품질로 끌어올릴 수 있습니다.
