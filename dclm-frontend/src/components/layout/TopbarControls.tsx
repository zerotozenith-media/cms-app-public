import { useEffect, useRef, useState } from 'react';
import { Link, useLocation as useRoute } from 'react-router-dom';
import { mediaUrl } from '../../api/client';
import { useLocations } from '../../api/locations';
import { useViewingLocation } from '../../api/viewing';
import { useAuth } from '../../context/AuthContext';
import { useOutstanding } from '../../api/notifications';

/** Closes a popover when the person taps elsewhere or presses Escape. */
function usePopover() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent | TouchEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', away); document.addEventListener('touchstart', away); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', away); document.removeEventListener('touchstart', away); document.removeEventListener('keydown', esc); };
  }, [open]);
  return { open, setOpen, ref };
}

export function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '?';
  return ((parts[0][0] ?? '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
}

/** F2: only for people covering every location. */
export function LocationPicker() {
  const { user } = useAuth();
  const { data: locations } = useLocations();
  const [viewing, setViewing] = useViewingLocation();
  const { open, setOpen, ref } = usePopover();
  if (!user || user.location) return null;
  const current = (locations ?? []).find((l) => l.id === viewing);
  const choose = (code: string | null) => { setViewing(code); setOpen(false); };
  return (
    <div className="tb-pop" ref={ref}>
      <button className={`tb-loc${current ? ' narrowed' : ''}`} aria-haspopup="listbox" aria-expanded={open}
        aria-label={`Viewing ${current?.name ?? 'all locations'}. Change`} onClick={() => setOpen(!open)}>
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" aria-hidden="true"><path d="M12 21s-7-6.1-7-11.5A7 7 0 0 1 19 9.5C19 14.9 12 21 12 21Z" stroke="currentColor" strokeWidth="1.8"/><circle cx="12" cy="9.5" r="2.5" stroke="currentColor" strokeWidth="1.8"/></svg>
        <span className="tb-loc-name">{current?.name ?? 'All locations'}</span>
        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" aria-hidden="true"><path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/></svg>
      </button>
      {open && (
        <div className="tb-menu" role="listbox" aria-label="Location to view">
          {[{ id: null as string | null, name: 'All locations' }, ...(locations ?? []).map((l) => ({ id: l.id as string | null, name: l.name }))].map((l) => (
            <button key={l.id ?? 'all'} role="option" aria-selected={viewing === l.id} className="tb-menu-item" onClick={() => choose(l.id)}>
              <span className="tb-check">{viewing === l.id ? '✓' : ''}</span>{l.name}
            </button>
          ))}
          <div className="tb-menu-note">Every page shows the location you choose.</div>
        </div>
      )}
    </div>
  );
}


/** F4: everything waiting on this person, on every page. */
export function NotificationBell() {
  const route = useRoute();
  const { open, setOpen, ref } = usePopover();
  const { data } = useOutstanding();
  useEffect(() => setOpen(false), [route.pathname, setOpen]);
  const total = data?.total ?? 0;
  return (
    <div className="tb-pop" ref={ref}>
      <button className="tb-bell" aria-label={total ? `${total} things need attention` : 'Nothing needs attention'} aria-expanded={open} onClick={() => setOpen(!open)}>
        <svg viewBox="0 0 24 24" width="21" height="21" fill="none" aria-hidden="true"><path d="M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15L6 16Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/><path d="M10 20.5a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
        {total > 0 && <span key={total} className={`tb-count ${data?.level}`}>{total > 99 ? '99+' : total}</span>}
      </button>
      {open && (
        <div className="tb-menu tb-bell-menu" role="dialog" aria-label="Needs your attention">
          <div className="tb-menu-head">Needs your attention</div>
          {!data?.items.length && <div className="tb-empty">Nothing needs your attention.</div>}
          {data?.items.map((i) => (
            <Link key={i.key} to={i.link} className={`tb-alert ${i.level}`} onClick={() => setOpen(false)}>
              <span className="tb-dot" aria-hidden="true" />
              <span className="tb-alert-text">{i.label}</span>
              <span aria-hidden="true">›</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

/** F1 and F3: the person's photo or initials, opening their details. */
export function UserBadge({ onLogout }: { onLogout: () => void }) {
  const { user } = useAuth();
  const { open, setOpen, ref } = usePopover();
  const route = useRoute();
  useEffect(() => setOpen(false), [route.pathname, setOpen]);
  if (!user) return null;
  const name = user.name || user.email;
  const photo = mediaUrl(user.photo);
  const face = (size: string) => photo
    ? <img className={`tb-face ${size}`} src={photo} alt="" />
    : <span className={`tb-face ${size}`} aria-hidden="true">{initials(name)}</span>;
  return (
    <div className="tb-pop" ref={ref}>
      <button className="tb-badge" aria-label={`${name}, account menu`} aria-expanded={open} onClick={() => setOpen(!open)}>{face('sm')}</button>
      {open && (
        <div className="tb-menu tb-user-menu" role="dialog" aria-label="Your account">
          <div className="tb-user">
            {face('lg')}
            <div className="tb-user-text">
              <div className="tb-user-name">{name}</div>
              <div className="tb-user-sub">{user.role ?? 'No role'}</div>
              <div className="tb-user-sub">{user.location_name ?? 'All locations'}</div>
            </div>
          </div>
          <Link to="/profile" className="tb-menu-item" onClick={() => setOpen(false)}>My profile</Link>
          <button className="tb-menu-item" onClick={onLogout}>Sign out</button>
        </div>
      )}
    </div>
  );
}
