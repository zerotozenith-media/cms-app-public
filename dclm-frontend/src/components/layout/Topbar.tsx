interface TopbarProps {
  pageTitle: string;
  onMenuClick: () => void;
  userName: string;
  userInitial: string;
  locationLabel?: string;
  roleLabel?: string;
  onLogout?: () => void;
}

/**
 * Structural port of the demo's topbar. Real location/role values and
 * the logout action are wired to live auth state in Batch 3.2 , this
 * batch verifies the visual shell is faithful to the approved design.
 */
export function Topbar({
  pageTitle,
  onMenuClick,
  userName,
  userInitial,
  locationLabel,
  roleLabel,
  onLogout,
}: TopbarProps) {
  return (
    <div className="topbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button className="menu-btn" aria-label="Menu" onClick={onMenuClick}>
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none">
            <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
        </button>
        <div className="page-title">{pageTitle}</div>
      </div>
      <div className="right">
        {locationLabel && <span className="locked-loc">{locationLabel}</span>}
        {roleLabel && <span className="locked-loc">{roleLabel}</span>}
        <div className="user-chip">
          <span className="av">{userInitial}</span>
          <span className="nm">{userName}</span>
        </div>
        {onLogout && (
          <button className="icon-btn" title="Log out" onClick={onLogout}>
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none">
              <path
                d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
