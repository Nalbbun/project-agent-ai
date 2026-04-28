# AI 에이전트용 SLM 선정 및 학습 가이드

## 1. 프로젝트 목표

최종 목표는 사용자가 만들고 싶은 프로그램을 자연어로 설명하면, 다음 역할의 AI 에이전트들이 협업하여 결과물을 만드는 구조입니다.

- PM 에이전트: 요구사항 분석·정의
- Architect 에이전트: 시스템 설계
- Dev 에이전트: FE/BE/DB 구현
- QA 에이전트: 검증·테스트
- SecOps 에이전트: 보안·인프라 점검
- Manager: 오케스트레이션 및 결과 통합

핵심 전략은 **작지만 강력한 3B 이하 모델을 역할별 베이스로 두고, 각 역할별 LoRA 어댑터를 분리하여 SFT → GRPO 순으로 학습**하는 것입니다.

---

## 2. 기본 방향 요약

### 추천 원칙

1. **모든 역할에 동일 모델 1개를 쓰기보다, 역할별로 최적 모델 + LoRA 분리**가 유리합니다.
2. **처음부터 GRPO만 바로 적용하지 말고 SFT를 먼저 수행**해야 합니다.
3. **코드 역할은 코드 전용 모델**, 나머지 문서·설계·검증 역할은 범용 Instruct 모델이 더 안정적입니다.
4. **한국어·영어 이중언어성**이 중요하므로 bilingual 또는 multilingual 기반을 우선 검토합니다.
5. 최종적으로는 모델 단독보다 **툴 사용 + 오케스트레이션 + RAG**를 붙여야 실무형 시스템이 됩니다.

---

## 3. 추천 베이스 모델

### 3.1 전체 공통 1순위

#### Qwen2.5-3B-Instruct

추천 이유:
- 3B 이하에서 범용성이 좋음
- 구조화 출력(JSON/YAML) 안정성이 높음
- 설계, QA, SecOps, Manager 계열에 균형이 좋음
- Qwen2.5 계열은 0.5B부터 72B까지 공개되어 있어 확장성이 좋음
- 모델 카드 기준 32K 컨텍스트 지원

적합 역할:
- Architect
- QA
- SecOps
- Manager 대안 모델
- PM 대안 모델

### 3.2 한국어/영어 업무형 1순위

#### EXAONE 3.5 2.4B Instruct

추천 이유:
- LG AI Research 공개 모델
- **영어·한국어 bilingual instruct 모델**
- 2.4B로 작지만 실무형 업무 에이전트에 적합
- 모델 카드 기준 32K 컨텍스트 지원
- 한국어 중심 요구사항 정리, 문서화, 오케스트레이션에 유리

적합 역할:
- PM
- Manager
- QA 대안 모델

### 3.3 코드 전용 1순위

#### Qwen2.5-Coder-1.5B-Instruct

추천 이유:
- 소형이지만 코드 작성, 수정, 리팩토링에 최적화
- FE/BE/DB 개발 에이전트의 베이스로 적합
- 모델 카드 기준 32K 컨텍스트 지원
- 역할별 LoRA(FE / BE / DB) 분리가 쉬움

적합 역할:
- Dev-FE
- Dev-BE
- Dev-DB

### 3.4 보조 실험용

#### SmolLM3-3B

추천 이유:
- 3B급에서 reasoning 지향
- 모델 카드 기준 6개 언어 및 long context 지원
- 범용 reasoning 실험용으로 적합

적합 역할:
- Architect 대안
- SecOps 대안
- 경량 로컬 추론 실험

---

## 4. 역할별 최소 모델 추천

| 역할 | 추천 모델 | 대안 | 추천 이유 |
|---|---|---|---|
| PM | EXAONE 3.5 2.4B Instruct | Qwen2.5-3B-Instruct | 한국어·영어 문서화, 요구사항 정리, 질문 생성에 강점 |
| Architect | Qwen2.5-3B-Instruct | SmolLM3-3B | 구조화 설계, 긴 컨텍스트, 포맷 안정성 |
| Dev (FE/BE/DB) | Qwen2.5-Coder-1.5B-Instruct | Qwen2.5-3B-Instruct + 코드 LoRA | 코드 생성·수정·리팩토링 특화 |
| QA | Qwen2.5-3B-Instruct | EXAONE 3.5 2.4B Instruct | 테스트 케이스, 누락 검출, 요구사항 검증에 적합 |
| SecOps | Qwen2.5-3B-Instruct | SmolLM3-3B | 보안 정책, 설정, YAML, 인프라 점검에 균형 좋음 |
| Manager | EXAONE 3.5 2.4B Instruct | Qwen2.5-3B-Instruct | 조정·재질문·결과 통합 등 업무형 대화에 유리 |

