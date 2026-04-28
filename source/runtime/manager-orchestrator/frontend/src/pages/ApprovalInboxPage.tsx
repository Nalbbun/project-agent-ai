import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, buildApprovalInboxStreamUrl, getStoredUser } from '../api/client';
import type { ApprovalInboxItem, ApprovalInboxSnapshot } from '../types';

export default function ApprovalInboxPage() {
  const [snapshot, setSnapshot] = useState<ApprovalInboxSnapshot>({ items: [], actionable_count: 0, queued_count: 0, total_count: 0, overdue_count: 0, due_soon_count: 0, by_phase: {}, by_project: {} });
  const [busyId, setBusyId] = useState<string>('');
  const [streamStatus, setStreamStatus] = useState<'connecting' | 'live' | 'closed'>('connecting');
  const [projectFilter, setProjectFilter] = useState<string>('all');
  const [phaseFilter, setPhaseFilter] = useState<string>('all');
  const [mode, setMode] = useState<'actionable' | 'queued' | 'all'>('actionable');
  const user = getStoredUser();

  const load = async () => {
    const rows = await api.approvalInbox();
    setSnapshot((prev) => ({ ...prev, items: rows, total_count: rows.length, actionable_count: rows.filter((x) => x.actionable).length, queued_count: rows.filter((x) => !x.actionable).length }));
  };

  useEffect(() => {
    load().catch(console.error);
    const source = new EventSource(buildApprovalInboxStreamUrl());
    source.addEventListener('snapshot', (event) => {
      const payload = JSON.parse((event as MessageEvent).data) as ApprovalInboxSnapshot;
      setSnapshot(payload);
      setStreamStatus('live');
    });
    source.onerror = () => setStreamStatus('closed');
    return () => source.close();
  }, []);

  const decide = async (item: ApprovalInboxItem, decision: 'approve' | 'reject') => {
    setBusyId(item.id);
    try {
      if (decision === 'approve') await api.approve(item.run_id, item.id, `Approved by ${user?.display_name ?? 'reviewer'}`);
      else await api.reject(item.run_id, item.id, `Rejected by ${user?.display_name ?? 'reviewer'}`);
      await load();
    } finally {
      setBusyId('');
    }
  };

  const items = snapshot.items;
  const projects = useMemo(() => Array.from(new Set(items.map((item) => item.project_name).filter(Boolean))).sort(), [items]);
  const phases = useMemo(() => Array.from(new Set(items.map((item) => item.phase))).sort(), [items]);
  const filtered = useMemo(() => items.filter((item) => {
    if (mode === 'actionable' && !item.actionable) return false;
    if (mode === 'queued' && item.actionable) return false;
    if (projectFilter !== 'all' && item.project_name !== projectFilter) return false;
    if (phaseFilter !== 'all' && item.phase !== phaseFilter) return false;
    return true;
  }), [items, mode, projectFilter, phaseFilter]);

  return (
    <div className="page">
      <header className="page-header split">
        <div>
          <h2>Approval Inbox</h2>
          <p className="muted">실시간 승인 대기함 / project·phase filter / SLA 상태 표시</p>
        </div>
        <div className="actions">
          <span className="muted">stream: {streamStatus}</span>
          <button className="secondary" onClick={() => load().catch(console.error)}>새로고침</button>
        </div>
      </header>
      <section className="card">
        <div className="filter-row">
          <label>View
            <select value={mode} onChange={(e) => setMode(e.target.value as 'actionable' | 'queued' | 'all')}>
              <option value="actionable">actionable</option>
              <option value="queued">queued</option>
              <option value="all">all</option>
            </select>
          </label>
          <label>Project
            <select value={projectFilter} onChange={(e) => setProjectFilter(e.target.value)}>
              <option value="all">all</option>
              {projects.map((project) => <option key={project} value={project!}>{project}</option>)}
            </select>
          </label>
          <label>Phase
            <select value={phaseFilter} onChange={(e) => setPhaseFilter(e.target.value)}>
              <option value="all">all</option>
              {phases.map((phase) => <option key={phase} value={phase}>{phase}</option>)}
            </select>
          </label>
        </div>
        <div className="stat-grid compact">
          <div className="card"><strong>Total</strong><div>{snapshot.total_count}</div></div>
          <div className="card"><strong>Actionable</strong><div>{snapshot.actionable_count}</div></div>
          <div className="card"><strong>Queued</strong><div>{snapshot.queued_count}</div></div>
          <div className="card"><strong>Overdue</strong><div>{snapshot.overdue_count}</div></div>
          <div className="card"><strong>Due Soon</strong><div>{snapshot.due_soon_count}</div></div>
        </div>
      </section>
      <section className="card">
        <h3>Inbox Items</h3>
        <div className="list-grid">
          {filtered.length ? filtered.map((item) => (
            <div key={item.id} className={`list-item ${item.is_overdue ? 'alert-critical' : item.due_soon ? 'alert-warning' : ''}`}>
              <strong>{item.run_title}</strong>
              <span className="muted">project: {item.project_name ?? '-'}</span>
              <span className="muted">phase: {item.phase} / stage {item.stage_index}/{item.stage_total}</span>
              <span className="muted">required: {item.required_role} / status: {item.status}</span>
              <span className="muted">due: {item.due_at ? new Date(item.due_at).toLocaleString() : '-'} / remaining: {item.sla_minutes_remaining ?? '-'}m</span>
              <div className="actions">
                <Link to={`/runs/${item.run_id}`} className="secondary">Run 보기</Link>
                {item.actionable && (
                  <>
                    <button className="secondary" disabled={busyId === item.id} onClick={() => decide(item, 'approve')}>Approve</button>
                    <button className="secondary" disabled={busyId === item.id} onClick={() => decide(item, 'reject')}>Reject</button>
                  </>
                )}
              </div>
            </div>
          )) : <div className="muted">조건에 맞는 승인 없음</div>}
        </div>
      </section>
    </div>
  );
}
