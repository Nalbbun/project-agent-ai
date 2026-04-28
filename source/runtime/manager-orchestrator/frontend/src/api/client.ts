import type {
  Agent,
  Approval,
  ApprovalAlertSnapshot,
  ApprovalInboxItem,
  ApprovalInboxSnapshot,
  Artifact,
  DashboardSummary,
  FoundationGuardSnapshot,
  LoginResponse,
  ProjectAccessRequest,
  ProjectKnowledge,
  ProjectMembership,
  ProjectMembershipInvite,
  ProjectSummary,
  ReplayAudit,
  ReplayDiff,
  Run,
  RunEnqueueResponse,
  User,
  WorkerMaintenanceResult,
  WorkerStatus,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';
const TOKEN_KEY = 'mo_access_token';
const USER_KEY = 'mo_user';

export function setAuth(response: LoginResponse) {
  localStorage.setItem(TOKEN_KEY, response.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(response.user));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getToken() { return localStorage.getItem(TOKEN_KEY); }
export function getStoredUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw) as User; } catch { return null; }
}

function buildStreamUrl(path: string) {
  const token = getToken();
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (token) url.searchParams.set('access_token', token);
  return url.toString();
}

export function buildDashboardStreamUrl() { return buildStreamUrl('/dashboard/stream'); }
export function buildWorkersStreamUrl() { return buildStreamUrl('/workers/stream'); }
export function buildRunStreamUrl(runId: string) { return buildStreamUrl(`/runs/${runId}/stream`); }
export function buildApprovalInboxStreamUrl() { return buildStreamUrl('/approvals/inbox/stream'); }

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(init?.headers as Record<string, string> ?? {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE}${url}`, { ...init, headers });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || 'Request failed');
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  login: (body: { username: string; password: string }) => request<LoginResponse>('/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  me: () => request<User>('/auth/me'),
  users: () => request<User[]>('/auth/users'),
  logout: () => request('/auth/logout', { method: 'POST' }),
  dashboard: () => request<DashboardSummary>('/dashboard'),
  foundationGuard: () => request<FoundationGuardSnapshot>('/foundation/guard'),
  approvalAlerts: () => request<ApprovalAlertSnapshot>('/approvals/alerts'),
  agents: () => request<Agent[]>('/agents'),
  workers: () => request<WorkerStatus[]>('/workers'),
  maintainWorkers: () => request<WorkerMaintenanceResult>('/workers/maintenance', { method: 'POST' }),
  projects: () => request('/projects'),
  createProject: (body: { name: string; description?: string }) => request('/projects', { method: 'POST', body: JSON.stringify(body) }),
  projectSummary: (projectId: string) => request<ProjectSummary>(`/projects/${projectId}/summary`),
  projectMemberships: (projectId: string) => request<ProjectMembership[]>(`/projects/${projectId}/memberships`),
  createProjectMembership: (projectId: string, body: { user_id: string; access_role: string }) => request<ProjectMembership>(`/projects/${projectId}/memberships`, { method: 'POST', body: JSON.stringify(body) }),
  deleteProjectMembership: (projectId: string, membershipId: string) => request(`/projects/${projectId}/memberships/${membershipId}`, { method: 'DELETE' }),
  myInvites: () => request<ProjectMembershipInvite[]>('/projects/my-invites'),
  projectInvites: (projectId: string) => request<ProjectMembershipInvite[]>(`/projects/${projectId}/invites`),
  createProjectInvite: (projectId: string, body: { invited_user_id: string; access_role: string; note?: string }) => request<ProjectMembershipInvite>(`/projects/${projectId}/invites`, { method: 'POST', body: JSON.stringify(body) }),
  acceptInvite: (inviteId: string) => request<ProjectMembershipInvite>(`/projects/invites/${inviteId}/accept`, { method: 'POST' }),
  declineInvite: (inviteId: string) => request<ProjectMembershipInvite>(`/projects/invites/${inviteId}/decline`, { method: 'POST' }),
  myAccessRequests: () => request<ProjectAccessRequest[]>('/projects/access-requests/mine'),
  projectAccessRequests: (projectId: string) => request<ProjectAccessRequest[]>(`/projects/${projectId}/access-requests`),
  createAccessRequest: (projectId: string, body: { requested_role: string; note?: string }) => request<ProjectAccessRequest>(`/projects/${projectId}/access-requests`, { method: 'POST', body: JSON.stringify(body) }),
  approveAccessRequest: (requestId: string, body: { access_role: string; note?: string }) => request<ProjectAccessRequest>(`/projects/access-requests/${requestId}/approve`, { method: 'POST', body: JSON.stringify(body) }),
  rejectAccessRequest: (requestId: string, body: { access_role?: string; note?: string }) => request<ProjectAccessRequest>(`/projects/access-requests/${requestId}/reject`, { method: 'POST', body: JSON.stringify(body) }),
  projectKnowledge: (projectId: string) => request<ProjectKnowledge[]>(`/projects/${projectId}/knowledge`),
  createProjectKnowledge: (projectId: string, body: { title: string; content: string; source_type?: string; tags?: string[]; summary?: string }) => request<ProjectKnowledge>(`/projects/${projectId}/knowledge`, { method: 'POST', body: JSON.stringify(body) }),
  deleteProjectKnowledge: (projectId: string, knowledgeId: string) => request(`/projects/${projectId}/knowledge/${knowledgeId}`, { method: 'DELETE' }),
  reindexProjectKnowledge: (projectId: string) => request(`/projects/${projectId}/knowledge/reindex`, { method: 'POST' }),
  runs: () => request<Run[]>('/runs'),
  run: (id: string) => request<Run>(`/runs/${id}`),
  replayHistory: (runId: string) => request<ReplayAudit[]>(`/runs/${runId}/replay-history`),
  replayDiff: (runId: string, auditId: string) => request<ReplayDiff>(`/runs/${runId}/replay-history/${auditId}/diff`),
  approvals: (runId: string) => request<Approval[]>(`/runs/${runId}/approvals`),
  approvalInbox: () => request<ApprovalInboxItem[]>(`/approvals/inbox`),
  approve: (runId: string, approvalId: string, note = '') => request<Approval>(`/runs/${runId}/approvals/${approvalId}/approve`, { method: 'POST', body: JSON.stringify({ note }) }),
  reject: (runId: string, approvalId: string, note = '') => request<Approval>(`/runs/${runId}/approvals/${approvalId}/reject`, { method: 'POST', body: JSON.stringify({ note }) }),
  createRun: (body: { project_id?: string | null; title: string; user_request: string; execution_mode?: string }) => request<Run>('/runs', { method: 'POST', body: JSON.stringify(body) }),
  executeRun: (id: string) => request<RunEnqueueResponse>(`/runs/${id}/execute`, { method: 'POST' }),
  retryRun: (id: string) => request<RunEnqueueResponse>(`/runs/${id}/retry`, { method: 'POST' }),
  cancelRun: (id: string) => request<Run>(`/runs/${id}/cancel`, { method: 'POST' }),
  resumeRun: (id: string) => request<RunEnqueueResponse>(`/runs/${id}/resume`, { method: 'POST' }),
  retryStep: (runId: string, stepId: string, mode = 'from-step') => request<RunEnqueueResponse>(`/runs/${runId}/steps/${stepId}/retry`, { method: 'POST', body: JSON.stringify({ mode }) }),
  replayDeadLetter: (runId: string, body: { mode: string; from_phase?: string; note?: string }) => request<RunEnqueueResponse>(`/runs/${runId}/dead-letter/replay`, { method: 'POST', body: JSON.stringify(body) }),
  artifacts: (runId: string) => request<Artifact[]>(`/runs/${runId}/artifacts`),
};
