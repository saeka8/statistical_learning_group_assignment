import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import type { ReactNode } from 'react';

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div aria-label="Loading workspace">Loading workspace...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace state={{ authIntent: 'login', from: location.pathname }} />;
  }

  return <>{children}</>;
}
