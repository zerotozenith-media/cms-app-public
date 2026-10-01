import { TopProgress } from './TopProgress';
import { useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { clearViewingLocation } from '../../api/viewing';
import { useAuth } from '../../context/AuthContext';

interface AppShellProps {
  pageTitle: string;
  children: ReactNode;
}

export function AppShell({ pageTitle, children }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    clearViewingLocation();
    await logout();
    navigate('/login', { replace: true });
  }


  return (
    <div className="shell">
      <TopProgress />
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="main">
        <Topbar
          pageTitle={pageTitle}
          onMenuClick={() => setSidebarOpen(true)}
          onLogout={handleLogout}
        />
        <div className="content">{children}</div>
      </div>
    </div>
  );
}
