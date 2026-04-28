# AI Multi-Agent Orchestrator Platform

## 1. 문서 목적

이 문서는 업로드된 `ai_agent_slm_strategy.md` 와 `ai_agent_multiactor_design.md` 를 기준으로,
현재까지 고도화된 멀티 에이전트 플랫폼의 **전체 개요, 운영 범위, 디렉토리 구조, 실행 방향**을 한 번에 이해할 수 있도록 재정리한 메인 README입니다.

본 플랫폼은 단순 챗봇이 아니라, 자연어 요구를 받아 **요구사항 정리 → 설계 → 구현 → 검증 → 보안 점검 → 병합/승인**까지 수행하는 운영형 소프트웨어 제작 AI 시스템입니다.

---

## 2. 핵심 개념

### 2.1 역할 구조
- PM: 요구사항 구조화, 질문, 범위 정의
- Architect: 시스템 구성, API, DB, ADR, 시퀀스 설계
- Dev-FE / Dev-BE / Dev-DB: 코드, 테스트, 마이그레이션 생성
- QA: 테스트 케이스, 경계값, 회귀 검증
- SecOps: 보안 점검, 하드닝, 우선조치 제안
- Manager / Orchestrator: 전체 순서 제어, 재질문, 재시도, 병합

### 2.2 한 줄 전략
**범용 3B 1개 + 코드 1.5B 1개 + 역할별 LoRA + SFT 선행 + 이후 GRPO + Tool Use + RAG**

### 2.3 운영 원칙
- 역할별 책임 분리
- JSON / YAML / 코드 중심 구조화 출력
- 자동 평가 가능한 태스크 우선
- Tool Use 와 RAG 전제
- Manager가 상태와 승인 흐름을 제어

---

## 3. 권장 모델 포트폴리오

### 공통 범용
- Qwen2.5-3B-Instruct

### 한국어/영어 업무형
- EXAONE 3.5 2.4B Instruct

### 개발 전용
- Qwen2.5-Coder-1.5B-Instruct

### 권장 배치
- PM / Manager: EXAONE 3.5 2.4B 또는 Qwen2.5-3B
- Architect / QA / SecOps: Qwen2.5-3B
- Dev-FE / Dev-BE / Dev-DB: Qwen2.5-Coder-1.5B

---

## 4. 학습 전략

### Phase 0. 데이터 준비
- 역할별 JSONL 정제
- schema validator 구성
- train / valid / test 분리
- eval harness 준비

### Phase 1. SFT
- 역할별 LoRA 학습
- 형식 안정화
- 역할 준수 고정

### Phase 2. Offline Eval
- schema pass
- task success
- 역할별 핵심 지표 측정

### Phase 3. GRPO
- Dev / QA부터 보상 함수 연결
- 자동 평가 가능한 태스크 우선 강화학습

### Phase 4. Multi-agent Simulation
- Manager 포함 end-to-end 검증

### Phase 5. Productionization
- router
- tool runner
- rag
- observability
- approval / replay / alert

---

## 5. 현재 소스 기준 반영 범위

### 학습 영역
- 역할별 JSON Schema / JSONL 샘플
- reward 코드 골격
- SFT / GRPO 스크립트 골격
- vLLM / Ollama / k8s 배포 예시

### 런타임 영역
- Manager-Orchestrator 백엔드/프론트
- Router 기반 role routing
- Qdrant 기반 Vector RAG
- Sandbox runner
- build / test / lint / type / SAST
- Auth / RBAC
- project membership
- approval inbox / multi-stage approval
- replay audit / diff / dead-letter recovery
- dashboard / workers / alerts
- sandbox image split 및 CI/CD

---

## 6. 디렉토리 구조

```text
.
├─ learning/
│  ├─ schemas/
│  ├─ rewards/
│  ├─ train/
│  ├─ serving/
│  ├─ configs/
│  └─ data_examples/
├─ runtime/
│  ├─ manager-orchestrator/
│  │  ├─ backend/
│  │  ├─ frontend/
│  │  ├─ db/
│  │  ├─ config/
│  │  ├─ sandbox-images/
│  │  └─ docker-compose.yml
│  └─ work_proxy_deploy/
│     ├─ router_service/
│     ├─ configs/
│     └─ docker-compose.integrated.yml
└─ docs/
```

---

## 7. 권장 운영 모드

### PoC
- Ollama
- 역할별 모델 개별 등록
- 내부 로컬 실험

### 검증
- vLLM multi-LoRA
- Router 연결
- Vector RAG + Tool Runner

### 운영
- vLLM + Router + Qdrant + Sandbox Runner + Approval + Alerts
- 승인, 재실행, 감사 이력, live monitoring 포함

---

## 8. 주요 문서

- `README.md`
- `system_build_manual.md`
- `user_manual.md`
- `final_overview.md`
- `phase_progress_summary.md`
- `document_index.md`

---

## 9. 결론

이 프로젝트는 모델 성능만을 다루는 문서 세트가 아니라,
**역할 분리형 학습 전략 + 운영형 오케스트레이션 + 실무 자동화 계층**까지 포함하는 전체 플랫폼 문서입니다.
