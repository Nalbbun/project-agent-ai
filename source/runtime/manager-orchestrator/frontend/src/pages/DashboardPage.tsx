import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, buildDashboardStreamUrl } from '../api/client';
import StatCard from '../components/StatCard';
import type { DashboardSummary, FoundationGuardSnapshot } from '../types';

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [foundation, setFoundation] = useState<FoundationGuardSnapshot | null>(null);
  const [streamStatus, setStreamStatus] = useState<'connecting' | 'live' | 'closed'>('connecting');

  useEffect(() => {
    api.dashboard().then(setSummary).catch(console.error);
    api.foundationGuard().then(setFoundation).catch(console.error);
    const source = new EventSource(buildDashboardStreamUrl());
    source.addEventListener('snapshot', (event) => {
      setSummary(JSON.parse((event as MessageEvent).data) as DashboardSummary);
      setStreamStatus('live');
    });
    source.onerror = () => setStreamStatus('closed');
    return () => source.close();
  }, []);

  const latest = useMemo(() => summary?.latest_runs ?? [], [summary]);
  if (!summary) return <div>Loading...</div>;

  return (
    <div className="page">
      <header className="page-header split">
        <div>
          <h2>Dashboard</h2>
          <p className="muted">운영 통합 통계 / approval hotspot / membership workflow / SLA alert</p>
        </div>
        <div className="muted">stream: {streamStatus}</div>
      </header>
      <section className="stat-grid">
        <StatCard title="Projects" value={summary.project_count} />
        <StatCard title="Runs" value={summary.run_count} />
        <StatCard title="Running" value={summary.running_count} />
        <StatCard title="Need Approval" value={summary.waiting_approval_count} />
        <StatCard title="Actionable Approval" value={summary.actionable_approval_count} />
        <StatCard title="Queued Approval" value={summary.queued_approval_count} />
        <StatCard title="Overdue Approval" value={summary.overdue_approval_count} />
        <StatCard title="Due Soon" value={summary.due_soon_approval_count} />
        <StatCard title="Pending Invites" value={summary.pending_invite_count} />
        <StatCard title="Pending Requests" value={summary.pending_request_count} />
        <StatCard title="Workers" value={summary.worker_count} />
        <StatCard title="Dead Letter" value={summary.dead_lettered_count} />
      </section>
      {foundation ? (
        <section className="card">
          <div className="split">
            <h3>Foundation Guard</h3>
            <span className={`status-pill ${foundation.status}`}>{foundation.status}</span>
          </div>
          <div className="foundation-grid">
            {foundation.items.map((item) => (
              <div key={item.code} className={`foundation-item ${item.status}`}>
                <div className="split">
                  <strong>{item.title}</strong>
                  <span className={`status-pill ${item.status}`}>{item.status}</span>
                </div>
                <span className="muted">{item.summary}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
      <section className="card-grid">
        <div className="card">
          <div className="split"><h3>Approval Alerts</h3><Link to="/approvals" className="secondary">Approval Inbox</Link></div>
          <div className="list-grid">
            {(summary.approval_alerts?.items ?? []).length ? summary.approval_alerts?.items.map((item) => (
              <Link key={item.id} to={`/runs/${item.run_id}`} className={`list-item ${item.severity === 'critical' ? 'alert-critical' : 'alert-warning'}`}>
                <strong>{item.run_title ?? item.phase}</strong>
                <span className="muted">project: {item.project_name ?? '-'}</span>
                <span className="muted">phase: {item.phase} / role: {item.required_role}</span>
                <span className="muted">due: {item.due_at ? new Date(item.due_at).toLocaleString() : '-'}</span>
              </Link>
            )) : <div className="muted">SLA 경고 없음</div>}
          </div>
        </div>
        <div className="card">
          <h3>Project Hotspots</h3>
          <div className="list-grid">
            {summary.project_hotspots.length ? summary.project_hotspots.map((item) => (
              <Link key={`${item.project_id ?? item.project_name}`} to="/projects" className="list-item">
                <strong>{item.project_name}</strong>
                <span className="muted">waiting approval: {item.waiting_approval_count}</span>
                <span className="muted">overdue approval: {item.overdue_approval_count}</span>
                <span className="muted">invites / requests: {item.pending_invite_count} / {item.pending_request_count}</span>
              </Link>
            )) : <div className="muted">hotspot 없음</div>}
          </div>
        </div>
      </section>
      <section className="card">
        <h3>Latest Runs</h3>
        <div className="list-grid">
          {latest.map((run) => (
            <Link key={run.id} to={`/runs/${run.id}`} className="list-item">
              <strong>{run.title}</strong>
              <span className="muted">status: {run.status}</span>
              <span className="muted">queue: {run.queue_status}</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
