# AI Multi-Agent Platform Final Overview

## 1. 프로젝트 비전

AI Multi-Agent Platform은 자연어 요구를 입력으로 받아
요구사항 분석, 설계, 구현, 테스트, 보안 검증, 최종 병합까지 수행하는 **운영형 소프트웨어 제작 AI 시스템**입니다.

핵심 구조:
- PM
- Architect
- Dev-FE / Dev-BE / Dev-DB
- QA
- SecOps
- Manager / Orchestrator

---

## 2. 핵심 전략

### 전략 1. 역할별 SLM + LoRA
단일 모델에 모든 역할을 몰지 않고 역할에 맞는 SLM과 LoRA를 분리합니다.

### 전략 2. SFT 선행 후 GRPO
먼저 형식과 역할을 안정화하고, 자동 평가 가능한 영역부터 GRPO를 적용합니다.

### 전략 3. Tool Use + RAG + Orchestrator
실행 가능한 산출물을 위해 Tool Runner, Vector RAG, Router, Orchestrator를 결합합니다.

---

## 3. 권장 모델 포트폴리오

- Qwen2.5-3B-Instruct
- EXAONE 3.5 2.4B Instruct
- Qwen2.5-Coder-1.5B-Instruct

권장 역할 배치:
- PM / Manager: EXAONE
- Architect / QA / SecOps: Qwen2.5-3B
- Dev: Qwen2.5-Coder-1.5B

---

## 4. 학습 파이프라인

1. JSONL 준비
2. Schema Validator
3. SFT LoRA
4. Offline Eval
5. GRPO
6. Multi-agent simulation
7. Production serving

---

## 5. 운영 아키텍처

```text
User/API
  ↓
Manager / Orchestrator
  ↓
Router Service
  ↓
Role-specific Model / LoRA
  ↓
RAG + Tool Runner + Artifact Storage
  ↓
Eval / Logs / Traces / Alerts
```

---

## 6. 현재 운영 고도화 수준

현재 반영 기능:
- Router 기반 역할 라우팅
- Qdrant 기반 Vector RAG
- Sandbox runner
- Build / Test / Lint / Type / SAST
- Auth / RBAC
- Project membership
- Approval inbox
- Multi-stage approval
- Approval SLA / alert
- Dashboard / Workers live stream
- Replay audit / diff
- Dead-letter recovery
- Sandbox image split 및 CI/CD

---

## 7. 운영 가치

### 생산성
역할 분리와 자동 실행으로 개발 속도를 향상합니다.

### 품질
QA / SecOps / Replay / Approval 기반 검증을 강화합니다.

### 통제성
Approval, RBAC, Membership, Audit으로 운영 통제를 강화합니다.

### 확장성
Ollama → vLLM → multi-LoRA production으로 확장 가능합니다.

---

## 8. 추가 문서 구성

기존 4개 문서 외에 아래 문서를 함께 운영하는 것을 권장합니다.

- `phase_progress_summary.md`
- `document_index.md`

---

## 9. 결론

이 플랫폼은 개념 검토용 AI가 아니라,
**학습·오케스트레이션·실행·검증·승인·운영 관측이 통합된 실무형 AI 제작 시스템**입니다.
