import { FormEvent, useEffect, useMemo, useState } from 'react';
import { api, getStoredUser } from '../api/client';
import type {
  Project,
  ProjectAccessRequest,
  ProjectKnowledge,
  ProjectMembership,
  ProjectMembershipInvite,
  ProjectSummary,
  User,
} from '../types';

export default function ProjectsPage() {
  const currentUser = getStoredUser();
  const [projects, setProjects] = useState<Project[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [knowledge, setKnowledge] = useState<ProjectKnowledge[]>([]);
  const [memberships, setMemberships] = useState<ProjectMembership[]>([]);
  const [summary, setSummary] = useState<ProjectSummary | null>(null);
  const [invites, setInvites] = useState<ProjectMembershipInvite[]>([]);
  const [myInvites, setMyInvites] = useState<ProjectMembershipInvite[]>([]);
  const [requests, setRequests] = useState<ProjectAccessRequest[]>([]);
  const [myRequests, setMyRequests] = useState<ProjectAccessRequest[]>([]);
  const [form, setForm] = useState({ name: '', description: '' });
  const [knowledgeForm, setKnowledgeForm] = useState({ title: '', content: '' });
  const [membershipForm, setMembershipForm] = useState({ user_id: '', access_role: 'viewer' });
  const [inviteForm, setInviteForm] = useState({ invited_user_id: '', access_role: 'viewer', note: '' });
  const [requestForm, setRequestForm] = useState({ requested_role: 'viewer', note: '' });

  const loadProjects = async () => {
    const rows = await api.projects();
    setProjects(rows as Project[]);
    if (!selectedProjectId && rows[0]?.id) setSelectedProjectId(rows[0].id);
  };

  const refreshGlobal = async () => {
    const [userRows, inviteRows, requestRows] = await Promise.all([
      api.users(),
      api.myInvites(),
      api.myAccessRequests(),
    ]);
    setUsers(userRows);
    setMyInvites(inviteRows);
    setMyRequests(requestRows);
  };

  const refreshProjectData = async (projectId: string) => {
    const [knowledgeRows, membershipRows, summaryRow, inviteRows, requestRows] = await Promise.all([
      api.projectKnowledge(projectId),
      api.projectMemberships(projectId),
      api.projectSummary(projectId),
      api.projectInvites(projectId).catch(() => [] as ProjectMembershipInvite[]),
      api.projectAccessRequests(projectId).catch(() => [] as ProjectAccessRequest[]),
    ]);
    setKnowledge(knowledgeRows as ProjectKnowledge[]);
    setMemberships(membershipRows as ProjectMembership[]);
    setSummary(summaryRow as ProjectSummary);
    setInvites(inviteRows);
    setRequests(requestRows);
  };

  useEffect(() => { loadProjects().catch(console.error); refreshGlobal().catch(console.error); }, []);
  useEffect(() => { if (selectedProjectId) refreshProjectData(selectedProjectId).catch(console.error); }, [selectedProjectId]);

  const selectedProject = useMemo(() => projects.find((p) => p.id === selectedProjectId) ?? null, [projects, selectedProjectId]);
  const canManageMembership = summary?.my_access_role === 'owner' || currentUser?.role === 'admin';
  const isMember = Boolean(summary?.my_access_role);

  const createProject = async (e: FormEvent) => {
    e.preventDefault();
    await api.createProject(form);
    setForm({ name: '', description: '' });
    await loadProjects();
  };
  const createKnowledge = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId) return;
    await api.createProjectKnowledge(selectedProjectId, knowledgeForm);
    setKnowledgeForm({ title: '', content: '' });
    await refreshProjectData(selectedProjectId);
  };
  const addMembership = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId || !membershipForm.user_id) return;
    await api.createProjectMembership(selectedProjectId, membershipForm);
    setMembershipForm({ user_id: '', access_role: 'viewer' });
    await refreshProjectData(selectedProjectId);
  };
  const createInvite = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId || !inviteForm.invited_user_id) return;
    await api.createProjectInvite(selectedProjectId, inviteForm);
    setInviteForm({ invited_user_id: '', access_role: 'viewer', note: '' });
    await refreshProjectData(selectedProjectId);
  };
  const createAccessRequest = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId) return;
    await api.createAccessRequest(selectedProjectId, requestForm);
    setRequestForm({ requested_role: 'viewer', note: '' });
    await refreshGlobal();
    await refreshProjectData(selectedProjectId);
  };
  const removeMembership = async (membershipId: string) => {
    if (!selectedProjectId) return;
    await api.deleteProjectMembership(selectedProjectId, membershipId);
    await refreshProjectData(selectedProjectId);
  };
  const deleteKnowledge = async (knowledgeId: string) => {
    if (!selectedProjectId) return;
    await api.deleteProjectKnowledge(selectedProjectId, knowledgeId);
    await refreshProjectData(selectedProjectId);
  };

  return (
    <div className="page two-column">
      <section className="card form-card">
        <h3>Create Project</h3>
        <form onSubmit={createProject}>
          <label>Name<input value={form.name} onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))} /></label>
          <label>Description<textarea rows={4} value={form.description} onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))} /></label>
          <button type="submit">프로젝트 생성</button>
        </form>
        <h3 style={{ marginTop: 24 }}>Projects</h3>
        <div className="list-grid">
          {projects.map((project) => (
            <button type="button" key={project.id} className={`list-item ${selectedProjectId === project.id ? 'selected' : ''}`} onClick={() => setSelectedProjectId(project.id)}>
              <strong>{project.name}</strong>
              <span className="muted">{project.description ?? '-'}</span>
            </button>
          ))}
        </div>
        <div className="card" style={{ marginTop: 16 }}>
          <h3>My Invites / Requests</h3>
          <div className="list-grid">
            {myInvites.map((item) => (
              <div key={item.id} className="list-item">
                <strong>Invite</strong>
                <span className="muted">project: {projects.find((p) => p.id === item.project_id)?.name ?? item.project_id}</span>
                <span className="muted">role: {item.access_role} / status: {item.status}</span>
                {item.status === 'pending' && <div className="actions"><button className="secondary" onClick={() => api.acceptInvite(item.id).then(refreshGlobal)}>Accept</button><button className="secondary" onClick={() => api.declineInvite(item.id).then(refreshGlobal)}>Decline</button></div>}
              </div>
            ))}
            {myRequests.map((item) => (
              <div key={item.id} className="list-item">
                <strong>Access Request</strong>
                <span className="muted">project: {projects.find((p) => p.id === item.project_id)?.name ?? item.project_id}</span>
                <span className="muted">requested: {item.requested_role} / status: {item.status}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
      <section className="page">
        <div className="card">
          <div className="split">
            <h3>Project Summary</h3>
            {selectedProjectId && <button className="secondary" onClick={() => api.reindexProjectKnowledge(selectedProjectId).then(() => refreshProjectData(selectedProjectId)).catch(console.error)}>Reindex Knowledge</button>}
          </div>
          {summary ? (
            <div className="stat-grid compact">
              <div className="card"><strong>My Access</strong><div>{summary.my_access_role ?? '-'}</div></div>
              <div className="card"><strong>Knowledge</strong><div>{summary.knowledge_count}</div></div>
              <div className="card"><strong>Members</strong><div>{summary.membership_count}</div></div>
              <div className="card"><strong>Runs</strong><div>{summary.run_count}</div></div>
              <div className="card"><strong>Waiting Approval</strong><div>{summary.waiting_approval_count}</div></div>
              <div className="card"><strong>Pending Invites</strong><div>{summary.pending_invite_count}</div></div>
              <div className="card"><strong>Pending Requests</strong><div>{summary.pending_request_count}</div></div>
            </div>
          ) : <div className="muted">프로젝트를 선택하세요.</div>}
        </div>
        <div className="card-grid">
          <div className="card">
            <h3>Knowledge</h3>
            <form onSubmit={createKnowledge}>
              <label>Title<input value={knowledgeForm.title} onChange={(e) => setKnowledgeForm((prev) => ({ ...prev, title: e.target.value }))} /></label>
              <label>Content<textarea rows={5} value={knowledgeForm.content} onChange={(e) => setKnowledgeForm((prev) => ({ ...prev, content: e.target.value }))} /></label>
              <button type="submit" disabled={!selectedProjectId}>지식 추가</button>
            </form>
            <div className="list-grid" style={{ marginTop: 16 }}>
              {knowledge.map((item) => (
                <div key={item.id} className="list-item">
                  <div className="split"><strong>{item.title}</strong><button className="secondary" type="button" onClick={() => deleteKnowledge(item.id)}>삭제</button></div>
                  <span className="muted">{item.source_type}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <h3>Memberships</h3>
            <form onSubmit={addMembership}>
              <label>User<select value={membershipForm.user_id} onChange={(e) => setMembershipForm((prev) => ({ ...prev, user_id: e.target.value }))}><option value="">선택</option>{users.map((user) => <option key={user.id} value={user.id}>{user.display_name} ({user.role})</option>)}</select></label>
              <label>Access Role<select value={membershipForm.access_role} onChange={(e) => setMembershipForm((prev) => ({ ...prev, access_role: e.target.value }))}><option value="viewer">viewer</option><option value="reviewer">reviewer</option><option value="editor">editor</option><option value="owner">owner</option></select></label>
              <button type="submit" disabled={!selectedProjectId || !canManageMembership}>멤버 추가</button>
            </form>
            <div className="list-grid" style={{ marginTop: 16 }}>
              {memberships.map((item) => {
                const user = users.find((u) => u.id === item.user_id);
                return (
                  <div key={item.id} className="list-item">
                    <div className="split"><strong>{user?.display_name ?? item.user_id}</strong>{canManageMembership && <button className="secondary" type="button" onClick={() => removeMembership(item.id)}>제거</button>}</div>
                    <span className="muted">username: {user?.username ?? '-'}</span>
                    <span className="muted">project role: {item.access_role}</span>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="card">
            <h3>Membership Invite Workflow</h3>
            <form onSubmit={createInvite}>
              <label>User<select value={inviteForm.invited_user_id} onChange={(e) => setInviteForm((prev) => ({ ...prev, invited_user_id: e.target.value }))}><option value="">선택</option>{users.filter((u) => u.id !== currentUser?.id).map((user) => <option key={user.id} value={user.id}>{user.display_name} ({user.role})</option>)}</select></label>
              <label>Access Role<select value={inviteForm.access_role} onChange={(e) => setInviteForm((prev) => ({ ...prev, access_role: e.target.value }))}><option value="viewer">viewer</option><option value="reviewer">reviewer</option><option value="editor">editor</option><option value="owner">owner</option></select></label>
              <label>Note<textarea rows={3} value={inviteForm.note} onChange={(e) => setInviteForm((prev) => ({ ...prev, note: e.target.value }))} /></label>
              <button type="submit" disabled={!selectedProjectId || !canManageMembership}>초대 발송</button>
            </form>
            <div className="list-grid" style={{ marginTop: 16 }}>
              {invites.map((item) => {
                const user = users.find((u) => u.id === item.invited_user_id);
                return <div key={item.id} className="list-item"><strong>{user?.display_name ?? item.invited_user_id}</strong><span className="muted">role: {item.access_role} / status: {item.status}</span><span className="muted">note: {item.note ?? '-'}</span></div>;
              })}
            </div>
          </div>
          <div className="card">
            <h3>Access Request Workflow</h3>
            {!isMember && selectedProject ? (
              <form onSubmit={createAccessRequest}>
                <label>Requested Role<select value={requestForm.requested_role} onChange={(e) => setRequestForm((prev) => ({ ...prev, requested_role: e.target.value }))}><option value="viewer">viewer</option><option value="reviewer">reviewer</option><option value="editor">editor</option></select></label>
                <label>Note<textarea rows={3} value={requestForm.note} onChange={(e) => setRequestForm((prev) => ({ ...prev, note: e.target.value }))} /></label>
                <button type="submit">접근 요청</button>
              </form>
            ) : <div className="muted">현재 프로젝트 접근 요청은 비멤버 사용자만 생성할 수 있습니다.</div>}
            <div className="list-grid" style={{ marginTop: 16 }}>
              {requests.map((item) => {
                const user = users.find((u) => u.id === item.requested_by_user_id);
                return (
                  <div key={item.id} className="list-item">
                    <strong>{user?.display_name ?? item.requested_by_user_id}</strong>
                    <span className="muted">requested: {item.requested_role} / status: {item.status}</span>
                    <span className="muted">note: {item.note ?? '-'}</span>
                    {canManageMembership && item.status === 'pending' && <div className="actions"><button className="secondary" onClick={() => api.approveAccessRequest(item.id, { access_role: item.requested_role, note: 'Approved from project UI' }).then(() => refreshProjectData(selectedProjectId)).then(refreshGlobal)}>Approve</button><button className="secondary" onClick={() => api.rejectAccessRequest(item.id, { note: 'Rejected from project UI' }).then(() => refreshProjectData(selectedProjectId)).then(refreshGlobal)}>Reject</button></div>}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
