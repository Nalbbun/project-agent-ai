# AI 멀티 에이전트 실무 설계안
## 역할별 JSONL 스키마 · Reward 설계 · SFT→GRPO 파이프라인 · 배포 아키텍처

> 기준 방향: 역할별 SLM + LoRA + SFT 선행 + 이후 GRPO + Tool Use + RAG

---

## 1. 목표 시스템 정의

최종 목표는 사용자가 자연어로 프로그램 요구를 입력하면, 아래 순서로 에이전트가 협업하는 구조입니다.

1. **PM**: 요구사항 구조화
2. **Architect**: 시스템 설계
3. **Dev**: FE / BE / DB 구현
4. **QA**: 검증 / 테스트
5. **SecOps**: 보안 / 인프라 점검
6. **Manager**: 순서 제어, 재질문, 결과 병합

핵심은 모델 자체보다 **역할 분리, 포맷 안정성, 자동평가 가능성, 툴 연동성**입니다.

---

## 2. 권장 베이스 모델 매핑

### 2.1 기본 추천
- **공통 베이스**: Qwen2.5-3B-Instruct
- **개발 전용**: Qwen2.5-Coder-1.5B-Instruct
- **한국어/영어 업무형 보조**: EXAONE 3.5 2.4B Instruct

### 2.2 역할별 배치
| 역할 | 베이스 모델 | 어댑터 전략 |
|---|---|---|
| PM | EXAONE 3.5 2.4B 또는 Qwen2.5-3B | `pm-lora` |
| Architect | Qwen2.5-3B | `architect-lora` |
| Dev-FE | Qwen2.5-Coder-1.5B | `dev-fe-lora` |
| Dev-BE | Qwen2.5-Coder-1.5B | `dev-be-lora` |
| Dev-DB | Qwen2.5-Coder-1.5B | `dev-db-lora` |
| QA | Qwen2.5-3B | `qa-lora` |
| SecOps | Qwen2.5-3B | `secops-lora` |
| Manager | EXAONE 3.5 2.4B 또는 Qwen2.5-3B | `manager-lora` |

### 2.3 핵심 판단
- Dev는 반드시 FE / BE / DB로 분리하는 것이 좋습니다.
- PM / QA / Manager는 한국어·영어 업무형 문장 처리 안정성이 중요합니다.
- Architect / SecOps는 구조화 출력과 긴 컨텍스트 안정성이 중요합니다.

---

## 3. JSONL 학습 데이터 스키마 설계

### 3.1 공통 원칙
모든 역할 데이터는 공통적으로 아래 필드를 유지합니다.

```json
{
  "id": "pm-000001",
  "role": "pm",
  "lang": "ko|en|mixed",
  "domain": "webapp|backend|infra|data|mobile|game",
  "difficulty": "easy|medium|hard",
  "input": {},
  "output": {},
  "metadata": {
    "source": "human|synthetic|distilled|production",
    "version": "v1",
    "tags": ["requirements", "crud", "auth"]
  }
}
```

#### 설계 원칙
- `role`은 단일 역할만 지정
- `lang`은 `ko`, `en`, `mixed`
- `output`은 자연어보다 JSON/YAML/코드 중심
- SFT와 GRPO 모두를 위해 검증 가능한 구조 유지

### 3.2 PM JSONL 스키마
```json
{
  "id": "pm-000001",
  "role": "pm",
  "lang": "ko",
  "domain": "webapp",
  "difficulty": "medium",
  "input": {
    "user_request": "사내 결재 시스템을 만들고 싶다. 관리자 페이지와 승인 흐름이 있어야 한다."
  },
  "output": {
    "summary": "사내 결재 시스템 구축 요구",
    "functional_requirements": ["문서 기안", "결재선 지정", "승인/반려 처리", "관리자 사용자 관리"],
    "non_functional_requirements": ["사내 SSO 연동", "감사 로그 보관", "권한 기반 접근 통제"],
    "questions": ["결재 단계는 고정형인가?", "모바일 승인 기능이 필요한가?"],
    "out_of_scope": ["전자서명 법적 인증 모듈"],
    "acceptance_criteria": ["기안자는 결재 요청을 생성할 수 있어야 한다"]
  }
}
```