---

## 5. 가장 현실적인 시작 조합

### 추천안 A: 역할별 분업형
- PM: EXAONE 3.5 2.4B Instruct
- Architect: Qwen2.5-3B-Instruct
- Dev: Qwen2.5-Coder-1.5B-Instruct
- QA: Qwen2.5-3B-Instruct
- SecOps: Qwen2.5-3B-Instruct
- Manager: EXAONE 3.5 2.4B Instruct

장점:
- 한국어/영어 문서형 업무는 EXAONE
- 설계/QA/보안은 Qwen2.5 3B
- 개발은 Coder 전용 모델로 분리

### 추천안 B: 단순 운영형
- 공통 베이스: Qwen2.5-3B-Instruct
- Dev만 별도: Qwen2.5-Coder-1.5B-Instruct
- 역할별 LoRA 어댑터만 분리

장점:
- 운영 복잡도 낮음
- 실험과 배포가 쉬움
- 초반 PoC에 적합

### 추천안 C: 한국어 비중이 큰 경우
- PM / QA / Manager: EXAONE 3.5 2.4B Instruct
- Architect / SecOps: Qwen2.5-3B-Instruct
- Dev: Qwen2.5-Coder-1.5B-Instruct

---

## 6. 학습 전략: SFT → GRPO → 역할별 고도화

### 6.1 왜 SFT를 먼저 해야 하는가

처음부터 RL(GRPO)로 들어가면 다음 문제가 발생하기 쉽습니다.
- 역할 준수 실패
- 출력 포맷 불안정
- 학습 보상 노이즈 증가
- 잘못된 행동 강화

따라서 먼저 SFT/LoRA로 아래를 안정화해야 합니다.
- 역할별 말투와 의사결정 방식
- JSON/YAML 출력 형식
- 한영 혼합 입력 처리
- 최소한의 업무 태스크 수행 능력

### 6.2 왜 그다음 GRPO인가

GRPO는 정답 문장을 외우는 방식보다, **행동 품질 최적화**에 적합합니다.

예:
- 설계 일관성 향상
- 테스트 누락 감소
- 형식 준수율 향상
- 보안 위반 감소
- 자기 수정 능력 강화

### 6.3 권장 학습 순서

1. PM / Architect / Dev 역할별 SFT LoRA
2. QA / SecOps / Manager SFT LoRA
3. QA / Dev부터 GRPO 적용
4. Architect / PM / SecOps / Manager 순으로 RL 확장

이유:
- QA와 Dev는 자동 평가가 쉬워 reward 설계가 명확함
- PM과 Manager는 보상 정의가 추상적이라 후순위가 안전함

---

## 7. 역할별 데이터 포맷 설계

### PM 데이터
입력:
- 사용자 요구

출력:
- 기능 요구사항
- 비기능 요구사항
- 질문 리스트
- 범위 정의
- Acceptance Criteria

### Architect 데이터
입력:
- 요구사항 명세

출력:
- 시스템 구성
- 모듈 분해
- API 정의
- DB 초안
- 시퀀스 흐름
- ADR

### Dev 데이터
입력:
- 설계 결과

출력:
- 코드
- 테스트 코드
- 마이그레이션
- 설정 파일

권장 분리:
- Dev-FE LoRA
- Dev-BE LoRA
- Dev-DB LoRA

### QA 데이터
입력:
- 요구사항 / 설계 / 코드

출력:
- 테스트 케이스
- 경계값 시나리오
- 회귀 체크리스트
- 버그 리포트

### SecOps 데이터
입력:
- 코드 / Dockerfile / YAML / IaC / CI 설정

출력:
- 위험 항목
- 보안 위반 분류
- 하드닝 가이드
- 우선 조치안

### Manager 데이터
입력:
- 전체 태스크 상태

출력:
- 작업 분배
- 에이전트 호출 순서
- 부족 정보 재질문
- 결과 병합
- 최종 산출물 요약

---

## 8. GRPO용 Reward 설계 가이드

역할별 reward는 서로 달라야 합니다.

