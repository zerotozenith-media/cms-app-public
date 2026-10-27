import { useEffect, useRef, useState } from 'react';
import { Link, useLocation as useRoute } from 'react-router-dom';
import { mediaUrl } from '../../api/client';
import { useLocations } from '../../api/locations';
import { useViewingLocation } from '../../api/viewing';
import { useAuth } from '../../context/AuthContext';
import { useOutstanding } from '../../api/notifications';
import { useMarkNoticesRead, useNotices, whenText } from '../../api/accountability';
import { openManual } from '../../api/help';
import type { HelpMsg } from '../../api/help';
import { helpForPath, slug } from '../../help/pages';

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
  const { data: notices } = useNotices();
  const markRead = useMarkNoticesRead();
  useEffect(() => setOpen(false), [route.pathname, setOpen]);
  const unread = notices?.unread ?? 0;
  const total = (data?.total ?? 0) + unread;
  // Opening the bell marks the alerts read; they stay shaded until it closes.
  const [shaded, setShaded] = useState<number[]>([]);
  function toggle() {
    if (!open && unread) {
      setShaded((notices?.results ?? []).filter((n) => !n.read).map((n) => n.id));
      markRead.mutate(undefined);
    }
    setOpen(!open);
  }
  return (
    <div className="tb-pop" ref={ref}>
      <button className="tb-bell" aria-label={total ? `${total} things need attention` : 'Nothing needs attention'} aria-expanded={open} onClick={toggle}>
        <svg viewBox="0 0 24 24" width="21" height="21" fill="none" aria-hidden="true"><path d="M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15L6 16Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round"/><path d="M10 20.5a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg>
        {total > 0 && <span key={total} className={`tb-count ${data?.level ?? 'waiting'}`}>{total > 99 ? '99+' : total}</span>}
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
          {(notices?.results ?? []).length > 0 && <>
            <div className="tb-menu-head" style={{ marginTop: 6 }}>Alerts</div>
            {notices!.results.slice(0, 12).map((n) => (
              <Link key={n.id} to={n.url || '/follow-up'} className={`fa-notice${shaded.includes(n.id) ? ' unread' : ''}`} onClick={() => setOpen(false)}>
                <div>
                  <div className="fa-notice-title">{n.title}</div>
                  {n.body && <div className="fa-notice-body">{n.body}</div>}
                  <div className="fa-notice-when">{whenText(n.created_at)}</div>
                </div>
              </Link>
            ))}
            <div className="tb-menu-note">The same alerts reach your phone when phone alerts are on.</div>
          </>}
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

/** Help for this page (Kay, 26 October 2026): the steps for the page you
 *  are on, the answers to what it may refuse, and its manual page. */
export function PageHelpButton() {
  const route = useRoute();
  const { open, setOpen, ref } = usePopover();
  const [err, setErr] = useState<HelpMsg>(null);
  useEffect(() => { setOpen(false); setErr(null); }, [route.pathname, setOpen]);
  const help = helpForPath(route.pathname);
  return (
    <div className="tb-pop" ref={ref}>
      <button className="tb-help" aria-label="Help for this page" aria-expanded={open} title="Help for this page" onClick={() => setOpen(!open)}>
        <svg viewBox="0 0 24 24" width="21" height="21" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8"/><path d="M9.6 9.3a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .8-1 1.5v.6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/><circle cx="12" cy="16.8" r="1.1" fill="currentColor"/></svg>
      </button>
      {open && (
        <div className="tb-menu tb-help-menu" role="dialog" aria-label="Help for this page">
          <div className="tb-menu-head">Help for this page{help ? `: ${help.title}` : ''}</div>
          {help ? (
            <>
              <ol className="tb-help-steps">{help.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
              {help.links.map((l) => (
                <Link key={l.t} className="tb-menu-item tb-help-link" onClick={() => setOpen(false)}
                  to={`/help?s=${l.s}${l.h ? `&h=${slug(l.h)}` : ''}`}>{l.t} <span aria-hidden="true">›</span></Link>
              ))}
              {help.manual && (
                <button type="button" className="tb-menu-item tb-help-link" onClick={async () => setErr(await openManual(help.manual))}>
                  Full details: manual, page {help.manual} <span aria-hidden="true">›</span>
                </button>
              )}
            </>
          ) : <div className="tb-empty">Search the full Help for what you are doing.</div>}
          {err && <div className={err.error ? 'form-error' : 'help-ok'} role={err.error ? 'alert' : 'status'}>{err.text}</div>}
          <Link to="/help" className="tb-menu-item tb-help-link tb-help-all" onClick={() => setOpen(false)}>Open the full Help <span aria-hidden="true">›</span></Link>
        </div>
      )}
    </div>
  );
}
