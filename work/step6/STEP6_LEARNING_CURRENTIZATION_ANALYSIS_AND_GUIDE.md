# Step 6 - Learning 현행화 분석 및 다음 단계 가이드

작성일: 2026-04-28

## 목표

`source/learning`을 Step 5 기준 runtime 상태와 비교하여, 학습 산출물을 어떤 순서로 현행화해야 하는지 정리했다.

## 확인한 대상

- `source/learning` 전체 구조
- role별 schema/sample JSONL
- reward skeleton
- train script
- vLLM/Ollama/k8s serving 예시
- runtime `agents.yaml`
- runtime router config
- runtime schema validator/prompt/tool runner

## 검증 결과

`source/learning/data_examples/scripts/validate_samples.py` 실행 결과:

```text
all_valid=True
files=16 passed=1975 failed=0
pm: valid=True passed=225 failed=0
architect: valid=True passed=400 failed=0
dev-fe: valid=True passed=225 failed=0
dev-be: valid=True passed=225 failed=0
dev-db: valid=True passed=225 failed=0
qa: valid=True passed=225 failed=0
secops: valid=True passed=225 failed=0
manager: valid=True passed=225 failed=0
```

## 분석 결론

learning은 기본 schema/sample 관점에서는 정상이다.

하지만 Step 5 runtime은 이미 운영 기능이 많이 확장되어 있어, learning 쪽은 다음 운영 신호를 아직 충분히 학습 데이터/reward에 반영하지 못한다.

- RAG/project knowledge/reindex
- tool runner build/test/lint/type/scan report
- approval/RBAC/project membership context
- dead-letter replay/replay audit/diff
- router backend/model/fallback metadata
- docker sandbox execution result

따라서 다음 단계는 즉시 fine-tuning이 아니라 `runtime trace export -> schema/reward v2 -> alignment check` 순서가 적절하다.

## 이번 Step 6에서 추가한 산출물

- `source/learning/LEARNING_CURRENTIZATION_GUIDE_STEP6.md`
- `source/learning/configs/runtime_alignment.step6.yaml`
- 갱신된 sample validation report
  - `source/learning/data_examples/reports/validation_report.json`
  - `source/learning/data_examples/reports/validation_summary.txt`

## 다음 단계 작업 순서

1. `scripts/check_runtime_alignment.py`
   - runtime agent/router/adapter/schema required key 동기화 검사

2. `scripts/export_runtime_traces.py`
   - 운영 DB의 run/step/artifact/event/replay audit를 role별 JSONL 후보로 export

3. schema v2
   - 기존 v1 wrapper 유지
   - `metadata.runtime` 아래에 backend/model/tool/replay/approval/sandbox evidence 추가

4. reward v2
   - RAG grounding
   - tool report pass/warn/fail
   - replay recovery quality
   - approval readiness
   - sandbox safety

5. pilot 학습 순서
   - 1차: `pm`, `architect`, `manager`
   - 2차: `dev-fe`, `dev-be`, `dev-db`
   - 3차: `qa`, `secops`

## 검증 메모

- `jsonschema==4.23.0` 최소 설치 후 sample validation 실행
- validation script는 `RefResolver` deprecation warning이 있으므로 이후 `referencing` 기반으로 교체 권장

## 산출물

- 변경 소스 압축 파일: `work/dist/step6_learning_currentization_sources.zip`

