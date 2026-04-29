# Manager / Orchestrator SW 매뉴얼 묶음

작성일: 2026-04-29

이 문서는 `source/runtime/manager-orchestrator` 기준으로 SW 설치, 환경 구성, 운영, 사용자 사용법, 장애 처리 절차를 정리한 매뉴얼 묶음이다.

## 문서 목록

1. [시스템 설치 및 환경 구성 매뉴얼](./01_system_installation_and_configuration.md)
2. [SW 운영 매뉴얼](./02_sw_operation_manual.md)
3. [SW 사용자 매뉴얼](./03_sw_user_manual.md)
4. [장애 발생 처리 가이드](./04_incident_troubleshooting_guide.md)

## 기본 접속 정보

- Frontend UI: `http://localhost:5174`
- Backend API: `http://localhost:8080`
- Router API: `http://localhost:8081`
- PostgreSQL: `localhost:5432`
- Qdrant: `http://localhost:6333`

## 기본 계정

초기 계정은 `.env`의 `AUTH_*_PASSWORD` 값으로 seed된다.

| 계정 | 기본 역할 | 기본 비밀번호 |
| --- | --- | --- |
| `admin` | admin | `admin1234!` |
| `operator` | operator | `operator1234!` |
| `reviewer` | reviewer | `reviewer1234!` |
| `viewer` | viewer | `viewer1234!` |

운영 환경에서는 최초 기동 전 반드시 기본 비밀번호를 변경한다.

