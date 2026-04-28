# work 이력 기반 단계별 분석 및 재정리 (프로젝트 필수 항목 중심)

작성일: 2026-04-28
대상: `work/step1~step4` md 이력 + 현재 `source/runtime` 구조

---

## 1) 단계별 시간순 이력 정리 (핵심 변화만)

### Step 1 — 진단/설계 단계
참고 문서:
- `work/step1/ai_fullstack_source_analysis.md`
- `work/step1/runtime_stabilization_detailed_checklist.md`
- `work/step1/runtime_stabilization_execution_design.md`

핵심:
- 전체 저장소를 `learning`(학습) + `runtime`(운영) 이원 구조로 규정
- 운영 안정화 우선순위(P0~P3) 수립
- Router 단일 경유, Postgres 통일, Queue/Worker, Schema 검증, RAG/Tool 확장 포인트를 “필수 설계”로 정의

의미:
- 이 단계는 코드 구현보다 **운영 관점 설계 기준선**을 확정한 단계

---

### Step 2 — P0/P1 안정화 반영 단계
참고 문서:
- `work/step2/MODIFICATIONS_APPLIED.md`

핵심:
- Router endpoint 단일화 + `agent_role` 기반 라우팅 연결
- Run/Step/Event/Artifact 확장 및 enqueue 중심 실행 구조
- step retry API, schema validator/RAG/tool runner 골격, worker 프로세스 추가
- 프론트에 queue 상태/trace/artifact 노출

의미:
- “동작은 되지만 운영 취약” 상태에서 **기본 운영 가능 상태**로 전환된 분기점

---

### Step 3 — Phase 3 확장(실사용 1차) 단계
참고 문서:
- `work/step3/STAGE_PROGRESS_AND_NEXT_APPLY.md`
- `work/step4/PHASE3_COMPLETE_AND_PHASE4_READY.md`

핵심:
- Project Knowledge + 간이 RAG를 실제 조회 흐름으로 연결
- Tool runner가 workspace materialize + 리포트 생성까지 수행
- 이후 Qdrant vector store, reindex API, 실행형 runner(build/test/lint/type/scan)까지 확장

의미:
- Stub 중심 구조에서 **실행 가능한 확장 기능(RAG/Runner)** 으로 진입

---

### Step 4 — 운영 고도화(1~5차) 단계
참고 문서:
- `work/step4/PHASE4_PROGRESS_APPLIED.md`
- `work/step4/PHASE4_SECOND_PROGRESS_APPLIED.md`
- `work/step4/PHASE4_THIRD_PROGRESS_APPLIED.md`
- `work/step4/PHASE4_FOURTH_PROGRESS_APPLIED.md`
- `work/step4/PHASE4_FIFTH_PROGRESS_APPLIED.md`

핵심(누적):
1. Auth/RBAC + Approval(단계 승인) + Worker 관측성 + Retry/Backoff
2. SSE 실시간 스트리밍(run/dashboard/workers/approval inbox)
3. Stale reclaim / dead-letter / replay 세분화 + replay audit/diff
4. Project membership + invite/request workflow
5. Approval SLA/alert + dashboard 통합 통계
6. Sandbox 실행 레이어 + sandbox image 분리 + CI/CD 워크플로

의미:
- 단순 오케스트레이터를 넘어 **운영 콘솔형 멀티에이전트 플랫폼** 수준으로 발전

---

## 2) 현재 프로젝트에 “실제로 필요한 항목” 재정리

아래는 이력 전체를 다시 정리해, 현재 프로젝트 유지/고도화에 **필수(Must)** 인 것만 추린 목록입니다.

### A. 반드시 유지해야 하는 기반 (Must Keep)
1. **Router 강제 경유 + 역할 라우팅**
   - 이유: 모델/LoRA 교체와 장애 우회(fallback)를 운영 중 무중단에 가깝게 수행 가능
2. **Queue/Worker + Retry/Backoff + Dead-letter**
   - 이유: 장시간 다단계 run 안정성의 핵심
3. **Approval + RBAC + Project Membership**
   - 이유: 운영 환경에서 사람 승인/권한 경계 없이는 실제 사용 어려움
4. **Artifact/Event/Audit(Replay 포함) 추적 체계**
   - 이유: 장애 원인 분석, 재현, 규정 준수(감사)
5. **RAG + Project Knowledge + Reindex**
   - 이유: 도메인 문맥 없는 생성 품질 한계 보완
6. **Runner Sandbox 격리**
   - 이유: 코드/명령 실행형 워크플로의 보안 최소선

### B. 지금 당장 고도화 우선순위 (Must Improve Next)
1. **테스트 신뢰성 복구**
   - 현재 환경 제약(의존성/네트워크)과 무관하게, CI에서 backend 테스트/정적검사 일관 실행 보장 필요
2. **Replay 정책 단순화 + API 의미 일치화**
   - `/retry`, `/resume`, `/dead-letter/replay` 역할을 사용자 관점에서 명확히 구분
3. **관측성 표준화(OpenTelemetry/메트릭)**
   - run/step latency, queue wait, approval lead time, dead-letter rate를 표준 지표화
4. **Sandbox 운영 보안 정책 강화**
   - 이미지 서명/Provenance, 네트워크 정책, 리소스 제한 프로파일 확정
5. **Approval/Membership 알림 채널 연동**
   - 이메일/슬랙/웹훅 없으면 SLA 기능의 실효성 제한

### C. 선택적/후순위 항목 (Should Later)
1. 완전 병렬 DAG 실행 고도화 (현재는 순차 중심)
2. field-level replay diff 고도화
3. 임베딩 프로바이더 다중화 최적화

---

## 3) 현재 소스 기준 권장 “재정리된 실행 로드맵”

### Phase A (1~2주): 안정 운영선 고정
- API 의미 정리: retry/resume/replay
- CI 기준선 고정: backend test + lint + type 최소셋
- 운영 대시보드 핵심 지표 1차 확정

### Phase B (2~4주): 운영 신뢰성 강화
- stale/dead-letter 자동 복구 정책 튜닝
- approval SLA 알림 채널 연결
- sandbox 보안 프로파일/이미지 배포 정책 고정

### Phase C (4주+): 품질/생산성 확장
- RAG 품질(임베딩/리랭크/인용) 고도화
- runner 결과의 구조화 리포트(SARIF/JUnit) 표준화
- project 규모 확대 대비 멀티 워커 운영 튜닝

---

## 4) 결론

`work` 이력은 “설계 → 안정화 → 확장 → 운영 고도화”로 매우 일관된 진화 경로를 보여줍니다.

현재 프로젝트에서 중요한 것은 기능 추가 자체보다,
- 이미 확보한 운영 핵심축(router, queue, approval, replay, rbac, sandbox)을 **신뢰성 있게 고정**하고
- 테스트/관측/보안 정책을 **운영 표준으로 수렴**시키는 것입니다.

즉, 다음 단계의 핵심은 “더 많은 기능”이 아니라
**기존 기능의 운영 품질 고정(신뢰성/가시성/보안성)** 입니다.
