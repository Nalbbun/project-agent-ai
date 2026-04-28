# vLLM Serving

이 디렉토리는 역할별 LoRA를 `--lora-modules`로 등록한 vLLM 백엔드와, 그 위에서 role 기반 요청을 분기하는 FastAPI 라우터를 함께 운용하는 구조를 가정합니다.

## 구성 요소
- `../../configs/vllm_request_router.local.yaml`: role → backend → target_model 매핑
- `../../router_service/`: FastAPI 기반 OpenAI 호환 프록시
- `docker-compose.yml`: 역할군별 vLLM 서버 예시

## 권장 요청 흐름
1. 클라이언트는 라우터에 `/v1/chat/completions` 요청
2. 본문 `extra_body.agent_role` 또는 `metadata.agent_role`에 역할 지정
3. 라우터가 YAML 설정을 읽어 적절한 backend와 target model 선택
4. 실패 시 fallback 순서로 재시도

## 라우터 로컬 실행
```bash
cd router_service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=..
export ROUTER_CONFIG_PATH=../configs/vllm_request_router.local.yaml
uvicorn router_service.app.main:app --host 0.0.0.0 --port 8080
```

## 라우터 Docker 빌드
```bash
docker build -f router_service/Dockerfile -t multi-agent-router:local .
docker run --rm -p 8080:8080 \
  -e ROUTER_CONFIG_PATH=/app/configs/vllm_request_router.local.yaml \
  -e VLLM_ROUTER_API_KEY=change-me \
  multi-agent-router:local
```
