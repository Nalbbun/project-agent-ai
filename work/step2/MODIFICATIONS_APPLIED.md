# Runtime Stabilization Applied Summary

이 반영본은 `runtime_stabilization_execution_design.md` 기준으로 업로드된 소스에 다음 항목을 실제 반영한 버전입니다.

## 반영 범위

### 1. Manager-Orchestrator 런타임
- Router 단일 endpoint 기반 agent registry 전환
- `agent_role` 기반 라우팅 요청 구조 반영
- PostgreSQL 전용 설정으로 정리
- Run/Step/Event/Artifact 모델 확장
- queue 상태, backend/model trace 저장
- `execute` API를 enqueue 중심 구조로 보완
- step 단위 retry API 추가
- schema validator / RAG stub / tool runner stub 추가
- worker 프로세스(`app.workers.run_worker`) 추가
- artifact 조회 API 추가
- 프론트에서 queue 상태, backend/model, artifact, step retry 표시

### 2. Router Service
- top-level `agent_role` + `extra_body.agent_role` + `metadata.agent_role` 모두 지원
- backend별 retry 반영
- 응답 header에 role/backend/model trace 추가
- config validation 강화

### 3. Compose / Config
- `manager-orchestrator/docker-compose.yml` 에 `router`, `backend-api`, `backend-worker` 분리 반영
- postgres healthcheck 추가
- `.env.example` 확장
- `agents.yaml` 을 router 기반으로 재작성

### 4. Learning 패키지 보완
- `learning/scripts/selfcheck.sh` 경로 수정
- `learning/configs/execution.local.yaml` 샘플 JSONL 경로 수정
- `backend/requirements.txt` 의 `psycopg[binary]` 버전을 현재 설치 가능한 버전으로 조정

## 검증
- backend Python compileall 통과
- router_service Python compileall 통과
- backend 핵심 테스트 7건 통과
  - pipeline 구조
  - JSON 파싱
  - schema validator

## 주의
- RAG / Build Runner / Security Runner 는 stub 인터페이스까지 반영됨
- 실제 벡터 DB, sandbox, build/test/scan 실행기는 아직 연결 전 단계
- 프론트엔드는 타입/구조 기준으로 반영했으며, npm build는 별도 환경에서 확인 필요
