import { Navigate } from 'react-router-dom';
import { getToken } from '../api/client';

export default function RequireAuth({ children }: { children: JSX.Element }) {
  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}
