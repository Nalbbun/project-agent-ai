# Step 5 - Second 작업 이력

작성일: 2026-04-28

## 목표

Step 5 최초 적용 이후 남은 검증/운영 프로파일 작업을 마무리했다.

대상 작업:

1. CI 또는 dependency 설치 환경에서 backend pytest 전체 실행
2. `npm install` 후 frontend `npm run build` 실행
3. 운영 프로파일에서 `RAG_ENABLED=true`, `VECTOR_STORE_ENABLED=true`, `RUNNER_SANDBOX_MODE=docker` 기준으로 Foundation Guard warning 제거

## 적용 내용

### Backend pytest 전체 실행

- `backend/requirements.txt` 기준으로 Python dependency 설치
- 전체 pytest 실행
- 최초 실행은 Windows Temp 및 재사용 basetemp 권한 문제로 실패
- 새 basetemp를 지정하여 재실행
- 최종 결과: `15 passed, 4 warnings`

실행 명령:

```powershell
python -m pytest --basetemp C:\Nalbbun_Project\project-agent-ai\work\pytest_step5_tmp_fresh
```

### Frontend dependency/build

- `frontend`에서 `npm install` 실행
- `package-lock.json` 생성
- `npm run build` 실행
- 기존 TypeScript strict build 오류 보정:
  - Vite `ImportMeta.env` 타입 추가
  - `api.projects()` 반환 타입을 `Project[]`로 명시
- 최종 결과: production build 성공

### Foundation Guard warning 제거 기준 반영

- `.env`
- `.env.example`

두 파일에서 운영 프로파일 기준을 맞춤:

```env
RAG_ENABLED=true
VECTOR_STORE_ENABLED=true
RUNNER_SANDBOX_MODE=docker
RUNNER_SANDBOX_NETWORK_ENABLED=false
```

### Git/작업 폴더 정리

- `node_modules`, `dist`, Python bytecode, pytest 임시 폴더가 git 변경으로 잡히지 않도록 `.gitignore` 추가
- pytest가 만든 일부 임시 폴더는 Windows 권한 문제로 삭제되지 않았지만 `.gitignore`로 추적 대상에서 제외

## 변경 파일

- `.gitignore`
- `source/runtime/manager-orchestrator/.env`
- `source/runtime/manager-orchestrator/.env.example`
- `source/runtime/manager-orchestrator/frontend/package-lock.json`
- `source/runtime/manager-orchestrator/frontend/src/api/client.ts`
- `source/runtime/manager-orchestrator/frontend/src/vite-env.d.ts`

## 검증 결과

- Backend: `15 passed, 4 warnings`
- Frontend: `npm run build` 성공

## 산출물

- 변경 소스 압축 파일 갱신: `work/dist/step5_foundation_guard_sources.zip`
- Second 작업 변경분 압축 파일: `work/dist/step5_second_validation_sources.zip`
