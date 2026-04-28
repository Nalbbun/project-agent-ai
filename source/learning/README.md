# AI Multi-Agent Next Work Package

이 패키지는 다음 4개 작업의 실무형 초안에 더해, **실행 환경용 로컬 경로/명령값**까지 채운 작업본입니다.

1. JSON Schema 8종 작성
2. reward Python 코드 골격 작성
3. TRL/PEFT 학습 스크립트 생성
4. vLLM/Ollama 배포 매니페스트 작성

## 추가 반영 사항
- `configs/adapter_registry.local.yaml`: 실제 서버 경로 기준 베이스 모델 / LoRA 경로
- `configs/execution.local.yaml`: repo self-check 및 Dev 역할별 build/test/lint 예시 명령
- `rewards/dev_db.py`: dev-db 전용 reward 분리
- `serving/vllm/docker-compose.yml`: 로컬 base + LoRA 정적 등록 반영
- `serving/ollama/register_models.sh`: merged GGUF 기준 역할별 모델 등록

## 디렉토리 구조

- `schemas/`: 역할별 JSON Schema 8종
- `rewards/`: 공통/역할별 reward 코드 골격
- `train/`: SFT / GRPO / 유틸리티 스크립트
- `serving/vllm/`: vLLM 배포용 docker-compose 및 설정
- `serving/ollama/`: Ollama Modelfile 및 실행 스크립트
- `serving/k8s/`: Kubernetes 예시 매니페스트
- `configs/`: 어댑터/모델/라우팅/실행 명령 설정 예시
- `data_examples/`: 역할별 JSONL 샘플

## 권장 순서

1. `configs/adapter_registry.local.yaml` 경로 점검
2. `configs/execution.local.yaml` 기준으로 self-check 수행
3. `train/validate_jsonl.py`로 학습 데이터 검증
4. `train/sft_*.sh`로 역할별 SFT 진행
5. `serving/vllm/` 또는 `serving/ollama/` 기준으로 PoC/운영 배포

## 주의

- 본 작업본은 **단일 Linux GPU 서버**를 기준으로 `/srv/llm/...` 경로를 채워 두었습니다.
- 실제 운영 환경의 경로, GPU 개수, 평가 러너 위치에 따라 `configs/execution.local.yaml`과 compose volume만 조정하면 됩니다.
- GRPO reward는 자동 채점 툴(build/test/lint/scan)와 연결해야 의미가 있습니다.
