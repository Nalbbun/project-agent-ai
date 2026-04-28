# vLLM 배포 가이드

## 기본 방향
- 일반 역할(Architect / QA / SecOps)은 `qwen-general`
- 개발 역할(Dev-FE / Dev-BE / Dev-DB)은 `qwen-coder`
- 업무형 역할(PM / Manager)은 `exaone-workflow`
- LoRA는 서버 시작 시 정적으로 등록

## 로컬 경로 기준
- 베이스 모델: `/srv/llm/base/...`
- LoRA 어댑터: `/srv/llm/adapters/...`
- Hugging Face 캐시: `/srv/llm/cache/huggingface`

## 기동
```bash
cp .env.example .env
docker compose up -d
```

## OpenAI 호환 호출 예시
서버는 `/v1/chat/completions`를 제공하며, `model` 필드에는 LoRA 이름을 직접 넣으면 됩니다.

### Architect
```json
{
  "model": "architect-lora",
  "messages": [
    {"role": "system", "content": "Return structured JSON only."},
    {"role": "user", "content": "사내 결재 시스템 아키텍처를 설계해줘"}
  ]
}
```

### Dev-BE
```json
{
  "model": "dev-be-lora",
  "messages": [
    {"role": "system", "content": "Return structured JSON only."},
    {"role": "user", "content": "결재 생성 API를 만들어줘"}
  ]
}
```

## 참고
- vLLM은 서버 시작 시 `--lora-modules`로 LoRA를 정적 등록할 수 있습니다. 또한 런타임 LoRA API와 플러그인도 제공하지만, 공식 문서상 런타임 업데이트는 보안 리스크가 있어 격리된 신뢰 환경에서만 권장됩니다.
- EXAONE 3.5 2.4B Instruct는 영어·한국어 bilingual 32K 모델이며, Hugging Face 모델 카드 기준 `transformers` 4.43+ 사용을 권장합니다.
