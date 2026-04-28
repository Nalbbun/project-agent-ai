import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Project, Run } from '../types';

export default function RunForm({ onCreated }: { onCreated: (run: Run) => void }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState('');
  const [executionMode, setExecutionMode] = useState('background');
  const [title, setTitle] = useState('AI Agent Manager / Orchestrator 구축');
  const [userRequest, setUserRequest] = useState('PM, Architect, Dev-FE/BE/DB, QA, SecOps를 관장하는 Manager / Orchestrator 백엔드/프론트엔드/DB 소스를 만들어줘');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.projects().then(setProjects).catch(console.error);
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const created = await api.createRun({ project_id: projectId || null, title, user_request: userRequest, execution_mode: executionMode });
      onCreated(created as Run);
      setProjectId('');
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card form-card" onSubmit={submit}>
      <h3>새 Run 생성</h3>
      <label>
        프로젝트
        <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
          <option value="">미지정</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>{project.name}</option>
          ))}
        </select>
      </label>
      <label>
        실행 모드
        <select value={executionMode} onChange={(e) => setExecutionMode(e.target.value)}>
          <option value="background">background</option>
          <option value="inline">inline</option>
        </select>
      </label>
      <label>
        제목
        <input value={title} onChange={(e) => setTitle(e.target.value)} />
      </label>
      <label>
        사용자 요구
        <textarea rows={6} value={userRequest} onChange={(e) => setUserRequest(e.target.value)} />
      </label>
      <button disabled={busy}>{busy ? '생성 중...' : 'Run 생성'}</button>
    </form>
  );
}
