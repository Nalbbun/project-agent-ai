# Ollama 배포 가이드

## 기본 방향
이 패키지의 기본 모델 축은 Qwen / EXAONE입니다. Ollama 공식 import 문서는 Safetensors 어댑터 import를 Llama / Mistral / Gemma 계열 중심으로 안내하고 있으므로, 이 패키지의 Ollama 경로는 **역할별 LoRA를 미리 merge한 뒤 GGUF로 변환한 결과물**을 등록하는 기준으로 잡았습니다.

## 준비 경로
역할별 merged GGUF를 아래 경로에 준비합니다.

- `/srv/llm/merged/ollama/pm-agent.gguf`
- `/srv/llm/merged/ollama/architect-agent.gguf`
- `/srv/llm/merged/ollama/dev-fe-agent.gguf`
- `/srv/llm/merged/ollama/dev-be-agent.gguf`
- `/srv/llm/merged/ollama/dev-db-agent.gguf`
- `/srv/llm/merged/ollama/qa-agent.gguf`
- `/srv/llm/merged/ollama/secops-agent.gguf`
- `/srv/llm/merged/ollama/manager-agent.gguf`

## 등록
```bash
cd serving/ollama
bash register_models.sh
```

## 참고
Ollama는 GGUF 기반 모델과 GGUF 어댑터 import를 지원합니다. Qwen / EXAONE LoRA를 직접 붙이는 경로보다, merge 후 GGUF로 내보낸 역할별 모델을 등록하는 쪽이 PoC 운영에서 더 안전합니다.
