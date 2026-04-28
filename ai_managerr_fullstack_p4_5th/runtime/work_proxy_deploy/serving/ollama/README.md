# Ollama Serving

이 디렉토리는 GGUF 생성 후 역할별 모델을 Ollama에 등록하는 흐름을 다룹니다.

## 포함 파일
- `register_models.sh`: GGUF 존재 여부를 확인하고 Modelfile 생성 후 `ollama create` 실행
- `../../configs/ollama_registration.local.yaml`: 역할별 모델명, GGUF 파일명, 시스템 프롬프트, 파라미터 정의
- `../../scripts/deploy_merge_convert_and_register_ollama.sh`: LoRA 병합 → GGUF 변환 → Ollama 등록 통합 실행

## 1. GGUF만 이미 있는 경우 등록
```bash
export REGISTRATION_CONFIG_PATH=/srv/project/configs/ollama_registration.local.yaml
bash serving/ollama/register_models.sh
```

## 2. LoRA부터 한 번에 처리
```bash
export BASE_MODEL_ROOT=/srv/llm/base
export ADAPTER_ROOT=/srv/llm/adapters
export MERGED_HF_ROOT=/srv/llm/merged/hf
export GGUF_ROOT=/srv/llm/merged/ollama
export LLAMACPP_ROOT=/opt/llama.cpp
export ROLES=architect,dev-fe,dev-be,dev-db,qa,secops
bash scripts/deploy_merge_convert_and_register_ollama.sh
```

## DRY RUN
```bash
DRY_RUN=1 bash scripts/deploy_merge_convert_and_register_ollama.sh
```
