# DB 구성

초기 버전은 PostgreSQL 기준입니다.

## 핵심 테이블

- `project`: 사용자 프로젝트
- `agent_catalog`: 역할별 모델/어댑터/엔드포인트 레지스트리
- `orchestration_run`: 한 번의 사용자 요구 실행 단위
- `orchestration_step`: PM/Architect/Dev/QA/SecOps/Manager 단계별 실행 이력
- `orchestration_event`: 이벤트 로그
- `artifact`: 단계별 구조화 산출물

## 운영 팁

- 장기적으로는 `artifact` 를 외부 object storage 와 연결하는 것이 좋습니다.
- `orchestration_event.payload` 에 runner, scan, rag 로그를 누적할 수 있습니다.
- 결과 diff 비교를 위해 `artifact_type` 을 `pm_json`, `arch_json`, `code_patch`, `qa_report`, `secops_report` 등으로 세분화할 수 있습니다.
