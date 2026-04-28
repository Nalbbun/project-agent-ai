# FastAPI Role Router

이 서비스는 `configs/vllm_request_router.local.yaml`을 읽어 OpenAI 호환 요청을 role 기준으로 백엔드(vLLM/Ollama OpenAI 호환 엔드포인트 등)로 프록시합니다.

## 지원 엔드포인트
- `GET /health`
- `GET /router/routes`
- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/completions`
- `POST /v1/responses`

## role 추출 우선순위
기본 설정 기준:
1. `extra_body.agent_role`
2. `extra_body.role`
3. `metadata.agent_role`
4. `metadata.role`
5. `X-Agent-Role` 헤더

## 로컬 실행
```bash
cd router_service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=..
export ROUTER_CONFIG_PATH=../configs/vllm_request_router.local.yaml
uvicorn router_service.app.main:app --host 0.0.0.0 --port 8080
```

## 요청 예시
```bash
curl http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "router-auto",
    "messages": [{"role": "user", "content": "승인 시스템 API를 설계해줘"}],
    "extra_body": {"agent_role": "architect"}
  }'
```

## 참고
- 라우터 전용 필드(`agent_role`, `task_type`)는 설정에 따라 백엔드 전달 전에 제거됩니다.
- 요청에 `stream=true`가 있으면 스트리밍 응답을 그대로 중계합니다.


## Docker Compose 통합 실행
```bash
cp .env.compose.example .env
docker compose -f docker-compose.integrated.yml up -d --build
```

Ollama까지 함께 쓰려면:
```bash
docker compose -f docker-compose.integrated.yml --profile ollama up -d --build
```
