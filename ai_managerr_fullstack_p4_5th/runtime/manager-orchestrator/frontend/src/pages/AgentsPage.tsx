import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Agent } from '../types';

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);

  useEffect(() => {
    api.agents().then(setAgents).catch(console.error);
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <h2>Agents</h2>
        <p className="muted">role / endpoint / model / adapter 매핑</p>
      </header>
      <div className="card-grid">
        {agents.map((agent) => (
          <div key={agent.id} className="card">
            <div className="agent-title">{agent.name}</div>
            <div className="muted">code: {agent.code}</div>
            <div className="muted">role: {agent.role}</div>
            <div className="muted">model: {agent.model}</div>
            <div className="muted">adapter: {agent.adapter ?? '-'}</div>
            <div className="muted break">endpoint: {agent.endpoint}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
