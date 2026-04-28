import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import RunForm from '../components/RunForm';
import type { Run } from '../types';

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);

  const load = () => api.runs().then(setRuns).catch(console.error);

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="page two-column">
      <RunForm onCreated={(run) => setRuns((prev) => [run, ...prev])} />
      <section className="card">
        <h3>Runs</h3>
        <div className="list-grid">
          {runs.map((run) => (
            <Link key={run.id} to={`/runs/${run.id}`} className="list-item">
              <strong>{run.title}</strong>
              <span className="muted">status: {run.status}</span>
              <span className="muted">created: {new Date(run.created_at).toLocaleString()}</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
