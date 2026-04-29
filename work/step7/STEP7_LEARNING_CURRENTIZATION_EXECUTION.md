# Step 7 - Learning 현행화 실행 기반 적용

작성일: 2026-04-29

## 목표

Step 6에서 정의한 다음 단계 작업을 실제 실행 가능한 파일로 구성했다.

대상:

1. `scripts/check_runtime_alignment.py`
2. `scripts/export_runtime_traces.py`
3. schema v2
4. reward v2
5. pilot 학습 순서

## 적용 내용

### 1. Runtime alignment 검사

추가 파일:

- `source/learning/scripts/check_runtime_alignment.py`

검사 대상:

- runtime `agents.yaml`
- runtime router config
- learning adapter registry
- runtime `SchemaValidator.REQUIRED_KEYS`
- learning schema output required keys

검증 결과:

```text
{"ok": true, "checked_agents": 8, "finding_count": 0}
```

### 2. Runtime trace export

추가 파일:

- `source/learning/scripts/export_runtime_traces.py`

기능:

- 운영 DB의 `orchestration_run`, `orchestration_step`, `artifact`, `orchestration_event`, `run_approval`, `run_replay_audit`를 role별 JSONL 후보로 export
- 기존 training sample wrapper 유지
- `metadata.runtime` 아래에 backend/model/tool/replay/approval evidence 포함

예시:

```powershell
python scripts/export_runtime_traces.py --database-url "$env:DATABASE_URL" --out-dir data_runtime_exports/step7 --limit 500
```

### 3. Schema v2

추가 파일:

- `source/learning/scripts/build_schema_v2_samples.py`
- `source/learning/schemas_v2/common-runtime.schema.json`
- `source/learning/schemas_v2/*.schema.json`

핵심:

- 기존 v1 wrapper 유지
- `metadata.runtime` optional evidence 추가
- runtime required key와 schema v2 required key 정렬

### 4. Reward v2

수정 파일:

- `source/learning/rewards/common.py`

추가 reward:

- `runtime_trace_score`
- `tool_report_score`
- `rag_grounding_score`
- `approval_readiness_score`
- `replay_recovery_score`
- `sandbox_safety_score`
- `runtime_reward_v2`

### 5. Pilot 학습 순서

추가 파일:

- `source/learning/configs/pilot_training_order.step7.yaml`

순서:

1. `pm`, `architect`, `manager`
2. `dev-fe`, `dev-be`, `dev-db`
3. `qa`, `secops`

## 검증

실행한 검증:

```powershell
python scripts/build_schema_v2_samples.py
python scripts/check_runtime_alignment.py --schemas schemas_v2 --report reports/runtime_alignment.step7.json
python -m compileall scripts rewards
python scripts/export_runtime_traces.py --help
```

결과:

- schema v2 생성 성공: 8개 role schema + common runtime schema
- alignment 검사 통과: 8개 agent, finding 0
- scripts/rewards compile 통과
- runtime trace export CLI 로드 확인

## 산출물

- `work/dist/step7_learning_currentization_execution_sources.zip`

