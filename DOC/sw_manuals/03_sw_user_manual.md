# SW 사용자 매뉴얼

## 1. 접속

브라우저에서 접속한다.

```text
http://localhost:5174
```

로그인 화면이 보이지 않으면 다음 주소로 직접 접속한다.

```text
http://localhost:5174/login
```

## 2. 로그인

관리자에게 받은 계정으로 로그인한다.

초기 테스트 계정:

- `admin / admin1234!`
- `operator / operator1234!`
- `reviewer / reviewer1234!`
- `viewer / viewer1234!`

운영 환경에서는 초기 비밀번호를 그대로 사용하지 않는다.

## 3. 화면 메뉴

### Dashboard

전체 상태를 확인한다.

확인 가능 항목:

- Projects
- Runs
- Running
- Need Approval
- Workers
- Dead Letter
- Foundation Guard
- Approval Alerts
- Project Hotspots
- Latest Runs

### Projects

프로젝트, 멤버, 지식 문서를 관리한다.

주요 기능:

- 프로젝트 생성
- 프로젝트 선택
- Knowledge 등록/삭제
- Reindex Knowledge
- 멤버 추가/제거
- 초대 생성
- 접근 요청 승인/반려

### Runs

AI multi-agent 작업을 생성하고 실행한다.

주요 기능:

- Run 생성
- Run 실행
- Run 상세 보기
- 실패 Run retry/resume
- Step별 결과 확인

### Agents

등록된 agent 목록을 확인한다.

확인 항목:

- code
- role
- router role
- model
- adapter
- active 여부

### Workers

worker 상태를 확인한다.

확인 항목:

- worker id
- status
- current run
- current step
- last seen

운영자 권한이 있으면 maintenance 실행이 가능하다.

### Approvals

승인 대기함이다.

확인 항목:

- Run title
- Project
- Phase
- Required role
- Due time
- Overdue / due soon

## 4. 기본 사용 흐름

### 4.1 프로젝트 생성

1. Projects 메뉴로 이동
2. Create Project에 이름과 설명 입력
3. 생성된 프로젝트 선택

### 4.2 프로젝트 지식 등록

1. Projects 메뉴에서 프로젝트 선택
2. Knowledge 섹션에 title/content 입력
3. 저장
4. Reindex Knowledge 클릭

지식 문서는 이후 run 생성 시 RAG context로 활용된다.

### 4.3 Run 생성

1. Runs 메뉴로 이동
2. Project 선택
3. Execution mode는 `background` 선택
4. Title 입력
5. User request 입력
6. Create Run 실행

User request 예:

```text
고객 문의 티켓을 등록하고 상태별로 조회할 수 있는 SaaS 기능을 설계해줘.
Frontend, Backend, DB, QA, SecOps까지 단계별 산출물을 만들어줘.
```

### 4.4 Run 실행

1. 생성된 Run 상세 화면으로 이동
2. Execute 클릭
3. Timeline에서 단계별 진행 확인

### 4.5 Approval 처리

Run이 `waiting_approval` 상태가 되면 Approvals 메뉴에서 승인한다.

1. Approvals 메뉴 이동
2. 승인 대상 선택
3. 산출물 확인
4. Approve 또는 Reject

승인이 완료되면 설정에 따라 run이 자동 재개될 수 있다.

### 4.6 결과 확인

Run Detail에서 다음을 확인한다.

- Step output
- Events
- Artifacts
- Replay history
- Final summary

## 5. 권한별 가능 작업

| 기능 | admin | operator | reviewer | viewer |
| --- | --- | --- | --- | --- |
| Dashboard 조회 | 가능 | 가능 | 가능 | 가능 |
| Project 생성 | 가능 | 가능 | 제한 | 제한 |
| Run 생성/실행 | 가능 | 가능 | 제한 | 제한 |
| Approval 승인 | 가능 | 가능 | 가능 | 제한 |
| Worker maintenance | 가능 | 가능 | 제한 | 제한 |
| Run 삭제 | 가능 | 제한 | 제한 | 제한 |

프로젝트 내부 권한은 membership에 따라 추가로 제한될 수 있다.

## 6. 자주 보는 상태 의미

- `queued`: 실행 대기
- `running`: 실행 중
- `waiting_approval`: 사람 승인 대기
- `retry_scheduled`: 자동 재시도 예약
- `dead_lettered`: 자동 처리 한도 초과
- `completed`: 완료
- `failed`: 실패
- `blocked`: 승인 반려 또는 진행 불가

## 7. 사용 시 주의사항

- User request는 가능한 구체적으로 작성한다.
- 프로젝트 지식은 최신화 후 Reindex를 실행한다.
- Approval 반려 시 note에 사유를 남긴다.
- 실패 Run은 무조건 full-reset하지 말고, 먼저 error/event/artifact를 확인한다.
- 운영 환경에서 기본 계정을 공유하지 않는다.

