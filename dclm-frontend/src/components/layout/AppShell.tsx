import { useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { useAuth } from '../../context/AuthContext';

interface AppShellProps {
  pageTitle: string;
  children: ReactNode;
}

export function AppShell({ pageTitle, children }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login', { replace: true });
  }

  const displayName = user?.name || user?.email || '';
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <div className="shell">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="main">
        <Topbar
          pageTitle={pageTitle}
          onMenuClick={() => setSidebarOpen(true)}
          userName={displayName}
          userInitial={initial}
          locationLabel={user?.location_name ?? 'All locations'}
          roleLabel={user?.role ?? undefined}
          onLogout={handleLogout}
        />
        <div className="content">{children}</div>
      </div>
    </div>
  );
}
