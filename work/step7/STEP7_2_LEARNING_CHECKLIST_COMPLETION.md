# Step 7-2 - Learning 체크리스트 보완 완료

작성일: 2026-04-29

## 목표

Step 6/7에서 정의한 learning 현행화 체크리스트를 실제 산출물 기준으로 재점검하고, 미완료 항목을 보완했다.

## 체크리스트 결과

- [x] `scripts/export_runtime_traces.py` 작성
  - Step 7에서 작성 완료
  - 운영 DB trace를 role별 JSONL 후보로 export

- [x] `schemas_v2/` 또는 schema `metadata.runtime` 확장안 작성
  - Step 7에서 `schemas_v2/` 생성
  - Step 7-2에서 metadata `$ref` 충돌을 수정하고 재생성

- [x] `rewards/common.py`에 runtime reward 함수 추가
  - `runtime_trace_score`
  - `tool_report_score`
  - `rag_grounding_score`
  - `approval_readiness_score`
  - `replay_recovery_score`
  - `sandbox_safety_score`
  - `runtime_reward_v2`

- [x] `scripts/check_runtime_alignment.py` 작성
  - v2 schema 기준 검사 통과
  - 결과: `{"ok": true, "checked_agents": 8, "finding_count": 0}`

- [x] `serving/k8s/router-configmap.yaml`을 runtime router config 수준으로 갱신
  - runtime router의 `router`, `backends`, `routes`, fallback, generation, policy 구조 반영
  - embedded YAML parse 확인
  - routes: `architect`, `dev-be`, `dev-db`, `dev-fe`, `manager`, `pm`, `qa`, `secops`

- [x] runtime export sample 20건 생성
  - `source/learning/data_runtime_exports/step7_2_sample/`
  - 총 20건
  - role 분포:
    - pm: 3
    - architect: 3
    - dev-fe: 3
    - dev-be: 3
    - dev-db: 2
    - qa: 2
    - secops: 2
    - manager: 2

- [x] v1 sample + runtime export sample 통합 검증
  - report: `source/learning/reports/v1_runtime_validation.step7-2.json`
  - 결과: `{"all_valid": true, "passed": 1995, "failed": 0, "files": 24}`

- [x] role별 eval report 생성
  - report: `source/learning/reports/role_eval.step7-2.json`
  - 총 runtime sample: 20
  - 모든 role schema pass rate: 1.0

## 추가/수정 파일

- `source/learning/serving/k8s/router-configmap.yaml`
- `source/learning/scripts/generate_runtime_export_samples.py`
- `source/learning/scripts/validate_v1_and_runtime_samples.py`
- `source/learning/scripts/generate_role_eval_report.py`
- `source/learning/scripts/build_schema_v2_samples.py`
- `source/learning/scripts/generate_role_eval_report.py`
- `source/learning/scripts/validate_v1_and_runtime_samples.py`
- `source/learning/schemas_v2/*.schema.json`
- `source/learning/data_runtime_exports/step7_2_sample/*`
- `source/learning/reports/v1_runtime_validation.step7-2.json`
- `source/learning/reports/role_eval.step7-2.json`

## 검증 명령

```powershell
python scripts/generate_runtime_export_samples.py --count 20
python scripts/build_schema_v2_samples.py
python scripts/check_runtime_alignment.py --schemas schemas_v2 --report reports/runtime_alignment.step7.json
python scripts/validate_v1_and_runtime_samples.py
python scripts/generate_role_eval_report.py
python -m compileall scripts rewards
```

## 산출물

- `work/dist/step7_2_learning_checklist_completion_sources.zip`

