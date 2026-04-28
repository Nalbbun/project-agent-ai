# AI Agent Sample JSONL Dataset

이 패키지는 멀티 에이전트 학습용 샘플 데이터 세트입니다.

포함 역할:
- pm
- architect
- dev-fe
- dev-be
- dev-db
- qa
- secops
- manager

구성:
- 각 역할별 `train` / `valid` 샘플 JSONL
- architect는 업로드된 기존 파일 형식에 맞춰 더 많은 수량으로 확장
- synthetic/distilled/human 메타 태그 포함

권장 사용:
1. 역할별 schema validator로 먼저 검증
2. SFT용 train/valid 분리 사용
3. 부족한 도메인은 추가 증강
4. 운영 데이터와 혼합 시 source/version 태그 유지

생성 수량:
- architect: train 320 / valid 80
- 그 외 역할: train 180 / valid 45

추가 포함:
- `schemas/`: 역할별 JSON Schema 검증 파일
- `scripts/validate_samples.py`: 전체 JSONL 일괄 검증 스크립트
- `reports/validation_report.json`: 검증 상세 리포트
- `reports/validation_summary.txt`: 검증 요약

실행 예시:
```bash
cd ai_agent_sample_dataset
python scripts/validate_samples.py
```
