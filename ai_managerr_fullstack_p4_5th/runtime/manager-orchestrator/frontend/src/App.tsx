import { Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import RequireAuth from './components/RequireAuth';
import AgentsPage from './pages/AgentsPage';
import ApprovalInboxPage from './pages/ApprovalInboxPage';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import ProjectsPage from './pages/ProjectsPage';
import RunDetailPage from './pages/RunDetailPage';
import RunsPage from './pages/RunsPage';
import WorkersPage from './pages/WorkersPage';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/workers" element={<WorkersPage />} />
        <Route path="/approvals" element={<ApprovalInboxPage />} />
        <Route path="/runs" element={<RunsPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
      </Route>
    </Routes>
  );
}
