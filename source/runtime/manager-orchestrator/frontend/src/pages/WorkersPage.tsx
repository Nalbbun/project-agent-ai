import { useEffect, useMemo, useState } from 'react';
import { api, buildWorkersStreamUrl } from '../api/client';
import type { WorkerMaintenanceResult, WorkerStatus } from '../types';

type WorkerSnapshot = {
  workers: WorkerStatus[];
  summary: {
    worker_count: number;
    active_worker_count: number;
    stale_worker_count: number;
    stale_run_count: number;
    dead_letter_count: number;
  };
};

export default function WorkersPage() {
  const [workers, setWorkers] = useState<WorkerStatus[]>([]);
  const [summary, setSummary] = useState<WorkerSnapshot['summary'] | null>(null);
  const [maintenance, setMaintenance] = useState<WorkerMaintenanceResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [streamStatus, setStreamStatus] = useState<'connecting' | 'live' | 'closed'>('connecting');

  const load = async () => {
    const [workerRows] = await Promise.all([api.workers()]);
    setWorkers(workerRows);
  };
  useEffect(() => {
    load().catch(console.error);
    const source = new EventSource(buildWorkersStreamUrl());
    source.addEventListener('snapshot', (event) => {
      const payload = JSON.parse((event as MessageEvent).data) as WorkerSnapshot;
      setWorkers(payload.workers);
      setSummary(payload.summary);
      setStreamStatus('live');
    });
    source.onerror = () => setStreamStatus('closed');
    return () => source.close();
  }, []);

  const runMaintenance = async () => {
    setBusy(true);
    try {
      const result = await api.maintainWorkers();
      setMaintenance(result);
      await load();
    } finally {
      setBusy(false);
    }
  };

  const info = useMemo(() => summary ?? { worker_count: workers.length, active_worker_count: workers.length, stale_worker_count: 0, stale_run_count: 0, dead_letter_count: 0 }, [summary, workers]);

  return (
    <div className="page">
      <header className="page-header split">
        <div>
          <h2>Workers</h2>
          <p className="muted">worker heartbeat / stale reclaim / dead-letter maintenance / live stream</p>
        </div>
        <div className="actions">
          <span className="muted">stream: {streamStatus}</span>
          <button className="secondary" onClick={runMaintenance} disabled={busy}>{busy ? '처리 중...' : 'Maintenance 실행'}</button>
        </div>
      </header>
      {maintenance && <div className="card muted">reclaimed_runs: {maintenance.reclaimed_runs} / dead_lettered_runs: {maintenance.dead_lettered_runs}</div>}
      <section className="stat-grid">
        <div className="card"><strong>Workers</strong><div>{info.worker_count}</div></div>
        <div className="card"><strong>Active</strong><div>{info.active_worker_count}</div></div>
        <div className="card"><strong>Stale Workers</strong><div>{info.stale_worker_count}</div></div>
        <div className="card"><strong>Stale Runs</strong><div>{info.stale_run_count}</div></div>
        <div className="card"><strong>Dead Letter</strong><div>{info.dead_letter_count}</div></div>
      </section>
      <div className="list-grid">
        {workers.map((worker) => (
          <div key={worker.id} className="card">
            <strong>{worker.worker_id}</strong>
            <div className="muted">status: {worker.status}</div>
            <div className="muted">host: {worker.hostname} / pid: {worker.pid}</div>
            <div className="muted">run: {worker.current_run_id ?? '-'}</div>
            <div className="muted">phase: {worker.current_step_phase ?? '-'}</div>
            <div className="muted">last seen: {new Date(worker.last_seen_at).toLocaleString()}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
