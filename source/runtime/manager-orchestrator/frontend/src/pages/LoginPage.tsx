import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, setAuth } from '../api/client';

export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin1234!');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const result = await api.login({ username, password });
      setAuth(result);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page">
      <form className="card login-card" onSubmit={submit}>
        <h2>Manager / Orchestrator Login</h2>
        <p className="muted">기본 계정: admin / admin1234!</p>
        <label>Username<input value={username} onChange={(e) => setUsername(e.target.value)} /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
        {error && <div className="error-box">{error}</div>}
        <button disabled={busy}>{busy ? '로그인 중...' : '로그인'}</button>
      </form>
    </div>
  );
}
