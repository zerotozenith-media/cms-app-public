import { LocationPicker, NotificationBell, UserBadge } from './TopbarControls';
import { ServiceTopBadge } from '../service/ServiceBadge';

interface TopbarProps {
  pageTitle: string;
  onMenuClick: () => void;
  onLogout: () => void;
}

/**
 * One row on every device (F1): the page title, then the location picker
 * for people covering every location (F2), the bell (F4) and the person's
 * badge (F1, F3). The old location, role and name labels looked like
 * buttons but did nothing, and wrapped to three rows on a phone.
 */
export function Topbar({ pageTitle, onMenuClick, onLogout }: TopbarProps) {
  return (
    <div className="topbar">
      <div className="tb-left">
        <button className="menu-btn" aria-label="Menu" onClick={onMenuClick}>
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none">
            <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </button>
        <div className="page-title">{pageTitle}</div>
      </div>
      <div className="right">
        <LocationPicker />
        <ServiceTopBadge />
        <NotificationBell />
        <UserBadge onLogout={onLogout} />
      </div>
    </div>
  );
}
