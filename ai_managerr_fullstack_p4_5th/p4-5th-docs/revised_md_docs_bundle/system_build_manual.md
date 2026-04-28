# 시스템 구축 메뉴얼

## 1. 목적

본 문서는 AI Multi-Agent Orchestrator Platform을 실제 개발/검증/운영 환경에 구축하기 위한 절차를 정리합니다.

---

## 2. 전체 구성

### 2.1 Control Plane
- manager-orchestrator backend
- manager-orchestrator frontend
- worker
- approval / membership / alert

### 2.2 Inference Plane
- router service
- general model serving
- coder model serving
- bilingual model serving

### 2.3 Data Plane
- PostgreSQL
- Qdrant
- artifact storage

### 2.4 Tool Plane
- sandbox runner
- build / test / lint / type
- SAST / dependency scan

---

## 3. 권장 환경

### 기본
- Ubuntu 또는 Linux 서버
- Docker / Docker Compose
- PostgreSQL
- Qdrant
- Python 3.11+
- Node.js 20+
- Git

### 선택
- Ollama: PoC
- vLLM: 운영
- GPU: 운영 추론용
- Reverse Proxy / TLS: 운영 환경 권장

---

## 4. 사전 준비 항목

### 필수 설정값
- DATABASE_URL
- ROUTER_BASE_URL
- VECTOR_DB_URL
- VECTOR_EMBEDDING_PROVIDER
- AUTH_SECRET_KEY
- APPROVAL_POLICY
- APPROVAL_SLA_HOURS
- RUNNER_SANDBOX_MODE
- RUNNER_SANDBOX_DOCKER_IMAGE

### 준비 자료
- 역할별 모델/LoRA 경로
- agent registry
- router config
- sandbox image config
- seed user / role 정책

---

## 5. 구축 절차

### Step 1. 소스 배치
- 프로젝트 루트에 전체 소스 배치
- `runtime/manager-orchestrator`
- `runtime/work_proxy_deploy`
- `learning`

### Step 2. 환경 변수 작성
`.env.example`을 기준으로 `.env` 생성

### Step 3. 데이터베이스 준비
- PostgreSQL 기동
- init schema 적용
- seed 데이터 반영
- health check 확인

### Step 4. Vector DB 준비
- Qdrant 기동
- collection 준비
- ready 상태 확인

### Step 5. Router 준비
- role → endpoint / model / adapter 매핑
- health / ready / routes 확인

### Step 6. Sandbox 이미지 준비
- python / node / java runner image build
- 운영 레지스트리 push 필요 시 반영
- CI/CD workflow 확인

### Step 7. Backend 기동
- backend-api
- backend-worker
- health live/ready 확인

### Step 8. Frontend 기동
- dependency 설치
- build
- dashboard 접속 확인

---

## 6. 권장 실행 순서

1. postgres
2. qdrant
3. router
4. backend-api
5. backend-worker
6. frontend

---

## 7. 모델 배치 전략

### PoC
- Ollama 역할별 모델 개별 등록
- Manager가 앱 레벨에서 라우팅

### 운영
- vLLM general
- vLLM coder
- vLLM bilingual
- Router에서 role 별 매핑
- multi-LoRA 구성

---

## 8. RAG 구축 절차

### 8.1 지식 소스 등록
- 프로젝트 knowledge 업로드
- chunk / embedding / 색인

### 8.2 artifact 색인
- step-output
- tool-report
- rag-context
- replay-related artifact

### 8.3 retrieval 전략
- vector + lexical hybrid
- role별 retrieval policy
- 필요 시 reindex

---

## 9. Runner 구축 절차

### 기능
- build
- test
- lint
- type
- scan

### sandbox 정책
- local / docker 모드
- network none 기본
- no-new-privileges
- read-only rootfs
- tmpfs 사용
- cpu / memory / pids 제한

---

## 10. 운영 기능 설정

### 인증/권한
- admin
- operator
- reviewer
- viewer

### 프로젝트 권한
- owner
- editor
- reviewer
- viewer

### 승인 정책
- single-stage
- multi-stage
- SLA / overdue / due-soon

---

## 11. 점검 엔드포인트

- `/health/live`
- `/health/ready`
- `/api/dashboard/stream`
- `/api/workers/stream`
- `/api/approvals/inbox`
- `/api/approvals/inbox/stream`

---

## 12. 운영 점검 체크리스트

- DB 연결 정상
- Router 정상
- Qdrant ready
- Worker heartbeat 존재
- Approval inbox 정상 조회
- Dashboard live stream 정상
- Replay history 기록 정상
- Alerts 생성 정상
- Sandbox image build 정상

---

## 13. 장애 대응

### DB 연결 문제
- DATABASE_URL
- schema/init
- postgres 상태

### Router 문제
- ROUTER_BASE_URL
- route config
- upstream model server 상태

### RAG 문제
- Qdrant health
- embedding provider
- reindex 상태

### Runner 문제
- docker 권한
- sandbox image
- timeout
- tool-report 내용

### Approval 정지
- pending approval 확인
- SLA 초과 여부
- reviewer/admin 권한 확인

---

## 14. 결론

운영 환경에서는 단순 추론 서버보다,
**Router + RAG + Runner + Approval + Alert + Observability**가 함께 안정적으로 구성되어야 합니다.
