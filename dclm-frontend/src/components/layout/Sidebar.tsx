import { NavLink } from 'react-router-dom';
import { Icon } from '../ui/Icon';
import { NAV_ITEMS } from '../../lib/nav';
import { useAuth } from '../../context/AuthContext';
import logoBadge from '../../assets/logo-badge.png';

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const { hasPermission } = useAuth();
  // Real role-based filtering, replacing the demo's role.nav array ,
  // an item shows only if the user's role has can_view on its module,
  // or it has no module at all (Dashboard, visible to any authenticated user).
  const visibleItems = NAV_ITEMS.filter((item) => item.module === null || hasPermission(item.module, 'view'));

  return (
    <>
      <div className={`backdrop${open ? ' show' : ''}`} onClick={onClose} />
      <aside className={`sidebar${open ? ' open' : ''}`}>
        <div className="side-brand">
          <img src={logoBadge} alt="DCLM Bahrain logo" />
          <span>
            <b>DCLM Bahrain</b>
            <span>Church Management</span>
          </span>
          <button
            className="side-close"
            aria-label="Close menu"
            style={{ position: 'absolute', right: 12, top: 16 }}
            onClick={onClose}
          >
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
              <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        <nav className="side-nav">
          {visibleItems.map((item) => (
            <NavLink
              key={item.key}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
              onClick={onClose}
            >
              <Icon name={item.icon} size={18} />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="side-foot">v0.2 · real backend, Phase 3 in progress</div>
      </aside>
    </>
  );
}