### 3.3 Architect JSONL 스키마
```json
{
  "id": "arch-000001",
  "role": "architect",
  "lang": "mixed",
  "domain": "webapp",
  "difficulty": "hard",
  "input": {
    "requirements": {
      "functional_requirements": ["문서 기안", "결재선 지정", "승인/반려 처리"],
      "non_functional_requirements": ["SSO 연동", "감사 로그", "RBAC"]
    }
  },
  "output": {
    "architecture_style": "modular monolith",
    "components": [
      {"name": "frontend", "responsibility": "기안/결재 UI"},
      {"name": "approval-service", "responsibility": "결재 상태 전이"},
      {"name": "audit-service", "responsibility": "감사 로그 적재"}
    ],
    "apis": [
      {"method": "POST", "path": "/api/approvals", "purpose": "결재 요청 생성"}
    ],
    "database": {"entities": ["document", "approval_line", "approval_action", "user", "role"]},
    "sequence": ["user submits document", "service validates route", "audit recorded"],
    "adrs": ["RBAC 적용", "감사 로그는 append-only 저장"]
  }
}
```

### 3.4 Dev JSONL 스키마
#### Dev-FE
```json
{
  "id": "dev-fe-000001",
  "role": "dev-fe",
  "lang": "ko",
  "domain": "webapp",
  "difficulty": "medium",
  "input": {
    "task": "결재 목록 페이지 구현",
    "design_context": {
      "framework": "React + TypeScript",
      "api": [{"method": "GET", "path": "/api/approvals"}],
      "ui_requirements": ["상태별 배지 표시", "검색 필터", "페이지네이션"]
    }
  },
  "output": {
    "files": [{"path": "src/pages/ApprovalListPage.tsx", "content": "..."}],
    "tests": [{"path": "src/pages/ApprovalListPage.test.tsx", "content": "..."}]
  }
}
```

#### Dev-BE
```json
{
  "id": "dev-be-000001",
  "role": "dev-be",
  "lang": "en",
  "domain": "backend",
  "difficulty": "medium",
  "input": {
    "task": "Create approval submission API",
    "design_context": {
      "framework": "Spring Boot",
      "api_contract": {"method": "POST", "path": "/api/approvals"}
    }
  },
  "output": {
    "files": [
      {"path": "ApprovalController.java", "content": "..."},
      {"path": "ApprovalService.java", "content": "..."}
    ],
    "tests": [{"path": "ApprovalControllerTest.java", "content": "..."}]
  }
}
```

#### Dev-DB
```json
{
  "id": "dev-db-000001",
  "role": "dev-db",
  "lang": "mixed",
  "domain": "data",
  "difficulty": "medium",
  "input": {
    "task": "결재 문서 및 승인 이력 테이블 설계",
    "constraints": ["PostgreSQL", "감사 로그 추적 가능", "soft delete 금지"]
  },
  "output": {
    "ddl": ["CREATE TABLE approval_document (...);", "CREATE TABLE approval_action (...);"] ,
    "indexes": ["CREATE INDEX idx_approval_document_status ON approval_document(status);"] ,
    "migration": {"tool": "Flyway", "file": "V001__create_approval_tables.sql"}
  }
}
```

