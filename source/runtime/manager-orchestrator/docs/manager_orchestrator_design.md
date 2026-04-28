# Manager / Orchestrator 설계 요약

## 왜 별도 운영 패키지인가

학습 패키지와 운영 패키지를 분리해야 다음 장점이 있습니다.

- 학습 자산(JSONL / Schema / Reward / Adapter Registry)와 런타임 API를 독립 배포 가능
- 운영에서 필요한 DB, 이벤트 로그, 재실행, 사용자 프로젝트 개념을 런타임에 집중 가능
- 모델 교체 없이 Manager 로직과 UI를 빠르게 변경 가능

## 런타임 책임

### Manager / Orchestrator
- 사용자 요구 수신
- 실행 단계 생성
- 현재 상태를 바탕으로 다음 agent 호출
- 실패/보류 상태 기록
- 최종 결과 병합

### Agent Router
- role → endpoint/model/adapter 매핑
- OpenAI-compatible API 호출
- simulation 모드 지원

### Persistence
- 프로젝트
- 실행 run
- step
- event log
- artifact
- prompt template

## 기본 Stage

1. manager-plan
2. pm
3. architect
4. dev-fe
5. dev-be
6. dev-db
7. qa
8. secops
9. manager-merge

## 향후 확장 포인트

- RAG connector
- sandbox / build runner
- lint / type check / SAST runner
- retry 정책 세분화
- human approval gate
- artifact diff viewer
