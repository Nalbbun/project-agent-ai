# 사용자 메뉴얼

## 1. 문서 목적

본 문서는 운영자, 리뷰어, 프로젝트 담당자가 AI Multi-Agent Orchestrator Platform을 사용하는 방법을 설명합니다.

---

## 2. 로그인

1. 로그인 화면 접속
2. 아이디와 비밀번호 입력
3. 권한에 따라 사용 가능한 메뉴 확인

### 권한 유형
- Admin
- Operator
- Reviewer
- Viewer

---

## 3. 주요 메뉴

- Dashboard
- Projects
- Runs
- Workers
- Approvals
- Alerts

---

## 4. 프로젝트 생성 및 관리

### 프로젝트 생성
1. Projects 메뉴 이동
2. 신규 프로젝트 생성
3. 프로젝트 이름 / 설명 입력
4. 생성 시 생성자는 owner 권한 자동 부여

### 프로젝트 관리
- summary 확인
- knowledge 등록/삭제/reindex
- membership 조회
- invite / request 처리

---

## 5. 프로젝트 지식 등록

1. 프로젝트 진입
2. Knowledge 등록
3. 문서 내용 입력 또는 업로드
4. 저장 후 index / reindex 수행

지식 문서는 이후 RAG 검색에 사용됩니다.

---

## 6. 멤버십 관리

### invite
- owner/admin이 사용자 초대 가능

### request
- 사용자가 접근 요청 가능

### 처리
- owner/reviewer/admin이 승인/반려
- 승인 시 membership 자동 생성 또는 갱신

---

## 7. Run 생성

1. Runs 메뉴 이동
2. 프로젝트 선택
3. 사용자 요구 입력
4. Run 생성

Manager가 자동으로 실행 계획을 구성하고 각 역할 에이전트를 순서대로 호출합니다.

---

## 8. Run 실행 흐름

일반 흐름:
1. PM
2. Architect
3. Dev-FE / Dev-BE / Dev-DB
4. QA
5. SecOps
6. Manager merge

### 상태 예시
- pending
- queued
- running
- retry_scheduled
- waiting_approval
- failed
- completed
- dead_lettered

---

## 9. Run 상세 화면

Run 상세에서 확인 가능한 정보:
- 현재 단계
- step 상태
- event 로그
- artifact 목록
- model / backend trace
- replay history
- replay diff

---

## 10. Approval Inbox 사용

Approvals 메뉴에서 확인 가능:
- actionable approval
- queued approval
- overdue approval
- due-soon approval
- phase / stage 정보

가능한 작업:
- approve
- reject
- 필터링
- project/phase 기준 확인

---

## 11. Dashboard 사용

Dashboard에서 확인 가능:
- 실행 중 run 수
- approval 대기 수
- overdue approval
- dead-letter 수
- invite / request 통계
- project hotspot

실시간 스트리밍으로 최신 상태가 반영됩니다.

---

## 12. Workers 화면

Workers 메뉴에서 확인 가능:
- 활성 worker
- heartbeat
- 현재 run
- 현재 phase
- stale 상태

실시간 스트리밍으로 현황 확인이 가능합니다.

---

## 13. Replay / Dead-letter 복구

Run이 dead-lettered 되면 replay 기능을 사용할 수 있습니다.

### 지원 모드
- requeue
- from-last-failed
- from-phase
- full-reset

복구 후에는 replay history 와 diff를 확인할 수 있습니다.

---

## 14. Alerts 확인

Alerts 또는 Dashboard에서 확인 가능:
- approval overdue
- approval due-soon
- 운영 경고 항목

SLA 기준에 따라 경고가 생성됩니다.

---

## 15. Artifact 확인

Artifact 종류:
- raw-llm-response
- normalized-output
- tool-report
- rag-context
- replay-diff

운영자는 preview를 통해 상세 내용을 바로 확인할 수 있습니다.

---

## 16. 운영 팁

- approval overdue를 우선 처리하십시오.
- dead-letter는 replay diff를 먼저 확인하십시오.
- knowledge reindex 후 RAG 품질을 점검하십시오.
- sandbox runner 실패 시 tool-report부터 확인하십시오.

---

## 17. 결론

본 시스템은 단순 대화형 AI가 아니라,
**프로젝트 단위 협업, 승인, 복구, 관측, 재실행까지 가능한 운영형 멀티 에이전트 플랫폼**입니다.
