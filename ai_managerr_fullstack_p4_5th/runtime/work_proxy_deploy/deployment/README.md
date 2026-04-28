# Integrated Docker Compose

이 구성은 다음을 한 번에 올리는 통합 예시입니다.

- `vllm-general`: Qwen2.5-3B + `architect/qa/secops` LoRA
- `vllm-coder`: Qwen2.5-Coder-1.5B + `dev-fe/dev-be/dev-db` LoRA
- `vllm-exaone`: EXAONE 3.5 2.4B + `pm/manager` LoRA
- `router`: FastAPI role router
- `ollama`(optional profile): GGUF 모델 서빙
- `ollama-bootstrap`(optional profile): GGUF 생성/등록 자동화

## 빠른 시작

```bash
cp .env.compose.example .env
# 필요 시 값 수정

docker compose -f docker-compose.integrated.yml up -d --build
```

라우터는 `http://127.0.0.1:${ROUTER_HOST_PORT:-8080}` 로 열립니다.

## Ollama까지 함께 실행

```bash
docker compose -f docker-compose.integrated.yml --profile ollama up -d --build
```

`ollama-bootstrap`은 one-shot 작업입니다. `DRY_RUN=1`이면 실제 등록 전 변환/등록 계획만 확인합니다.

## 요청 예시

```bash
curl http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_ROUTER_TOKEN_IF_SET' \
  -d '{
    "model": "router-auto",
    "messages": [{"role": "user", "content": "결재 시스템 백엔드 API를 설계해줘"}],
    "extra_body": {"agent_role": "architect"}
  }'
```

## 전제 조건

- 호스트에 `/srv/llm/base` 와 `/srv/llm/adapters` 가 준비되어 있어야 합니다.
- vLLM 공식 Docker 이미지는 `vllm/vllm-openai` 이며 OpenAI 호환 서버와 LoRA 옵션을 지원합니다.
- Ollama 공식 Docker 이미지는 `ollama/ollama` 입니다.
- `ollama-bootstrap`을 실제로 사용할 경우 호스트의 `llama.cpp` 경로가 `LLAMACPP_ROOT`로 마운트되어 있어야 합니다.

## 주의

- `deploy.resources...devices` 는 NVIDIA GPU 예약 예시입니다. Compose 구현과 런타임 환경에 따라 `docker compose` 버전 또는 NVIDIA Container Toolkit 설정이 필요합니다.
- `router` 는 기본적으로 vLLM 백엔드만 사용합니다. Ollama를 라우터 백엔드로 넣으려면 `configs/vllm_request_router.local.yaml`에 Ollama OpenAI 호환 프록시 또는 별도 adapter를 추가하세요.
