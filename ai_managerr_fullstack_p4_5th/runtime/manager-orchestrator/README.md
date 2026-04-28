# Manager / Orchestrator Runtime

## 스택

- Backend: FastAPI + SQLModel
- Frontend: React + Vite + TypeScript
- DB: PostgreSQL
- Agent protocol: OpenAI-compatible Chat Completions

## 역할 구조

- `manager`: orchestration / merge
- `pm`: requirements structuring
- `architect`: architecture design
- `dev-fe`: frontend planning / generation
- `dev-be`: backend planning / generation
- `dev-db`: schema / migration planning
- `qa`: validation
- `secops`: security review

## 핵심 API

- `GET /health`
- `GET /api/dashboard`
- `GET /api/agents`
- `GET /api/projects`
- `POST /api/projects`
- `GET /api/runs`
- `POST /api/runs`
- `GET /api/runs/{run_id}`
- `POST /api/runs/{run_id}/execute`
- `POST /api/runs/{run_id}/retry`
- `GET /api/runs/{run_id}/events`

## 실행 팁

1. `.env.example` 를 `.env` 로 복사
2. 초기 테스트는 `SIMULATION_MODE=true`
3. 실제 연결 시 `config/agents.yaml` 를 vLLM/Ollama endpoint 기준으로 수정
4. 이후 RAG / Tool Runner / Artifact Storage 를 단계적으로 붙임