### 3.5 QA JSONL 스키마
```json
{
  "id": "qa-000001",
  "role": "qa",
  "lang": "ko",
  "domain": "webapp",
  "difficulty": "medium",
  "input": {
    "requirements": [
      "기안자는 결재 요청을 생성할 수 있어야 한다",
      "승인자는 승인/반려 의견을 남길 수 있어야 한다"
    ],
    "code_summary": "결재 생성 API 및 UI 구현 완료"
  },
  "output": {
    "test_cases": [
      {"title": "정상 결재 요청 생성", "given": "로그인한 기안자", "when": "필수값 입력 후 저장", "then": "결재 요청 생성"},
      {"title": "필수값 누락 검증", "given": "제목 없는 문서", "when": "저장 시도", "then": "검증 에러 표시"}
    ],
    "boundary_cases": ["결재선 1명", "결재선 최대 인원"],
    "regression_checklist": ["목록 조회 영향 없음", "알림 발송 영향 없음"]
  }
}
```

### 3.6 SecOps JSONL 스키마
```json
{
  "id": "secops-000001",
  "role": "secops",
  "lang": "en",
  "domain": "infra",
  "difficulty": "hard",
  "input": {
    "artifacts": {
      "dockerfile": "...",
      "k8s_yaml": "...",
      "ci_pipeline": "...",
      "app_config": "..."
    }
  },
  "output": {
    "findings": [
      {
        "severity": "high",
        "category": "secret-exposure",
        "issue": "Database password is hardcoded in deployment manifest",
        "recommendation": "Move secret to Kubernetes Secret or external secret manager"
      }
    ],
    "hardening_actions": ["runAsNonRoot 적용", "readOnlyRootFilesystem 적용", "image digest pinning"],
    "priority_order": ["Remove plaintext secret", "Drop root privileges", "Restrict network policy"]
  }
}
```

### 3.7 Manager JSONL 스키마
```json
{
  "id": "mgr-000001",
  "role": "manager",
  "lang": "ko",
  "domain": "webapp",
  "difficulty": "hard",
  "input": {
    "user_request": "사내 결재 시스템을 만들어줘",
    "current_state": {"pm": null, "architect": null, "dev": null, "qa": null, "secops": null}
  },
  "output": {
    "execution_plan": [
      {"step": 1, "agent": "pm", "task": "요구사항 구조화"},
      {"step": 2, "agent": "architect", "task": "시스템 설계"},
      {"step": 3, "agent": "dev-be", "task": "백엔드 API 구현"},
      {"step": 4, "agent": "dev-fe", "task": "프론트엔드 화면 구현"},
      {"step": 5, "agent": "qa", "task": "테스트 설계 및 검증"},
      {"step": 6, "agent": "secops", "task": "보안 검토"}
    ],
    "missing_info_questions": ["결재 단계 수는?", "사내 SSO 종류는?"],
    "merge_strategy": ["Architect 결과를 Dev 입력으로 전달", "QA/SecOps 결과를 Dev 재작업 입력으로 전달"]
  }
}
```

---

## 4. 데이터셋 운영 규칙

### 4.1 학습셋 비율
- 60% 실제 실무 문서 기반 정제
- 20% 고품질 synthetic augmentation
- 20% self-instruct / distillation

### 4.2 언어 비율
- `ko`: 40%
- `en`: 40%
- `mixed`: 20%

### 4.3 난이도 비율
- easy: 30%
- medium: 50%
- hard: 20%

### 4.4 금지 규칙
- 검증 불가능한 샘플 금지
- output 포맷 흔들리는 데이터 금지
- 한 샘플에 두 역할 이상 혼합 금지
- Manager 데이터에 구현 상세 과도 주입 금지

---

## 5. Reward 설계

### 5.1 공통 Reward
```text
R_total = 
  w_format * R_format
+ w_schema * R_schema
+ w_completeness * R_completeness
+ w_consistency * R_consistency
- w_hallucination * P_hallucination
- w_redundancy * P_redundancy
```

### 5.2 PM Reward
```text
R_pm =
  0.30 * requirements_coverage
+ 0.20 * nonfunctional_separation
+ 0.20 * question_quality
+ 0.20 * acceptance_criteria_quality
+ 0.10 * scope_boundary_clarity
```