### 공통 Reward
- JSON Schema 통과 여부
- 형식 준수율
- 중복 및 모순 패널티
- hallucination 패널티
- 지정한 섹션 누락 패널티

### PM Reward
- 요구사항 커버율
- 질문 품질
- 기능/비기능 분리 정확도

### Architect Reward
- 설계 일관성
- 컴포넌트 간 연결 정확도
- API / DB / 흐름의 정합성

### Dev Reward
- 빌드 성공 여부
- 테스트 통과율
- 린트 통과율
- 실행 가능성

### QA Reward
- 결함 탐지율
- 테스트 케이스 다양성
- 요구사항 대비 누락 검출률

### SecOps Reward
- 취약점 탐지율
- 잘못된 설정 탐지율
- 위험도 우선순위 정확성

### Manager Reward
- 작업 분해 적절성
- 순서 제어 품질
- 재질문 필요성 판단 정확도
- 전체 결과 통합 품질

---

## 9. 모델보다 더 중요한 설계 요소

### 9.1 Tool Use
실무형 AI 제작 시스템은 모델만으로 완성되지 않습니다.
필수적으로 연결할 툴 예시는 다음과 같습니다.

- 코드 실행 샌드박스
- 테스트 러너
- 린터 / 타입체커
- 보안 스캐너(SAST / dependency scan)
- DB schema diff
- Git patch 생성기
- 파일 생성 및 프로젝트 템플릿 생성기

### 9.2 RAG
작은 모델은 모든 지식을 내장하기 어렵습니다.
다음 정보를 외우게 하기보다 검색하게 하는 편이 훨씬 효율적입니다.

- 사내 코딩 규칙
- 아키텍처 표준
- 보안 정책
- 운영 가이드
- 프로젝트 템플릿
- 기존 코드베이스 컨텍스트

### 9.3 Evaluation Set
학습보다 먼저 평가셋을 만드세요.
권장 규모:
- 역할별 100~300개 이상
- 쉬운 문제 / 중간 난이도 / 실무형 문제 구분
- 한국어 / 영어 / 혼합 입력 모두 포함

이 평가셋이 없으면 LoRA와 GRPO를 반복해도 성능 향상 여부를 판단하기 어렵습니다.

---

## 10. 권장 개발 로드맵

### Phase 1. PoC
- Qwen2.5-3B-Instruct 1개로 공통 실험
- Dev만 Qwen2.5-Coder-1.5B-Instruct 사용
- 역할 프롬프트만 분리

### Phase 2. 역할별 SFT LoRA
- PM / Architect / Dev 우선
- 역할별 출력 포맷 고정
- 기본 업무 성능 확보

### Phase 3. 역할별 GRPO
- QA / Dev부터 시작
- 자동 평가 가능한 reward부터 적용
- 이후 Architect / PM / SecOps / Manager 확장

### Phase 4. 멀티 에이전트 오케스트레이션
- Manager가 작업 분해
- PM → Architect → Dev → QA → SecOps 순서 실행
- 실패 시 재시도 또는 상위 재정의 루프 적용

### Phase 5. 실무 배포
- RAG 연결
- 프로젝트 템플릿 자동 생성
- 코드 패치 생성
- 테스트 / 보안 검사 자동 실행
- 최종 산출물 패키징

---

## 11. 최종 추천

### 가장 먼저 선택할 기본 베이스
1. **Qwen2.5-3B-Instruct**
2. **EXAONE 3.5 2.4B Instruct**
3. **Qwen2.5-Coder-1.5B-Instruct**
4. **SmolLM3-3B**(보조 실험용)

### 가장 현실적인 한 줄 전략

**범용 3B 1개 + 코드 1.5B 1개 + 역할별 LoRA + SFT 선행 + 이후 GRPO + Tool Use + RAG**

이 구성이 현재 기준으로 가장 성공 확률이 높은 시작점입니다.

---

## 12. 참고 소스

- Qwen2.5-3B-Instruct model card: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct
- Qwen2.5-Coder-1.5B-Instruct model card: https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct
- EXAONE 3.5 2.4B Instruct model card: https://huggingface.co/LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct
- SmolLM3-3B model card: https://huggingface.co/HuggingFaceTB/SmolLM3-3B
- TRL GRPO Trainer docs: https://huggingface.co/docs/trl/grpo_trainer
- TRL LoRA docs: https://huggingface.co/docs/trl/lora_without_regret
