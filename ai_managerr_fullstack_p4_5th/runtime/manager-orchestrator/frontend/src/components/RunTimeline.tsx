import type { RunStep } from '../types';

export default function RunTimeline({ steps, onRetryStep }: { steps: RunStep[]; onRetryStep?: (stepId: string) => void }) {
  return (
    <div className="timeline">
      {steps.map((step) => (
        <div key={step.id} className={`timeline-step ${step.status}`}>
          <div className="timeline-head">
            <strong>{step.seq}. {step.phase}</strong>
            <span className={`badge ${step.status}`}>{step.status}</span>
          </div>
          <div className="muted">agent: {step.agent_code}</div>
          <div className="muted">backend: {step.backend_name ?? '-'} / model: {step.target_model ?? '-'}</div>
          <div className="muted">schema: {step.schema_valid === null || step.schema_valid === undefined ? '-' : String(step.schema_valid)} / retry: {step.retry_count}/{step.max_retry_count} / ms: {step.execution_ms ?? '-'} / failure: {step.failure_category ?? '-'}</div>
          {step.output_text && <pre>{step.output_text}</pre>}
          {step.error_message && <div className="error-box">{step.error_message}</div>}
          {step.status === 'failed' && onRetryStep && (
            <div className="actions">
              <button className="secondary" onClick={() => onRetryStep(step.id)}>이 단계부터 재시도</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