### 5.3 Architect Reward
```text
R_arch =
  0.25 * component_coverage
+ 0.25 * api_db_consistency
+ 0.20 * sequence_validity
+ 0.15 * adr_quality
+ 0.15 * design_coherence
```

### 5.4 Dev Reward
```text
R_dev =
  0.35 * build_success
+ 0.25 * unit_test_pass_rate
+ 0.15 * lint_pass
+ 0.10 * static_type_pass
+ 0.10 * contract_match
+ 0.05 * patch_minimality
```

### 5.5 QA Reward
```text
R_qa =
  0.35 * defect_detection_rate
+ 0.20 * boundary_case_diversity
+ 0.20 * requirement_traceability
+ 0.15 * regression_relevance
+ 0.10 * reproducibility
```

### 5.6 SecOps Reward
```text
R_secops =
  0.30 * vuln_detection_rate
+ 0.25 * config_misuse_detection
+ 0.20 * severity_prioritization
+ 0.15 * remediation_actionability
+ 0.10 * false_positive_control
```

### 5.7 Manager Reward
```text
R_manager =
  0.30 * task_decomposition_quality
+ 0.25 * ordering_validity
+ 0.20 * missing_info_detection
+ 0.15 * merge_quality
+ 0.10 * retry_strategy_quality
```

---

## 6. SFT → GRPO 학습 파이프라인

### Phase 0. 데이터 준비
- 역할별 JSONL 정제
- schema validator 구축
- train/valid/test 분리
- eval harness 구성

### Phase 1. SFT
- 역할별 LoRA 학습
- 형식 준수와 역할 안정화
- 구조화 출력 정착

### Phase 2. Offline Eval
- schema pass rate
- task pass rate
- role-specific metrics 측정

### Phase 3. GRPO
- QA / Dev부터 시작
- reward 함수 연결
- rollout + grading + update loop

### Phase 4. Multi-agent simulation
- Manager 포함 전체 체인 실행
- 단계별 품질 측정

### Phase 5. Productionization
- adapter registry
- serving
- routing
- observability
- fallback

### SFT 권장 세팅
- `r`: 16 또는 32
- `lora_alpha`: 32 또는 64
- `lora_dropout`: 0.05
- `bf16`: 가능하면 활성화
- `gradient_checkpointing`: 사용
- `max_seq_length`: 4K~8K부터 시작

### GRPO 적용 순서
1. Dev-FE
2. Dev-BE
3. Dev-DB
4. QA
5. SecOps
6. Architect
7. PM
8. Manager

---

## 7. 평가 체계

### 7.1 역할별 핵심 지표
| 역할 | 핵심 지표 |
|---|---|
| PM | 요구사항 커버율, 질문 품질, AC 품질 |
| Architect | API-DB 정합성, 컴포넌트 완결성, 흐름 일관성 |
| Dev | build/test/lint/type 성공률 |
| QA | 결함 탐지율, 경계값 다양성, 재현성 |
| SecOps | misconfig 탐지율, false positive, remediation 품질 |
| Manager | task ordering 정확도, re-plan 품질, merge 품질 |

### 7.2 공통 게이트
- schema pass > 95%
- role task success > 85%
- hallucination penalty low
- regression failure 없음

---

## 8. 배포 아키텍처

### 8.1 권장 기본 구조
```text
[User/API]
   ↓
[Manager / Orchestrator]
   ↓
[Task Router]
   ├─ PM Adapter
   ├─ Architect Adapter
   ├─ Dev-FE Adapter
   ├─ Dev-BE Adapter
   ├─ Dev-DB Adapter
   ├─ QA Adapter
   ├─ SecOps Adapter
   ↓
[Tool Layer]
   ├─ Sandbox / Runner
   ├─ Test
   ├─ Lint / Type Check
   ├─ SAST / Dependency Scan
   ├─ RAG
   └─ Artifact Storage
   ↓
[Eval / Logs / Traces]
```

