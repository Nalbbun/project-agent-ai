import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, buildRunStreamUrl, getStoredUser } from '../api/client';
import RunTimeline from '../components/RunTimeline';
import type { Artifact, ReplayAudit, ReplayDiff, Run } from '../types';

const ACTIVE_QUEUE_STATUSES = new Set(['queued', 'resuming', 'running', 'retry_scheduled', 'waiting_approval']);

export default function RunDetailPage() {
  const { runId = '' } = useParams();
  const [run, setRun] = useState<Run | null>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [replayHistory, setReplayHistory] = useState<ReplayAudit[]>([]);
  const [replayDiff, setReplayDiff] = useState<ReplayDiff | null>(null);
  const [selectedReplayId, setSelectedReplayId] = useState<string>('');
  const [busy, setBusy] = useState(false);
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);
  const [streamConnected, setStreamConnected] = useState(false);
  const user = getStoredUser();
  const canReview = user?.role === 'admin' || user?.role === 'reviewer';

  const isActive = useMemo(() => Boolean(run?.queue_status && ACTIVE_QUEUE_STATUSES.has(run.queue_status)), [run?.queue_status]);
  const isDeadLettered = run?.queue_status === 'dead_lettered';

  const load = async () => {
    const [runData, artifactData, replayData] = await Promise.all([api.run(runId), api.artifacts(runId), api.replayHistory(runId)]);
    setRun(runData as Run);
    setArtifacts(artifactData as Artifact[]);
    setReplayHistory(replayData as ReplayAudit[]);
  };

  useEffect(() => { load().catch(console.error); }, [runId]);
  useEffect(() => {
    if (!runId) return;
    const source = new EventSource(buildRunStreamUrl(runId));
    source.addEventListener('snapshot', (event) => {
      setStreamConnected(true);
      try {
        const payload = JSON.parse((event as MessageEvent).data) as Run;
        setRun(payload);
        setArtifacts(payload.artifacts ?? []);
      } catch (error) { console.error(error); }
    });
    source.addEventListener('end', () => { setStreamConnected(false); source.close(); });
    source.onerror = () => setStreamConnected(false);
    return () => source.close();
  }, [runId]);

  const execAction = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try { await fn(); await load(); } finally { setBusy(false); }
  };
  const loadReplayDiff = async (auditId: string) => {
    setSelectedReplayId(auditId);
    setReplayDiff(await api.replayDiff(runId, auditId));
  };

  if (!run) return <div>Loading...</div>;
  const pendingApprovals = run.approvals.filter((item) => item.status === 'pending');

  return (
    <div className="page">
      <header className="page-header split">
        <div>
          <h2>{run.title}</h2>
          <p className="muted">status: {run.status} / queue: {run.queue_status ?? '-'} / current: {run.current_stage ?? '-'}</p>
          <p className="muted">stream: {streamConnected ? 'connected' : 'disconnected'}</p>
        </div>
        <div className="actions wrap-actions">
          <button onClick={() => execAction(() => api.executeRun(runId))} disabled={busy || isActive}>{busy ? '처리 중...' : '실행 요청'}</button>
          <button className="secondary" onClick={() => execAction(() => api.retryRun(runId))} disabled={busy}>전체 재시도</button>
          <button className="secondary" onClick={() => execAction(() => api.resumeRun(runId))} disabled={busy}>Resume</button>
          <button className="secondary" onClick={() => execAction(() => api.cancelRun(runId))} disabled={busy || !isActive}>Cancel</button>
          {isDeadLettered && (
            <>
              <button className="secondary" onClick={() => execAction(() => api.replayDeadLetter(runId, { mode: 'requeue' }))} disabled={busy}>Dead-letter Requeue</button>
              <button className="secondary" onClick={() => execAction(() => api.replayDeadLetter(runId, { mode: 'from-last-failed' }))} disabled={busy}>Replay Last Failed</button>
              <button className="secondary" onClick={() => execAction(() => api.replayDeadLetter(runId, { mode: 'full-reset' }))} disabled={busy}>Full Reset Replay</button>
            </>
          )}
        </div>
      </header>

      <section className="card">
        <h3>사용자 요구</h3>
        <p>{run.user_request}</p>
        <div className="muted">execution_mode: {run.execution_mode} / started: {run.started_at ? new Date(run.started_at).toLocaleString() : '-'} / finished: {run.finished_at ? new Date(run.finished_at).toLocaleString() : '-'}</div>
        {run.waiting_reason && <div className="warning-box">waiting_reason: {run.waiting_reason}</div>}
        {run.last_error && <div className="error-box">{run.last_error}</div>}
        {run.final_summary && (<><h4>Final Summary</h4><p>{run.final_summary}</p></>) }
      </section>

      <section className="card">
        <div className="split"><h3>Approvals</h3><Link to="/approvals" className="secondary">Approval Inbox</Link></div>
        {!run.approvals.length ? <div className="muted">승인 항목 없음</div> : <div className="list-grid">{run.approvals.map((approval) => (<div key={approval.id} className={`list-item ${approval.due_at ? '' : ''}`}><strong>{approval.phase}</strong><span className="muted">status: {approval.status} / required_role: {approval.required_role}</span><span className="muted">stage: {approval.stage_index} / {approval.stage_total}</span><span className="muted">due: {approval.due_at ? new Date(approval.due_at).toLocaleString() : '-'}</span>{approval.note && <pre className="artifact-preview">{approval.note}</pre>}{approval.status === 'pending' && canReview && (<div className="actions"><button className="secondary" onClick={() => execAction(() => api.approve(runId, approval.id, 'Approved from UI'))}>Approve</button><button className="secondary" onClick={() => execAction(() => api.reject(runId, approval.id, 'Rejected from UI'))}>Reject</button></div>)}</div>))}</div>}
        {pendingApprovals.length > 0 && <div className="muted">pending approvals: {pendingApprovals.length}</div>}
      </section>

      <section className="card-grid">
        <div className="card">
          <h3>Replay Audit / History</h3>
          {!replayHistory.length ? <div className="muted">replay history 없음</div> : <div className="list-grid">{replayHistory.map((item) => (<button key={item.id} type="button" className={`list-item ${selectedReplayId === item.id ? 'selected' : ''}`} onClick={() => loadReplayDiff(item.id)}><strong>{item.mode}</strong><span className="muted">target: seq {item.target_seq} / phase {item.target_phase ?? '-'}</span><span className="muted">before: {item.previous_status ?? '-'} / {item.previous_queue_status ?? '-'}</span><span className="muted">after: {item.result_status ?? '-'} / {item.result_queue_status ?? '-'}</span><span className="muted">at: {new Date(item.created_at).toLocaleString()}</span></button>))}</div>}
        </div>
        <div className="card">
          <h3>Replay Diff</h3>
          {!replayDiff ? <div className="muted">replay 항목을 선택하면 reset 범위와 diff를 볼 수 있습니다.</div> : <><div className="muted">changed steps: {String(replayDiff.summary.changed_step_count ?? 0)} / removed approvals: {replayDiff.removed_approval_ids.length}</div><pre className="artifact-preview">{JSON.stringify(replayDiff.summary, null, 2)}</pre><div className="two-mini"><div><h4>Before</h4><pre className="artifact-preview">{JSON.stringify(replayDiff.before_steps, null, 2)}</pre></div><div><h4>After</h4><pre className="artifact-preview">{JSON.stringify(replayDiff.after_steps, null, 2)}</pre></div></div></>}
        </div>
      </section>

      <section className="card">
        <h3>Step Timeline</h3>
        <RunTimeline steps={run.steps} onRetryStep={(stepId) => execAction(() => api.retryStep(runId, stepId))} />
      </section>

      <section className="card">
        <h3>Artifacts</h3>
        <div className="list-grid">
          {artifacts.map((artifact) => (
            <button type="button" key={artifact.id} className="list-item" onClick={() => setSelectedArtifactId(selectedArtifactId === artifact.id ? null : artifact.id)}>
              <strong>{artifact.name}</strong>
              <span className="muted">type: {artifact.artifact_type} / storage: {artifact.storage_type}</span>
              <span className="muted">summary: {artifact.summary ?? '-'}</span>
              {selectedArtifactId === artifact.id && <pre className="artifact-preview">{JSON.stringify(artifact.content ?? {}, null, 2)}</pre>}
            </button>
          ))}
        </div>
      </section>

      <section className="card">
        <h3>Event Logs</h3>
        <div className="log-list">{run.events.map((event) => (<div key={event.id} className={`log-item ${event.level}`}><strong>[{event.level}]</strong> {event.event_type} - {event.message}<div className="muted">{new Date(event.created_at).toLocaleString()}</div></div>))}</div>
      </section>
    </div>
  );
}
