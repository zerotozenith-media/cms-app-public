import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface ProtectedRouteProps {
  children: ReactNode;
  /** If given, the user's role must have real view permission for this
   * module, not just be logged in. Found this was missing while testing
   * Batch 3.10: a user without admin access could still navigate
   * directly to /admin by URL and land on a confusing empty shell , safe
   * (the backend correctly rejects every real API call, so no data ever
   * leaks) but not a good experience, and worth closing properly rather
   * than leaving as "technically safe, looks broken." */
  requiredModule?: string;
}

export function ProtectedRoute({ children, requiredModule }: ProtectedRouteProps) {
  const { user, isLoading, hasPermission } = useAuth();
  const location = useLocation();

  if (isLoading) return null; // brief flash avoided , restoring session from storage
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  if (requiredModule && !hasPermission(requiredModule, 'view')) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
