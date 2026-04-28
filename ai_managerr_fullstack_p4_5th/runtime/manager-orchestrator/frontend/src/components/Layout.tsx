import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { clearAuth, getStoredUser } from '../api/client';

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/projects', label: 'Projects' },
  { to: '/runs', label: 'Runs' },
  { to: '/agents', label: 'Agents' },
  { to: '/workers', label: 'Workers' },
  { to: '/approvals', label: 'Approvals' },
];

export default function Layout() {
  const navigate = useNavigate();
  const user = getStoredUser();
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>Manager / Orchestrator</h1>
        <p className="muted">PM · Architect · Dev · QA · SecOps 관리 콘솔</p>
        <p className="muted">user: {user?.display_name ?? user?.username ?? '-'} / role: {user?.role ?? '-'}</p>
        <button className="secondary" onClick={() => { clearAuth(); navigate('/login'); }}>로그아웃</button>
        <nav>
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content"><Outlet /></main>
    </div>
  );
}
