import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import type { Role } from '../lib/types';
import { Logo } from './brand';

export function homeForRole(role: Role): string {
  return role === 'gestor' || role === 'admin' ? '/dashboard' : '/triagem';
}

export function FullScreenLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="animate-pulse">
        <Logo size={48} />
      </div>
    </div>
  );
}

export function ProtectedRoute({
  children,
  roles,
}: {
  children: ReactNode;
  roles?: Role[];
}) {
  const { user, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) {
    return <Navigate to={homeForRole(user.role)} replace />;
  }
  return <>{children}</>;
}