### 8.2 vLLM 기준
**적합한 경우**
- 역할별 LoRA를 동적으로 선택해야 할 때
- 처리량이 중요할 때
- OpenAI 호환 API로 통합하고 싶을 때

**장점**
- 고처리량
- 멀티 LoRA
- OpenAI API 호환
- scale-out 용이

**추천도**
- **프로덕션 1순위**

### 8.3 Ollama 기준
**적합한 경우**
- 빠른 PoC
- 내부 개발팀 로컬 실행
- 운영 단순성이 최우선일 때

**장점**
- 가장 간단
- 로컬 실험 쉬움
- 배포 진입장벽 낮음

**추천도**
- **PoC / 내부 개발용 1순위**

### 8.4 TGI 기준
**적합한 경우**
- Hugging Face 중심 생태계
- TGI 운영 경험이 있는 팀
- Inference Endpoint 스타일 운영

**장점**
- 고성능
- HF 친화적
- LoRA 지원

**추천도**
- **HF 중심 운영 시 1순위, 일반 멀티에이전트는 2순위**

---

## 9. 최종 권장 배포안

### 9.1 PoC 단계
- Ollama
- 역할별 모델 개별 등록
- Manager는 애플리케이션 레벨에서 라우팅
- Tool Use는 외부 Python/Java 서비스로 연결

### 9.2 검증 단계
- vLLM
- base model 2~3개 + multi-LoRA
- OpenAI-compatible API 통합
- observability/logging 추가

### 9.3 운영 단계
- vLLM 메인 + RAG + Tool Layer + Eval Harness
- 필요 시 일부 보조 워커는 TGI 또는 별도 inference node

---

## 10. 오케스트레이터 설계

### 10.1 Manager 동작 규칙
1. 사용자 요구 수신
2. 충분한 정보인지 판별
3. 부족하면 질문 생성
4. PM 호출
5. PM 결과를 Architect 입력으로 전달
6. Architect 결과를 Dev/QA/SecOps에 분배
7. QA/SecOps 실패면 Dev 재작업
8. 최종 병합 후 산출물 패키징

### 10.2 상태 모델 예시
```json
{
  "request_id": "req-20260414-001",
  "status": "running",
  "stage": "dev-be",
  "artifacts": {
    "pm": "s3://.../pm.json",
    "architect": "s3://.../architect.json",
    "dev_be": null,
    "qa": null
  },
  "retry_count": {
    "dev-be": 1
  }
}
```

---

## 11. 실무 구현 순서

### Step 1
PM / Architect / Dev-FE / Dev-BE / Dev-DB용 JSONL 200~500개씩 준비

### Step 2
역할별 schema validator 작성

### Step 3
Qwen2.5-3B + Qwen2.5-Coder-1.5B 기준 SFT LoRA 학습

### Step 4
Dev/QA용 자동 평가 harness 구축
- build
- test
- lint
- type check
- security scan

### Step 5
Dev → QA 순서로 GRPO 적용

### Step 6
Manager를 붙여 end-to-end workflow 검증

### Step 7
vLLM 기반 multi-LoRA serving으로 전환

---

## 12. 최종 결론

**데이터는 역할별 JSONL로 분리하고, SFT로 역할·형식을 먼저 고정한 뒤, Dev/QA부터 GRPO를 적용하고, 배포는 PoC는 Ollama, 운영은 vLLM multi-LoRA 중심으로 가는 것이 가장 현실적입니다.**

---

## 13. 참고 소스
- Qwen2.5-3B-Instruct model card
- Qwen2.5-Coder-1.5B-Instruct model card
- EXAONE 3.5 2.4B Instruct model card
- TRL GRPO Trainer docs
- PEFT LoRA docs
- vLLM OpenAI-compatible server docs
- Ollama import / adapter docs
- Hugging Face TGI docs
